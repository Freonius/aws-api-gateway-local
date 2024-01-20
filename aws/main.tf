# These variables set the correct endpoint for local development
variable "use_local_endpoint" {
  type    = bool
  default = true
}

variable "localstack_endpoint" {
  type    = string
  default = "http://127.0.0.1:4566"
}

variable "dynamodb_endpoint" {
  type    = string
  default = "http://127.0.0.1:4566"
}

variable "cognito_endpoint" {
  type    = string
  default = "http://127.0.0.1:9229"
}

variable "s3_endpoint" {
  type    = string
  default = "http://127.0.0.1:4566"
}

variable "current_env" {
  type    = string
  default = "Local"
}

variable "aws_region" {
  type    = string
  default = "eu-west-1"
}

# Define provider and region
provider "aws" {
  region     = var.aws_region
  access_key = var.use_local_endpoint ? "test" : null
  secret_key = var.use_local_endpoint ? "test" : null
  endpoints {
    lambda       = var.use_local_endpoint ? var.localstack_endpoint : null
    logs         = var.use_local_endpoint ? var.localstack_endpoint : null
    s3           = var.use_local_endpoint ? var.localstack_endpoint : null
    dynamodb     = var.use_local_endpoint ? var.dynamodb_endpoint : null
    apigateway   = var.use_local_endpoint ? var.localstack_endpoint : null
    apigatewayv2 = var.use_local_endpoint ? var.localstack_endpoint : null
    iam          = var.use_local_endpoint ? var.localstack_endpoint : null
    ses          = var.use_local_endpoint ? var.localstack_endpoint : null
    cloudwatch   = var.use_local_endpoint ? var.localstack_endpoint : null

    cognitoidentityprovider = var.use_local_endpoint ? var.cognito_endpoint : null
  }
  s3_use_path_style           = var.use_local_endpoint
  skip_credentials_validation = var.use_local_endpoint
  skip_metadata_api_check     = var.use_local_endpoint
  skip_requesting_account_id  = var.use_local_endpoint
  default_tags {
    tags = {
      Environment = var.current_env
      Name        = "AWS API Gateway Local"
      Service     = "AWS API Gateway Local"
    }
  }
}

# Create Cognito User Pool
resource "aws_cognito_user_pool" "cognito_user_pool" {
  name = "test-user-pool"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  schema {
    name                = "email"
    attribute_data_type = "String"
    mutable             = true
    required            = true
  }
  mfa_configuration = "OFF"
  software_token_mfa_configuration {
    enabled = false
  }

  password_policy {
    minimum_length    = var.use_local_endpoint ? 6 : 8
    require_lowercase = true
    require_uppercase = var.use_local_endpoint ? false : true
    require_numbers   = var.use_local_endpoint ? false : true
    require_symbols   = var.use_local_endpoint ? false : true
  }
}

resource "aws_cognito_user_pool_client" "cognito_client" {
  name                                 = "test-user-pool-client"
  user_pool_id                         = aws_cognito_user_pool.cognito_user_pool.id
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  callback_urls                        = ["http://localhost:3500"]
  allowed_oauth_flows_user_pool_client = true
  token_validity_units {
    access_token  = "days"
    refresh_token = "days"
    id_token      = "days"
  }
}

output "user_pool_id" {
  value = aws_cognito_user_pool.cognito_user_pool.id
}

output "user_pool_client_id" {
  value = aws_cognito_user_pool_client.cognito_client.id
}

# S3
# Create S3 bucket (minimal example)
resource "aws_s3_bucket" "s3" {
  bucket = "test-s3-bucket"
}

# Api gateway V1
resource "aws_api_gateway_rest_api" "api_gateway" {
  count       = var.use_local_endpoint ? 0 : 1
  name        = "test-api"
  description = "Test API"
}

# Et cetera...

# Lambda trigger
variable "lambda_root" {
  type        = string
  description = "The relative path to the source of the lambda"
  default     = "./lambdas"
}

