"""Lambda helpers."""
from json import dumps, loads
from contextlib import suppress
from logging import getLogger, Logger
from base64 import b64decode
from os import environ
from typing import Callable, Union
from traceback import format_exception

with suppress(ImportError):
    # pylint: disable=unused-import
    from aws_lambda_typing.context import Context
    from aws_lambda_typing.responses import (
        APIGatewayProxyResponseV1,
        APIGatewayProxyResponseV2,
    )
    from aws_lambda_typing.events import APIGatewayProxyEventV1, APIGatewayProxyEventV2

try:
    from .cognito import Cognito
    from .exceptions import LambdaException
    from .s3 import S3
except ImportError:
    from cognito import Cognito  # type: ignore
    from exceptions import LambdaException  # type: ignore
    from s3 import S3  # type: ignore


def return_body(
    payload: Union[dict[str, object], list[object], None, str],
    status_code: int = 200,
    headers: Union[dict[str, str], None] = None,
) -> "Union[APIGatewayProxyResponseV2, APIGatewayProxyResponseV1]":
    """Return the body."""
    response_headers = headers if headers is not None else {}
    response_headers["Content-Type"] = str(
        "application/json"
        if payload is not None and not isinstance(payload, str)
        else "text/plain",
    )
    if environ.get("ALLOW_CORS", "1") == "1":
        response_headers["Access-Control-Allow-Origin"] = environ.get(
            "CORS_ORIGIN", "*"
        )
        response_headers[
            "Access-Control-Allow-Methods"
        ] = "GET, POST, PUT, OPTIONS, DELETE"
        response_headers["Access-Control-Allow-Headers"] = str(
            "Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With"
        )
        response_headers["Access-Control-Allow-Credentials"] = "true"

    if payload is None:
        payload = ""
    if not isinstance(payload, str):
        payload = dumps(payload)
    return {
        "statusCode": status_code,
        "headers": response_headers,
        "body": payload,
    }


