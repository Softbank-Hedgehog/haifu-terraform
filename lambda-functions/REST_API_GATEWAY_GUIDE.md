# REST API Gateway 연동 가이드

## 📋 API Gateway 설정 정보

- **API 게이트웨이**: `haifu-dev-agent-api`
- **API 타입**: REST API
- **ARN**: `arn:aws:execute-api:ap-northeast-2:895169747692:ax1iakl8t8/*/*`
- **엔드포인트**: `https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod`
- **스테이지**: `prod`
- **리소스 경로**: `/{proxy+}`
- **메서드**: ANY
- **승인**: NONE (인증 없음)

---

## 🎯 지원되는 엔드포인트

### 1. **POST /prod/main** - 기획안 검토 및 일반 질의

**요청:**
```bash
curl -X POST https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod/main \
  -H "Content-Type: application/json" \
  -d '{
    "message": "React 프로젝트를 AWS에 배포하려고 합니다. 어떤 방법이 좋을까요?",
    "context": {
      "framework": "react",
      "scale": "small"
    }
  }'
```

**응답:**
```json
{
  "reply": "React 프로젝트의 경우 다음 배포 방법을 추천드립니다:\n\n1. **AWS Amplify** (가장 간단)..."
}
```

---

### 2. **POST /prod/chat** - 일반 챗봇 대화

**요청:**
```bash
curl -X POST https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "AWS Lambda의 장단점을 알려주세요"
  }'
```

**응답:**
```json
{
  "reply": "AWS Lambda의 주요 장단점은 다음과 같습니다:\n\n**장점:**\n1. 서버 관리 불필요..."
}
```

---

### 3. **POST /prod/deployment** - 정적/동적 배포 판단

**요청:**
```bash
curl -X POST https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod/deployment \
  -H "Content-Type: application/json" \
  -d '{
    "s3_snapshot": {
      "bucket": "haifu-dev-source-bucket",
      "s3_prefix": "user/123456/project-abc/service-web/20251122T100000Z-sourcefile"
    }
  }'
```

**응답:**
```json
{
  "deployment_type": "STATIC"
}
```

또는:
```json
{
  "deployment_type": "DYNAMIC"
}
```

---

### 4. **POST /prod/cost** - 비용 견적 (기본 엔드포인트)

**요청:**
```bash
curl -X POST https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod/cost \
  -H "Content-Type: application/json" \
  -d '{
    "s3_snapshot": {
      "bucket": "haifu-dev-source-bucket",
      "s3_prefix": "user/123456/project-abc/service-backend/20251122T100000Z-sourcefile"
    },
    "cpu": "1 vCPU",
    "memory": "2 GB"
  }'
```

**응답:**
```json
{
  "repository_analysis": {
    "framework": "fastapi",
    "language": "python",
    "runtime": "PYTHON_3",
    "has_dockerfile": true,
    "dependencies": []
  },
  "cost_estimation": {
    "service": "app_runner",
    "cpu": "1 vCPU",
    "memory": "2 GB",
    "estimated_monthly_cost_usd": 51.78,
    "breakdown": {
      "compute": 51.68,
      "data_transfer": 0.0,
      "build": 0.1
    },
    "runtime": "PYTHON_3",
    "framework": "fastapi",
    "usage_assumptions": {
      "uptime_percentage": 100.0,
      "traffic_level": "medium",
      "requests_per_month": 1000000
    },
    "cost_optimization_tips": [
      "Enable auto-scaling to reduce idle costs",
      "Use CloudFront CDN"
    ],
    "reasoning": "Standard production workload"
  }
}
```

---

## 🔄 경로 매핑

| 경로 | Action | 설명 |
|------|--------|------|
| `/prod/main` | `main` | 기획안 검토 및 일반 질의 |
| `/prod/chat` | `chat` | 일반 챗봇 대화 |
| `/prod/deployment` | `deployment_check` | 정적/동적 배포 판단 |
| `/prod/cost` | `cost` | 비용 견적 |
| `/prod/` (루트) | `cost` | 기본값: 비용 견적 |

---

## 🔧 REST API vs HTTP API 차이점

### REST API (현재 설정)

**이벤트 구조:**
```json
{
  "resource": "/{proxy+}",
  "path": "/prod/main",
  "httpMethod": "POST",
  "headers": {...},
  "body": "{...}",
  "requestContext": {
    "stage": "prod",
    "requestId": "...",
    ...
  }
}
```

**특징:**
- `event['path']` 사용 (스테이지 포함)
- `event['httpMethod']` 사용
- `event['requestContext']['stage']` 존재

### HTTP API (이전 설정)

**이벤트 구조:**
```json
{
  "version": "2.0",
  "routeKey": "$default",
  "rawPath": "/main",
  "requestContext": {
    "http": {
      "method": "POST",
      "path": "/main"
    }
  },
  "body": "{...}"
}
```

**특징:**
- `event['rawPath']` 사용 (스테이지 미포함)
- `event['requestContext']['http']['method']` 사용
- 더 간단한 구조

---

## 🧪 테스트 스크립트

### Python

