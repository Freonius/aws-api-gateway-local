"""API Gateway simulator"""
from contextlib import suppress
from typing import IO, cast
from os import environ
from json import dumps, loads
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from boto3 import client
from uvicorn import run as uvrun

with suppress(ImportError):
    from boto3_type_annotations.lambda_.client import Client as LambdaClient
with suppress(ImportError):
    from aws_lambda_typing.events import APIGatewayProxyEventV1

# pylint: disable=broad-except

lbd: "LambdaClient" = client(
    "lambda",
    region_name=environ.get("AWS_DEFAULT_REGION", None),
    aws_access_key_id=environ.get("AWS_ACCESS_KEY_ID", None),
    aws_secret_access_key=environ.get("AWS_SECRET_ACCESS_KEY", None),
    endpoint_url=environ.get("AWS_ENDPOINT_URL", None),
)


async def get_payload(request: Request) -> "APIGatewayProxyEventV1":
    """Convert the request to a payload"""
    body = None
    with suppress(Exception):
        body = await request.json()
        # body = (await request.body()).decode("utf-8")
    payload: "APIGatewayProxyEventV1" = {
        "body": dumps(body) if body is not None else None,
        "headers": dict(request.headers),
        "httpMethod": request.method,
        "isBase64Encoded": False,
        "path": request.url.path,
        "queryStringParameters": dict(request.query_params),
        "requestContext": {
            "httpMethod": request.method.strip().upper(),
        },  # dict(request.scope),  # TODO: Add request context
        "resource": request.url.path,
        "stageVariables": None,  # dict(request.scope),
        "pathParameters": dict(request.path_params),
        "multiValueQueryStringParameters": dict(
            request.query_params
        ),  # TODO: Add request context
        "multiValueHeaders": dict(request.headers),  # TODO: Add request context
    }
    return payload


async def run_lambda(request: Request, lambda_name: str) -> Response:
    """Run the lambda"""
    payload = await get_payload(request)
    try:
        res = lbd.invoke(
            FunctionName=lambda_name,
            InvocationType="RequestResponse",
            Payload=dumps(payload),
        )
    except Exception as err:
        print(err)
        return Response(str(err), status_code=500)
    response = loads(cast(IO[bytes], res["Payload"]).read().decode("utf-8"))
    print(response)
    return Response(
        response["body"],
        status_code=response["statusCode"],
        headers=response["headers"],
    )


routes: list[dict[str, str | list[str]]] = []

with suppress(Exception):
    with open("./routes.json", "r", encoding="utf-8") as handle:
        routes = loads(handle.read())


def run(port: int = 9000) -> None:
    """The main function"""

    app = FastAPI()

    for route in routes:

        @app.route(
            cast(str, route["path"]),
            methods=[route["method"]]
            if isinstance(route["method"], str)
            else route["method"],
        )
        async def _(request: Request) -> Response:
            """The endpoints function"""
            lambda_name: str | None = None
            for rt in routes:
                with suppress(KeyError):
                    if rt["path"] == request.url.path:
                        if (
                            isinstance(rt["method"], list)
                            and request.method in rt["method"]
                        ):
                            lambda_name = cast(str, rt["lambda"])
                        elif (
                            isinstance(rt["method"], str)
                            and request.method == rt["method"]
                        ):
                            lambda_name = cast(str, rt["lambda"])
                            break
            if lambda_name is None:
                raise HTTPException(status_code=404, detail="Not found")
            print(request.url.path, request.method, lambda_name)
            return await run_lambda(request, lambda_name=lambda_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "*",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uvrun(app, host="0.0.0.0", port=port)


__all__ = ["run"]
