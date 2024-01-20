"""Login a user."""
from common import LambdaDecorator


def lambda_handler(event, context) -> dict[str, str]:  # type: ignore
    """Login a user."""

    helper = LambdaDecorator(event, context, no_auth=True)

    @helper  # type: ignore
    def inner_function() -> dict[str, str]:
        """Inner function."""
        email = helper.body["email"].lower()
        password = helper.body["password"]
        token = helper.cognito.login(email, password)
        return {
            "access_token": token,
            "token_type": "Bearer",
        }

    return inner_function()  # type: ignore
