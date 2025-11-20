# Minimal Deployment Example

This example shows how to deploy a minimal infrastructure using the Haifu Terraform modules.

## Prerequisites

- AWS CLI configured
- Terraform >= 1.0 installed

## Quick Start

1. Copy the example configuration:
```bash
cp env/terraform.tfvars.example env/terraform.tfvars
```

2. Edit `env/terraform.tfvars` with your values

3. Initialize and apply:
```bash
terraform init
terraform plan -var-file="env/terraform.tfvars"
terraform apply -var-file="env/terraform.tfvars"
```

## Example Configuration

```hcl
module "vpc" {
  source = "./modules/vpc"
  
  name_prefix        = local.name_prefix
  availability_zones = ["us-west-2a", "us-west-2b"]
  tags              = local.common_tags
}

module "alb" {
  source = "./modules/alb"
  
  name_prefix        = local.name_prefix
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.public_subnet_ids
  security_group_ids = [module.vpc.default_security_group_id]
  tags              = local.common_tags
}
```

## Clean Up

```bash
terraform destroy -var-file="env/terraform.tfvars"
```