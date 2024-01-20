"""Get the data."""
from json import loads
from common import LambdaDecorator


def lambda_handler(event, context) -> list[object]:  # type: ignore
    """Get the data."""
    helper = LambdaDecorator(event, context, no_auth=False)

    @helper  # type: ignore
    def inner_function():
        """Inner function."""
        if helper.http_method != "GET":
            helper.http_error(405, "Method not allowed")
        with helper.s3(f"{helper.sub}.zip") as s3:
            if s3.file_exists("data.json"):
                with s3.read("data.json", encoding="utf-8") as f:
                    return loads(f.read())
            helper.http_error(404, "Not found")

    return inner_function()  # type: ignore