class LambdaDecorator:
    """Lambda decorator."""

    _context: "Context"
    _event: "Union[APIGatewayProxyEventV1, APIGatewayProxyEventV2]"
    _email: Union[str, None]
    _sub: Union[str, None]
    _no_auth: bool
    _use_cognito: bool
    _cognito: "Union[Cognito, None]"
    _additional_headers: dict[str, str]
    _logger: Logger

    def __init__(
        self,
        event: "Union[APIGatewayProxyEventV1, APIGatewayProxyEventV2]",
        context: "Context",
        no_auth: bool = False,
    ) -> None:
        """Initialize the Lambda decorator."""
        for key in (
            "AWS_DEFAULT_REGION",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "COGNITO_ENDPOINT_URL",
            "DYNAMO_ENDPOINT_URL",
            "S3_ENDPOINT_URL",
            "SES_ENDPOINT_URL",
        ):
            with suppress(KeyError):
                if environ[key].strip() == "":
                    del environ[key]
        if len(environ.get("LOCALSTACK_HOSTNAME", "").strip()) > 0:
            # Lambdas on Localstack run on docker, so localhost is something else
            # We need the name of localstack
            for key in (
                "COGNITO_ENDPOINT_URL",
                "DYNAMO_ENDPOINT_URL",
                "S3_ENDPOINT_URL",
                "SES_ENDPOINT_URL",
            ):
                with suppress(KeyError):
                    environ[key] = str(
                        environ[key]
                        .replace("127.0.0.1", environ["LOCALSTACK_HOSTNAME"])
                        .replace("localhost", environ["LOCALSTACK_HOSTNAME"])
                    )

        self._context = context
        self._event = event
        self._email = None
        self._sub = None
        self._no_auth = no_auth
        self._use_cognito = environ.get("USE_COGNITO", "1") == "1"
        self._cognito = Cognito() if self._use_cognito else None
        self._additional_headers = {}
        self._logger = getLogger(context.function_name)

    @property
    def cognito(self) -> "Cognito":
        """Get the Cognito."""
        if self._cognito is None:
            raise LambdaException("Cognito not set", 500)
        return self._cognito

    @property
    def context(self) -> "Context":
        """Get the context."""
        if self._context is None:
            raise LambdaException("Context not set", 500)
        return self._context

    @property
    def event(self) -> "Union[APIGatewayProxyEventV1, APIGatewayProxyEventV2]":
        """Get the event."""
        if self._event is None:
            raise LambdaException("Event not set", 500)
        return self._event

    @property
    def event_v1(self) -> "APIGatewayProxyEventV1":
        """Get the event v1."""
        if self._event is None:
            raise LambdaException("Event not set", 500)
        return self._event  # type: ignore

    @property
    def event_v2(self) -> "APIGatewayProxyEventV2":
        """Get the event v2."""
        if self._event is None:
            raise LambdaException("Event not set", 500)
        return self._event  # type: ignore

    @property
    def email(self) -> str:
        """Get the email."""
        if self._email is None:
            raise LambdaException("Email not set", 500)
        return self._email

    @property
    def sub(self) -> str:
        """Get the sub."""
        if self._sub is None:
            raise LambdaException("Sub not set", 500)
        return self._sub

    @property
    def body(self) -> dict[str, object]:
        """Get the body."""
        if "body" not in self.event:
            return {}
        if self.event["body"] is None:
            return {}
        return loads(self.event["body"])  # type: ignore

    @property
    def headers(self) -> dict[str, str]:
        """Get the headers with lowercased keys."""
        return {
            key.lower().strip(): value for key, value in self.event["headers"].items()
        }

    @property
    def file(self) -> Union[bytes, None]:
        """Get the file or None if none is present."""
        body = self.body
        if "file" not in body:
            return None
        if body["file"] is None:
            return None
        if isinstance(body["file"], bytes):
            return body["file"]
        if isinstance(body["file"], str):
            return b64decode(body["file"])
        return None

    @property
    def path(self) -> str:
        """Get the path."""
        if "rawPath" in self.event:
            return self.event["rawPath"]  # type: ignore
        return self.event["path"]  # type: ignore

    @property
    def http_method(self) -> str:
        """Get the HTTP method."""
        if "httpMethod" in self.event["requestContext"]:
            return self.event["requestContext"]["httpMethod"].strip().upper()  # type: ignore
        return self.event["requestContext"]["http"]["method"].strip().upper()  # type: ignore

    @property
    def path_params(self) -> dict[str, str]:
        """Get the path parameters with lowercased keys."""
        return (
            {
                key.lower().strip(): value
                for key, value in self.event["pathParameters"].items()
            }
            if self.event["pathParameters"] is not None
            else {}
        )

    @property
    def query_params(self) -> dict[str, str]:
        """Get the query parameters with lowercased keys."""
        return (
            {
                key.lower().strip(): value
                for key, value in self.event["queryStringParameters"].items()
            }
            if self.event["queryStringParameters"] is not None
            else {}
        )

    @property
    def logger(self) -> Logger:
        """Get the logger."""
        return self._logger

    @property
    def log(self) -> Logger:
        """Get the logger."""
        return self._logger

    @property
    def user(self) -> dict[str, str]:
        """Get the user."""
        return self.cognito.get_user_from_sub(self.sub)

    def add_header(self, key: str, value: str) -> None:
        """Add a header."""
        self._additional_headers[key] = value

    def http_error(self, status_code: int, message: str) -> None:
        """Raise an HTTP error."""
        raise LambdaException(message, status_code)

    def s3(self, key: str) -> "S3":
        """Get the S3 object."""
        return S3(key)

    def login(self, email: str, password: str) -> str:
        """Login."""
        return self.cognito.login(email, password)

    def register(
        self,
        email: str,
        password: str,
        data: dict[str, str],
        auto_validate: bool = False,
    ) -> None:
        """Register a new user."""
        self.cognito.register(email, password, data)
        if auto_validate:
            self.cognito.confirm_user(email)

    def get_user(
        self,
        event: "Union[APIGatewayProxyEventV1, APIGatewayProxyEventV2]",
    ) -> tuple[str, str]:
        """Get the user email and sub from the event."""
        if self._use_cognito and self._cognito is not None:
            try:
                auth_header = event["headers"].get("authorization")
                if auth_header is None:
                    event["headers"].get("Authorization")
                if auth_header is None:
                    raise LambdaException("Unauthorized", 403)
                email, sub = self._cognito.get_user_from_token(auth_header)
                return email, sub
            except Exception as err:
                raise LambdaException("Unauthorized", 403) from err
        try:
            authorizer = event["requestContext"]["authorizer"]
            if authorizer is None:
                raise LambdaException("Unauthorized", 403)
            if isinstance(authorizer, dict) and "claims" in authorizer:
                return authorizer["claims"]["email"], authorizer["claims"]["sub"]  # type: ignore
            email = authorizer["jwt"]["claims"]["email"]
            sub = authorizer["jwt"]["claims"]["sub"]
            return email, sub
        except KeyError as err:
            raise LambdaException("Unauthorized", 403) from err

    def __call__(
        self,
        function: Callable[
            [],
            Union[dict[str, object], list[object], None, str],
        ],
    ) -> Callable[[], "Union[APIGatewayProxyResponseV1, APIGatewayProxyResponseV2]",]:
        """Call the function."""

        def wrapped_function() -> (
            "Union[APIGatewayProxyResponseV1, APIGatewayProxyResponseV2]"
        ):
            """Wrapped function."""
            try:
                if self._no_auth is False:
                    self._email, self._sub = self.get_user(self._event)
                result = function()
                return return_body(
                    result,
                    200 if result is not None else 204,
                    self._additional_headers,
                )
            except LambdaException as err:
                return return_body(
                    payload=err.message,
                    status_code=err.code,
                    headers=self._additional_headers,
                )
            except Exception as err:  # pylint: disable=broad-except
                self._logger.exception(err)
                new_err = "\n".join(
                    format_exception(err.__class__, err, err.__traceback__)
                )
                return return_body(
                    payload=new_err,
                    status_code=500,
                    headers=self._additional_headers,
                )

        return wrapped_function
