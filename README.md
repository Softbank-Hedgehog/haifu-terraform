# hAIfu Terraform Infrastructure

**AI 기반 자동 배포 플랫폼을 위한 AWS 인프라스트럭처**

hAIfu는 배포 전 과정의 설정값을 AI Agent가 직접 결정해주는 혁신적인 배포 플랫폼입니다. 사용자는 GitHub 저장소 연결만으로 정적/동적 서비스를 원클릭 배포할 수 있습니다.

## 🎯 프로젝트 목표

- **AI 기반 자동화**: 빌드 명령, 런타임, 환경변수, 서버 스펙을 AI가 자동 추천
- **정적/동적 통합 배포**: S3+CloudFront와 ECS Fargate를 자동 선택하여 배포
- **실시간 모니터링**: EventBridge 기반 실시간 로그 스트리밍 및 AI Summary
- **원클릭 CI/CD**: CodePipeline을 통한 완전 자동화된 배포 파이프라인

## 📁 프로젝트 구조

```
haifu-terraform/
├── bootstrap/              # Terraform 원격 상태 관리 (S3 + DynamoDB)
├── modules/                # 재사용 가능한 Terraform 모듈
│   ├── vpc/               # VPC, 서브넷, 보안 그룹
│   ├── alb/               # Application Load Balancer
│   ├── ecs-fargate/       # ECS Fargate 클러스터 (동적 서비스용)
│   ├── lambda/            # AI Agent 및 배포 Lambda 함수
│   ├── iam/               # IAM 역할 및 정책
│   ├── s3-cloudfront/     # S3 + CloudFront (정적 사이트용)
│   ├── codepipeline/      # CI/CD 파이프라인
│   └── eventbridge/       # 실시간 이벤트 처리
├── env/                   # 환경별 설정 (dev, prod)
├── lambda-functions/      # Lambda 함수 소스 코드
└── buildspec-example.yml  # CodeBuild 빌드 스펙 예시
```

## 🏗️ 인프라 아키텍처

### AI Agent 및 백엔드
- **Lambda Functions**: AI Agent, 배포 처리, 실시간 상태 업데이트
- **Amazon Bedrock**: LLM 모델 호출 (Claude, Llama)
- **S3**: RAG 기반 프로젝트 파일 저장 및 분석
- **FastAPI on ECS Fargate**: 백엔드 API 서버

### CI/CD 파이프라인
- **CodePipeline**: 배포 파이프라인 오케스트레이션
- **CodeBuild**: 빌드, 테스트, Docker 이미지 생성
- **ECR**: Docker 이미지 저장소
- **CodeDeploy**: ECS Fargate 자동 배포

### 배포 대상
- **정적 사이트**: S3 + CloudFront (React, Vue, 정적 웹)
- **동적 서비스**: ECS Fargate (API 서버, 백엔드 애플리케이션)

### 모니터링 및 로깅
- **EventBridge**: 배포 상태 변화 이벤트 수집
- **WebSocket API**: 실시간 로그 스트리밍
- **CloudWatch**: 메트릭 및 로그 수집

## 🚀 배포 가이드

### 1. 사전 준비
```bash
# AWS CLI 설정
aws configure

# Terraform 설치 확인
terraform --version
```

### 2. Bootstrap (최초 1회만)
```bash
cd bootstrap
terraform init
terraform apply
cd ..
```

### 3. 인프라 배포
```bash
# 개발 환경
terraform init
terraform plan -var-file="env/dev.tfvars"
terraform apply -var-file="env/dev.tfvars"

# 프로덕션 환경
terraform plan -var-file="env/prod.tfvars"
terraform apply -var-file="env/prod.tfvars"
```

## 🛠️ 주요 AWS 리소스

| 서비스 | 용도 | 설명 |
|--------|------|------|
| **VPC** | 네트워크 | 10.0.0.0/16 CIDR, 퍼블릭/프라이빗 서브넷 |
| **ECS Fargate** | 동적 서비스 | AI가 추천한 스펙으로 컨테이너 실행 |
| **Lambda** | AI Agent | 코드 분석, 설정 추천, 배포 처리 |
| **S3 + CloudFront** | 정적 사이트 | 글로벌 CDN을 통한 정적 웹 호스팅 |
| **CodePipeline** | CI/CD | GitHub → Build → Deploy 자동화 |
| **EventBridge** | 실시간 이벤트 | 배포 상태 변화를 실시간으로 전달 |
| **Bedrock** | AI 모델 | 코드 분석 및 설정 자동 생성 |

## 🔧 핵심 기능

### AI 기반 자동화
- 프로젝트 구조 분석으로 정적/동적 자동 판별
- 런타임, 빌드 명령, 환경변수 자동 생성
- CPU/Memory 스펙 자동 추천

### 원클릭 배포
- GitHub 저장소 연결 후 클릭 한 번으로 배포 완료
- 정적 → S3+CloudFront, 동적 → ECR+ECS Fargate 자동 선택

### 실시간 모니터링
- EventBridge를 통한 배포 상태 실시간 업데이트
- AI Summary로 실패 원인 및 해결책 즉시 제공

## 📊 예상 비용 (MVP 기준)

- **Lambda**: ~1,000원/월
- **Bedrock**: ~20,000원/월 (소규모 호출)
- **ECS Fargate**: ~5,000원/월 (0.25 vCPU, 0.5GB)
- **S3 + CloudFront**: ~1,000원/월
- **기타 서비스**: ~3,000원/월

**총 예상 비용**: 약 30,000원/월 (프로토타입 기준)

## 🎯 사용자 경험

1. **GitHub 로그인** → 저장소 선택
2. **AI 분석** → 자동 설정 생성
3. **원클릭 배포** → 실시간 진행 상황 확인
4. **AI Summary** → 실패 시 즉시 해결책 제공
5. **상시 AI Agent** → 언제든 질문 및 조언 가능

hAIfu는 "배포의 고통"을 "창작의 기쁨"으로 바꾸는 새로운 세대의 배포 플랫폼입니다.