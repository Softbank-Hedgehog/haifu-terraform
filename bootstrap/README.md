# Bootstrap Infrastructure

이 디렉토리는 Terraform 원격 state 관리를 위한 S3 버킷과 DynamoDB 테이블을 생성합니다.

## 사용 방법

1. **Bootstrap 리소스 생성:**
```bash
cd bootstrap
terraform init
terraform plan
terraform apply
```

2. **메인 프로젝트에서 원격 state 사용:**
```bash
cd ..
terraform init  # backend 설정이 적용됨
```

## 생성되는 리소스

- **S3 버킷**: `haifu-terraform-state` (state 파일 저장)
- **DynamoDB 테이블**: `terraform-lock` (state lock)

## 주의사항

- Bootstrap 리소스는 한 번만 생성하면 됩니다
- 삭제 시 주의: state 파일이 손실될 수 있습니다