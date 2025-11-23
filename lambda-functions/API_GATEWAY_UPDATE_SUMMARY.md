# REST API Gateway 연동 업데이트 요약

## 📋 변경 사항

### 1. **agent_lambda.py** - Lambda 함수 수정

#### ✅ 경로 추출 로직 변경

**이전 (HTTP API):**
```python
raw_path = event.get('rawPath')  # "/main"
```

**현재 (REST API):**
```python
request_path = event.get('path')  # "/prod/main"
stage = event.get('requestContext', {}).get('stage')  # "prod"

# 스테이지 제거
if stage and request_path.startswith(f'/{stage}/'):
    clean_path = request_path[len(stage) + 1:]  # "/main"
```

#### ✅ 경로별 Action 매핑

| 요청 경로 | Action | 기능 |
|-----------|--------|------|
| `/prod/main` | `main` | 기획안 검토 |
| `/prod/chat` | `chat` | 일반 대화 |
| `/prod/deployment` | `deployment_check` | 배포 타입 판단 |
| `/prod/cost` | `cost` | 비용 견적 |

---

### 2. **app/routers/agent.py** - FastAPI Router 업데이트

#### ✅ API Gateway 우선 사용

```python
class AgentLambdaClient:
    def __init__(self):
        # REST API Gateway 사용 (기본값)
        self.use_api_gateway = True
        self.api_gateway_url = "https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod"
```

#### ✅ 두 가지 호출 방식 지원

1. **REST API Gateway** (권장)
   ```python
   def _invoke_via_api_gateway(self, payload, action):
       url = f"{self.api_gateway_url}/{action}"
       response = requests.post(url, json=payload)
   ```

2. **Lambda 직접 invoke** (Fallback)
   ```python
   def _invoke_via_lambda(self, payload):
       self.lambda_client.invoke(FunctionName=..., Payload=...)
   ```

---

### 3. **환경 변수 설정**

#### `.env` 파일

```bash
# REST API Gateway 사용 (권장)
USE_API_GATEWAY=true
AGENT_API_GATEWAY_URL=https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod

# 또는 Lambda 직접 invoke
# USE_API_GATEWAY=false
# AGENT_LAMBDA_FUNCTION_NAME=haifu-agent-lambda
```

---

## 🎯 API Gateway 설정 정보

- **API 게이트웨이**: `haifu-dev-agent-api`
- **API 타입**: REST API
- **엔드포인트**: `https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod`
- **스테이지**: `prod`
- **리소스 경로**: `/{proxy+}`
- **메서드**: ANY
- **승인**: NONE

---

## 🧪 테스트 방법

### 1. REST API Gateway 직접 호출

```bash
# Main Query
curl -X POST https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod/main \
  -H "Content-Type: application/json" \
  -d '{"message": "React 프로젝트 배포 방법을 알려주세요"}'

# Chat
curl -X POST https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "AWS Lambda란?"}'

# Deployment Check
curl -X POST https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod/deployment \
  -H "Content-Type: application/json" \
  -d '{"s3_snapshot": {"bucket": "...", "s3_prefix": "..."}}'

# Cost Estimation
curl -X POST https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod/cost \
  -H "Content-Type: application/json" \
  -d '{"s3_snapshot": {"bucket": "...", "s3_prefix": "..."}, "cpu": "1 vCPU", "memory": "2 GB"}'
```

### 2. Python 테스트 스크립트

```bash
# Lambda 함수 직접 테스트
cd haifu-terraform/lambda-functions
python test_rest_api.py

# FastAPI Router 테스트
cd haifu-chatbot-standalone
python test_agent_api.py
```

---

## 🔄 아키텍처

### 이전 (HTTP API)

```
Frontend → FastAPI → Lambda (직접 invoke)
```

### 현재 (REST API Gateway)

```
Frontend → FastAPI → REST API Gateway → Lambda
                                ↓
                          (경로 기반 라우팅)
```

---

## 📊 REST API vs HTTP API 차이

| 항목 | REST API | HTTP API |
|------|----------|----------|
| **경로 필드** | `event['path']` | `event['rawPath']` |
| **스테이지** | 경로에 포함 (`/prod/main`) | 경로에 미포함 (`/main`) |
| **HTTP 메서드** | `event['httpMethod']` | `event['requestContext']['http']['method']` |
| **비용** | 약간 높음 | 저렴 |
| **기능** | 더 많은 기능 | 간단하고 빠름 |

---

## ✅ 완료 체크리스트

- [x] Lambda 함수 REST API 이벤트 구조 지원
- [x] 스테이지 제거 로직 (`/prod/main` → `main`)
- [x] 경로 기반 라우팅 (`/main`, `/chat`, `/deployment`, `/cost`)
- [x] FastAPI Router API Gateway 호출 지원
- [x] 환경 변수 기반 호출 방식 선택
- [x] 테스트 스크립트 작성
- [x] 문서화

---

## 🎉 완료!

Agent Lambda가 REST API Gateway와 완전히 연동되었습니다!

**엔드포인트**: `https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod`

**지원 기능**:
- ✅ Main Query (기획안 검토)
- ✅ Chat (일반 대화)
- ✅ Deployment Check (배포 타입 판단)
- ✅ Cost Estimation (비용 견적)

**클라이언트 통합**:
- FastAPI Router가 API Gateway를 통해 Lambda 호출
- 환경 변수로 직접 invoke도 지원
- CORS 헤더 자동 추가

