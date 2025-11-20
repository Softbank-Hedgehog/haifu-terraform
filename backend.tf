terraform {
  backend "s3" {
    bucket         = "haifu-terraform-state"
    key            = "terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}