"""Post the data."""
from json import dumps
from common import LambdaDecorator


def lambda_handler(event, context) -> list[object]:  # type: ignore
    """Post the data."""
    helper = LambdaDecorator(event, context, no_auth=False)

    @helper  # type: ignore
    def inner_function():
        """Inner function."""
        if helper.http_method not in ("POST", "PUT"):
            helper.http_error(405, "Method not allowed")
        with helper.s3(f"{helper.sub}.zip") as s3:
            s3.write("data.json", dumps(helper.body).encode("utf-8"))

    return inner_function()  # type: ignore
