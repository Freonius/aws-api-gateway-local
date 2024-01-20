# AWS API Gateway Local

![Medium](https://img.shields.io/badge/Medium-12100E?style=for-the-badge&logo=medium&logoColor=white)![AWS](https://img.shields.io/badge/AWS-%23FF9900.svg?style=for-the-badge&logo=amazon-aws&logoColor=white)![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)![Terraform](https://img.shields.io/badge/terraform-%235835CC.svg?style=for-the-badge&logo=terraform&logoColor=white)![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)

A small example of how you can test your lambdas locally like, simulating how they should behave behind an API Gateway on AWS.

There is an article on Medium [here](https://medium.com/@freonius/test-an-aws-api-gateway-locally-b869249090f6).

## TLDR

Run these commands

```bash
docker-compose -f "./docker-compose.yml" up -d --build
cd aws
terraform init
terraform apply -auto-approve
```

and go to [http://localhost:9001](http://localhost:9001) to try it out.

Obviously you need docker and terraform.

## Budget to run this?

0.00 EUR (equivalent to 0.00 USD)
