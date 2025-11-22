# Secrets 관리 가이드

## AWS Secrets Manager를 통한 안전한 Secret 관리

### 1. Terraform으로 Secret 생성
```bash
terraform apply
```

### 2. Secret 값 업데이트 (실제 값으로 변경)
```bash
aws secretsmanager put-secret-value \
  --secret-id "haifu-server/main" \
  --secret-string '{
    "ENVIRONMENT": "dev",
    "GITHUB_CLIENT_ID": "your-github-oauth-client-id",
    "GITHUB_CLIENT_SECRET": "your-github-oauth-client-secret", 
    "JWT_SECRET_KEY": "your-random-jwt-secret-key",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRE_DAYS": "7",
    "FRONTEND_URL": "https://your-frontend-domain.com",
    "DYNAMODB_PROJECTS_TABLE": "haifu-dev-projects",
    "DYNAMODB_SERVICES_TABLE": "haifu-dev-services",
    "PORT": "8000"
  }' \
  --region ap-northeast-2
```

### 3. Secret 확인
```bash
aws secretsmanager get-secret-value \
  --secret-id "haifu-server/main" \
  --region ap-northeast-2
```

### 보안 장점
- ✅ Terraform 코드에 민감한 정보 없음
- ✅ Git 히스토리에 Secret 노출 방지
- ✅ AWS IAM을 통한 접근 제어
- ✅ Secret 자동 로테이션 지원
- ✅ 암호화된 저장