resource "null_resource" "install_dependencies" {
  provisioner "local-exec" {
    command = "bash ${var.lambda_root}/zip-lambdas.sh"
  }

  triggers = {
    get_data_versions         = filemd5("${var.lambda_root}/get_data.py"),
    post_data_versions        = filemd5("${var.lambda_root}/post_data.py"),
    login_versions            = filemd5("${var.lambda_root}/login.py"),
    register_versions         = filemd5("${var.lambda_root}/register.py"),
    common_s3_versions        = filemd5("${var.lambda_root}/common/s3.py"),
    common_cognito_versions   = filemd5("${var.lambda_root}/common/cognito.py"),
    common_exception_versions = filemd5("${var.lambda_root}/common/exceptions.py"),
    common_helper_versions    = filemd5("${var.lambda_root}/common/lambda_helpers.py"),
    common_init_versions      = filemd5("${var.lambda_root}/common/__init__.py"),

    # TODO: Other files
  }
}

resource "aws_iam_role" "lambda_execution_role" {
  name = "lambda-execution-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda_execution_policy_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "lambda_execution_policy" {
  name   = "lambda-execution-policy"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData",
        "cloudwatch:GetMetricData",
        "cognito-idp:AdminGetUser",
        "cognito-idp:AdminUpdateUserAttributes",
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_policy_attachment" "lambda_execution_policy_attachment" {
  name       = "lambda-execution-policy-attachment"
  roles      = [aws_iam_role.lambda_execution_role.name]
  policy_arn = aws_iam_policy.lambda_execution_policy.arn
}

# Lambdas
resource "aws_lambda_function" "get_data_lambda" {
  function_name    = "get_data"
  role             = aws_iam_role.lambda_execution_role.arn
  filename         = "${var.lambda_root}/get_data.zip"
  source_code_hash = base64sha256("${var.lambda_root}/get_data.zip")

  handler = "get_data.lambda_handler"
  runtime = "python3.9"
  timeout = 30

  environment {
    variables = {
      LOG_LEVEL             = "info"
      AWS_DEFAULT_REGION    = var.use_local_endpoint ? "eu-west-1" : ""
      AWS_ACCESS_KEY_ID     = var.use_local_endpoint ? "test" : ""
      AWS_SECRET_ACCESS_KEY = var.use_local_endpoint ? "test" : ""
      ALLOW_CORS            = var.use_local_endpoint ? "1" : "0"
      USE_COGNITO           = var.use_local_endpoint ? "1" : "0"
      LOGGER_NAME           = "get_data"
      COGNITO_CLIENT_ID     = aws_cognito_user_pool_client.cognito_client.id
      COGNITO_USER_POOL_ID  = aws_cognito_user_pool.cognito_user_pool.id
      COGNITO_ENDPOINT_URL  = var.use_local_endpoint ? "http://cognito:9229" : ""
      S3_ENDPOINT_URL       = var.use_local_endpoint ? var.s3_endpoint : ""
      S3_BUCKET_NAME        = aws_s3_bucket.s3.bucket
      LOCALSTACK_HOSTNAME   = var.use_local_endpoint ? "aws" : "",
    }
  }
}

