FROM python:3.11-alpine

ENV AWS_DEFAULT_REGION=eu-west-1 \
    AWS_ACCESS_KEY_ID=test \
    AWS_SECRET_ACCESS_KEY=test \
    AWS_ENDPOINT_URL=http://aws:4566

WORKDIR /app

RUN pip install boto3 fastapi uvicorn

ADD ./aws_api_gateway_local ./aws_api_gateway_local
ADD ./routes.json ./routes.json

EXPOSE 9000

CMD python -m aws_api_gateway_local --port 9000
