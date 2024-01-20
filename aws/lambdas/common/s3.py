"""Common utilities for S3."""
from io import BytesIO, StringIO
from os import environ
from contextlib import suppress
from typing import Union, cast, Literal, overload
from zipfile import ZipFile
from boto3 import client

with suppress(ImportError):
    from boto3_type_annotations.s3 import Client as S3Client


class S3:
    """Common utilities for S3.

    Example:
    ```python
    with S3("testId/test1.zip") as s3:
        with s3.read("test.txt") as f:
            print(f.read())
    ```
    """

    s3: "S3Client"
    key: str
    _buffer: BytesIO
    _files: list[tuple[str, BytesIO]]

    def __init__(self, key: str, bucket_name: Union[str, None] = None) -> None:
        """Initialize the S3 object.

        Args:
            bucket_name (str): The name of the bucket.
        """
        self.key = key
        if bucket_name is None:
            bucket_name = environ.get("S3_BUCKET_NAME", "test-s3-bucket")
        self.bucket_name = bucket_name
        self._buffer = BytesIO()
        self._files = []
        self.s3 = client(
            "s3",
            region_name=environ.get("AWS_DEFAULT_REGION", None),
            aws_access_key_id=environ.get("AWS_ACCESS_KEY_ID", None),
            aws_secret_access_key=environ.get("AWS_SECRET_ACCESS_KEY", None),
            endpoint_url=environ.get("S3_ENDPOINT_URL", None),
        )

    def download(self) -> None:
        """Download a file from S3."""
        self._buffer = BytesIO()
        value: bytes = cast(
            BytesIO,
            self.s3.get_object(
                Bucket=self.bucket_name,
                Key=self.key,
            )["Body"],
        ).read()
        self._buffer.write(value)

    def unzip(self) -> None:
        """Unzip a file from S3."""
        with ZipFile(self._buffer, "r") as zip_obj:
            for filename in zip_obj.namelist():
                self._files.append((filename, BytesIO(zip_obj.read(filename))))

    def upload(self) -> None:
        """Upload a file to S3."""
        self.s3.put_object(
            Bucket=self.bucket_name, Key=self.key, Body=self._buffer.getvalue()
        )

    def zip(self) -> None:
        """Zip a file."""
        buffer = BytesIO()
        with ZipFile(
            buffer,
            "w",
        ) as zip_obj:
            for filename, file_buffer in self._files:
                zip_obj.writestr(filename, file_buffer.getvalue())

        self._buffer = BytesIO()
        self._buffer.write(buffer.getvalue())

    def __enter__(self) -> "S3":
        """Enter the context."""
        with suppress(Exception):
            self.download()
            self.unzip()
        return self

    # pylint: disable=unused-argument
    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore
        """Exit the context."""
        self.zip()
        self.upload()

    def write(self, filename: str, data: Union[str, bytes]) -> None:
        """Write a file to the zip file"""
        if not isinstance(data, bytes):
            data = data.encode("utf-8")
        for i, file in enumerate(self._files):
            if file[0] == filename:
                self._files[i] = (filename, BytesIO(data))
                return
        self._files.append((filename, BytesIO(data)))

    @overload
    def read(self, filename: str, encoding: Literal["utf-8"]) -> StringIO:
        pass

    @overload
    def read(self, filename: str, encoding: None = None) -> BytesIO:
        pass

    def read(
        self,
        filename: str,
        encoding: Union[Literal["utf-8"], None] = None,
    ) -> Union[BytesIO, StringIO]:
        """Read a file from the zip file"""
        for file in self._files:
            if file[0] == filename:
                if encoding:
                    return StringIO(file[1].read().decode(encoding))
                return file[1]
        raise FileNotFoundError

    def file_exists(self, filename: str) -> bool:
        """Check if a file exists in the zip file"""
        for file in self._files:
            if file[0] == filename:
                return True
        return False

    @property
    def exists(self) -> bool:
        """Check if the file exists."""
        # pylint: disable=broad-except
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=self.key)
            return True
        except Exception:
            return False

    @property
    def empty(self) -> bool:
        """Check if the file is empty."""
        return len(self._buffer.getvalue()) == 0