```python
import requests
import json

BASE_URL = "https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod"

# 1. Main Query
response = requests.post(
    f"{BASE_URL}/main",
    json={
        "message": "FastAPI 프로젝트를 배포하려고 합니다.",
        "context": {"framework": "fastapi"}
    }
)
print("Main:", response.json()['reply'][:100])

# 2. Chat
response = requests.post(
    f"{BASE_URL}/chat",
    json={"message": "AWS Lambda란?"}
)
print("Chat:", response.json()['reply'][:100])

# 3. Deployment Check
response = requests.post(
    f"{BASE_URL}/deployment",
    json={
        "s3_snapshot": {
            "bucket": "haifu-dev-source-bucket",
            "s3_prefix": "user/123/proj/svc/20251122-sourcefile"
        }
    }
)
print("Deployment:", response.json()['deployment_type'])

# 4. Cost Estimation
response = requests.post(
    f"{BASE_URL}/cost",
    json={
        "s3_snapshot": {
            "bucket": "haifu-dev-source-bucket",
            "s3_prefix": "user/123/proj/svc/20251122-sourcefile"
        },
        "cpu": "1 vCPU",
        "memory": "2 GB"
    }
)
print("Cost:", response.json()['cost_estimation']['estimated_monthly_cost_usd'])
```

### JavaScript

```javascript
const BASE_URL = 'https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod';

// 1. Main Query
const mainResponse = await fetch(`${BASE_URL}/main`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'React 프로젝트 배포 방법',
    context: { framework: 'react' }
  })
});
const mainData = await mainResponse.json();
console.log('Main:', mainData.reply);

// 2. Chat
const chatResponse = await fetch(`${BASE_URL}/chat`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'AWS S3란?'
  })
});
const chatData = await chatResponse.json();
console.log('Chat:', chatData.reply);

// 3. Deployment Check
const deployResponse = await fetch(`${BASE_URL}/deployment`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    s3_snapshot: {
      bucket: 'haifu-dev-source-bucket',
      s3_prefix: 'user/123/proj/svc/20251122-sourcefile'
    }
  })
});
const deployData = await deployResponse.json();
console.log('Deployment Type:', deployData.deployment_type);

// 4. Cost Estimation
const costResponse = await fetch(`${BASE_URL}/cost`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    s3_snapshot: {
      bucket: 'haifu-dev-source-bucket',
      s3_prefix: 'user/123/proj/svc/20251122-sourcefile'
    },
    cpu: '2 vCPU',
    memory: '4 GB'
  })
});
const costData = await costResponse.json();
console.log('Monthly Cost:', costData.cost_estimation.estimated_monthly_cost_usd);
```

---

## ⚙️ Lambda 함수 수정 사항

### 주요 변경점

1. **경로 추출 로직 변경**
   - HTTP API의 `rawPath` → REST API의 `path` 사용
   - 스테이지 제거 로직 추가 (`/prod/main` → `/main`)

2. **이벤트 구조 대응**
   ```python
   # 이전 (HTTP API)
   raw_path = event.get('rawPath')
   
   # 현재 (REST API)
   request_path = event.get('path')
   stage = event.get('requestContext', {}).get('stage')
   ```

3. **CORS 헤더 유지**
   - REST API에서도 동일하게 CORS 헤더 반환

---

## 📊 에러 응답

### 400 Bad Request

```json
{
  "error": "s3_snapshot required"
}
```

### 404 Not Found

```json
{
  "error": "No files found"
}
```

### 500 Internal Server Error

```json
{
  "error": "Internal Server Error",
  "message": "Error details..."
}
```

---

## 🔐 보안 고려사항

### 현재 상태: 인증 없음 (NONE)

- ⚠️ 프로덕션 환경에서는 인증 추가 필요
- **권장 옵션**:
  1. **API Key**: 간단한 API 키 인증
  2. **IAM**: AWS IAM 권한 기반
  3. **Cognito**: 사용자 인증
  4. **Lambda Authorizer**: 커스텀 인증 로직

### API Key 추가 예시 (AWS Console)

1. API Gateway → API Keys → Create API Key
2. Usage Plans → Create → API 연결
3. 요청 시 헤더 추가:
   ```bash
   curl -H "x-api-key: YOUR_API_KEY" \
     https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod/cost
   ```

---

## 📈 모니터링

### CloudWatch Logs

Lambda 함수 로그 확인:
```bash
aws logs tail /aws/lambda/haifu-agent-lambda --follow
```

### 주요 로그

```
Received Event: {"path": "/prod/cost", "httpMethod": "POST", ...}
Processing API Gateway request
Request path: /prod/cost, Stage: prod, Method: POST
Clean path: /cost
Action from path: cost
```

---

## ✅ 체크리스트

- [x] REST API Gateway 이벤트 구조 지원
- [x] 경로 기반 라우팅 (`/main`, `/chat`, `/deployment`, `/cost`)
- [x] 스테이지 제거 로직 (`/prod/main` → `main`)
- [x] CORS 헤더 설정
- [x] 에러 핸들링
- [ ] 인증 추가 (프로덕션 필수)
- [ ] Rate limiting (API Gateway throttling)
- [ ] CloudWatch 알람 설정

---

## 🎉 완료!

Agent Lambda가 REST API Gateway와 정상적으로 연동되었습니다!

**Base URL**: `https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod`

**엔드포인트**:
- `/main` - 기획안 검토
- `/chat` - 일반 대화
- `/deployment` - 배포 타입 판단
- `/cost` - 비용 견적

