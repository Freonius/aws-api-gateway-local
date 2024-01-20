"""Register a new user."""
from common import LambdaDecorator


def lambda_handler(event, context) -> str:  # type: ignore
    """Register a new user."""

    helper = LambdaDecorator(event, context, no_auth=True)

    @helper  # type: ignore
    def inner_function() -> str:
        """Inner function."""
        email = helper.body["email"].lower()
        password = helper.body["password"]
        data = {
            "given_name": helper.body["first_name"],
            "family_name": helper.body["last_name"],
        }
        helper.cognito.register(email, password, data)
        helper.cognito.confirm_user(email)
        return ""

    return inner_function()  # type: ignore
