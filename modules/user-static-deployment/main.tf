# User Static Deployment Module
# This module creates infrastructure for deploying user static sites
# Includes S3, CloudFront, and CodePipeline for automated deployments

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Local values for resource naming
locals {
  resource_prefix = "haifu-user-${var.user_id}-${var.project_name}"
  
  common_tags = merge(var.tags, {
    Module  = "user-static-deployment"
    UserId  = var.user_id
    Project = var.project_name
    Type    = "UserStaticSite"
  })
}