resource "aws_lambda_function" "post_data_lambda" {
  function_name    = "post_data"
  role             = aws_iam_role.lambda_execution_role.arn
  filename         = "${var.lambda_root}/post_data.zip"
  source_code_hash = base64sha256("${var.lambda_root}/post_data.zip")

  handler = "post_data.lambda_handler"
  runtime = "python3.9"
  timeout = 30

  environment {
    variables = {
      LOG_LEVEL             = "info"
      AWS_DEFAULT_REGION    = var.use_local_endpoint ? "eu-west-1" : ""
      AWS_ACCESS_KEY_ID     = var.use_local_endpoint ? "test" : ""
      AWS_SECRET_ACCESS_KEY = var.use_local_endpoint ? "test" : ""
      ALLOW_CORS            = var.use_local_endpoint ? "1" : "0"
      USE_COGNITO           = var.use_local_endpoint ? "1" : "0"
      LOGGER_NAME           = "post_data"
      COGNITO_CLIENT_ID     = aws_cognito_user_pool_client.cognito_client.id
      COGNITO_USER_POOL_ID  = aws_cognito_user_pool.cognito_user_pool.id
      COGNITO_ENDPOINT_URL  = var.use_local_endpoint ? "http://cognito:9229" : ""
      S3_ENDPOINT_URL       = var.use_local_endpoint ? var.s3_endpoint : ""
      S3_BUCKET_NAME        = aws_s3_bucket.s3.bucket
      LOCALSTACK_HOSTNAME   = var.use_local_endpoint ? "aws" : "",
    }
  }
}

resource "aws_lambda_function" "login_lambda" {
  function_name    = "login"
  role             = aws_iam_role.lambda_execution_role.arn
  filename         = "${var.lambda_root}/login.zip"
  source_code_hash = base64sha256("${var.lambda_root}/login.zip")

  handler = "login.lambda_handler"
  runtime = "python3.9"
  timeout = 30

  environment {
    variables = {
      LOG_LEVEL             = "info"
      AWS_DEFAULT_REGION    = var.use_local_endpoint ? "eu-west-1" : ""
      AWS_ACCESS_KEY_ID     = var.use_local_endpoint ? "test" : ""
      AWS_SECRET_ACCESS_KEY = var.use_local_endpoint ? "test" : ""
      ALLOW_CORS            = var.use_local_endpoint ? "1" : "0"
      USE_COGNITO           = var.use_local_endpoint ? "1" : "0"
      LOGGER_NAME           = "login"
      COGNITO_CLIENT_ID     = aws_cognito_user_pool_client.cognito_client.id
      COGNITO_USER_POOL_ID  = aws_cognito_user_pool.cognito_user_pool.id
      COGNITO_ENDPOINT_URL  = var.use_local_endpoint ? "http://cognito:9229" : ""
      S3_ENDPOINT_URL       = var.use_local_endpoint ? var.s3_endpoint : ""
      S3_BUCKET_NAME        = aws_s3_bucket.s3.bucket
      LOCALSTACK_HOSTNAME   = var.use_local_endpoint ? "aws" : "",
    }
  }
}

resource "aws_lambda_function" "register_lambda" {
  function_name    = "register"
  role             = aws_iam_role.lambda_execution_role.arn
  filename         = "${var.lambda_root}/register.zip"
  source_code_hash = base64sha256("${var.lambda_root}/register.zip")

  handler = "register.lambda_handler"
  runtime = "python3.9"
  timeout = 30

  environment {
    variables = {
      LOG_LEVEL             = "info"
      AWS_DEFAULT_REGION    = var.use_local_endpoint ? "eu-west-1" : ""
      AWS_ACCESS_KEY_ID     = var.use_local_endpoint ? "test" : ""
      AWS_SECRET_ACCESS_KEY = var.use_local_endpoint ? "test" : ""
      ALLOW_CORS            = var.use_local_endpoint ? "1" : "0"
      USE_COGNITO           = var.use_local_endpoint ? "1" : "0"
      LOGGER_NAME           = "register"
      COGNITO_CLIENT_ID     = aws_cognito_user_pool_client.cognito_client.id
      COGNITO_USER_POOL_ID  = aws_cognito_user_pool.cognito_user_pool.id
      COGNITO_ENDPOINT_URL  = var.use_local_endpoint ? "http://cognito:9229" : ""
      S3_ENDPOINT_URL       = var.use_local_endpoint ? var.s3_endpoint : ""
      S3_BUCKET_NAME        = aws_s3_bucket.s3.bucket
      LOCALSTACK_HOSTNAME   = var.use_local_endpoint ? "aws" : "",
    }
  }
}

