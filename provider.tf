provider "aws" {
  region = var.aws_region
  
  # DNS 해석 문제 해결을 위한 엔드포인트 설정
  endpoints {
    ec2 = "https://ec2.ap-northeast-2.amazonaws.com"
    ecs = "https://ecs.ap-northeast-2.amazonaws.com"
    s3  = "https://s3.ap-northeast-2.amazonaws.com"
  }
  
  # 재시도 설정
  retry_mode      = "adaptive"
  max_retries     = 3
  
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# CloudFront용 ACM 인증서는 반드시 us-east-1에 있어야 함
provider "aws" {
  alias  = "us-east-1"
  region = "us-east-1"
}
