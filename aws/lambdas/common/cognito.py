"""Common utilities for Cognito."""
from os import environ
from contextlib import suppress
from boto3 import client

with suppress(ImportError):
    from boto3_type_annotations.cognito_idp import Client as CognitoClient


class Cognito:
    """Cognito class."""

    client: "CognitoClient"

    def __init__(self) -> None:
        """Initialize the Cognito class."""
        self.client = client(
            "cognito-idp",
            region_name=environ.get("AWS_DEFAULT_REGION", None),
            aws_access_key_id=environ.get("AWS_ACCESS_KEY_ID", None),
            aws_secret_access_key=environ.get("AWS_SECRET_ACCESS_KEY", None),
            endpoint_url=environ.get("COGNITO_ENDPOINT_URL", None),
        )

    def register(self, email: str, password: str, data: dict[str, str]) -> None:
        """Register a new user.

        Args:
            email (str): The email of the user.
            password (str): The password of the user.
        """
        attributes = [
            {"Name": "email", "Value": email},
        ]
        for key, value in data.items():
            attributes.append({"Name": key, "Value": value})
        self.client.sign_up(
            ClientId=environ.get("COGNITO_CLIENT_ID", None),
            Username=email,
            Password=password,
            UserAttributes=attributes,
        )

    def login(self, email: str, password: str) -> str:
        """Login a user.

        Args:
            email (str): The email of the user.
            password (str): The password of the user.

        Returns:
            str: The access token.
        """
        response = self.client.initiate_auth(
            ClientId=environ.get("COGNITO_CLIENT_ID", None),
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": email,
                "PASSWORD": password,
            },
        )
        return response["AuthenticationResult"]["AccessToken"]  # type: ignore

    def get_user_from_token(self, token: str) -> tuple[str, str]:
        """Get the Cognito user from the token.

        Args:
            token (str): The token.

        Returns:
            str: The Cognito user.
        """
        if token.startswith("Bearer "):
            token = token.replace("Bearer ", "")
        # Verify the authorization token
        response = self.client.get_user(AccessToken=token)

        # Get the user attributes
        user_attributes = response["UserAttributes"]

        # Extract the email and sub attributes
        email: str = ""
        sub: str = ""

        for attribute in user_attributes:
            if attribute["Name"] == "email":
                email = attribute["Value"]
            elif attribute["Name"] == "sub":
                sub = attribute["Value"]
        if email == "" or sub == "":
            raise KeyError("Email or sub not found in user attributes")
        return email, sub

    def get_user_from_sub(self, sub: str) -> dict[str, str]:
        """Get the Cognito user from the sub.

        Args:
            sub (str): The sub.

        Returns:
            str: The Cognito user.
        """
        response = self.client.admin_get_user(
            UserPoolId=environ.get("COGNITO_USER_POOL_ID", None),
            Username=sub,
        )
        return {val["Name"]: val["Value"] for val in response["UserAttributes"]}

    def confirm_user(self, email: str) -> None:
        """Confirm a user.

        Args:
            email (str): The email of the user.
        """
        self.client.admin_confirm_sign_up(
            UserPoolId=environ.get("COGNITO_USER_POOL_ID", None),
            Username=email,
        )
