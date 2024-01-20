"""AWS API gateway local server."""
from argparse import ArgumentParser
from . import run

parser: ArgumentParser = ArgumentParser()
parser.add_argument(
    "--port",
    type=int,
    default=9000,
    help="The port to listen on",
)

if __name__ == "__main__":
    args = parser.parse_args()
    run(port=args.port)
