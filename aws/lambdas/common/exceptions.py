"""Lambda exceptions"""


class LambdaException(Exception):
    """Lambda exception."""

    message: str
    code: int

    def __init__(self, message: str, code: int) -> None:
        """Initialize the Lambda exception."""
        self.message = message
        self.code = code
        super().__init__(message)
