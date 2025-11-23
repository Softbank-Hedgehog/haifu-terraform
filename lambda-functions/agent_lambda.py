"""
Agent Lambda Function
기능:
1. General Chat (일반 대화)
2. Deployment Analysis (정적/동적 배포 판단)
3. Cost Estimation (기존: 비용 견적)
"""
import json
import boto3
import os
from typing import Dict, Any, List, Optional

# =============================================================================
# AWS App Runner 스펙 상수 및 가격 정보
# =============================================================================
RUNTIMES = [
    "PYTHON_3", "NODEJS_16", "NODEJS_18", "NODEJS_20",
    "JAVA_11", "JAVA_17", "DOTNET_6", "GO_1", "PHP_81", "RUBY_31"
]
CPU_OPTIONS = ["1 vCPU", "2 vCPU", "4 vCPU"]
MEMORY_OPTIONS = ["2 GB", "3 GB", "4 GB", "6 GB", "8 GB", "10 GB", "12 GB"]
CPU_MEMORY_COMBINATIONS = {
    "1 vCPU": ["2 GB", "3 GB", "4 GB"],
    "2 vCPU": ["4 GB", "6 GB", "8 GB"],
    "4 vCPU": ["8 GB", "10 GB", "12 GB"]
}

# AWS App Runner 가격 (Seoul Region, ap-northeast-2, 2024년 기준)
PRICE_PER_VCPU_HOUR = 0.064   # USD
PRICE_PER_GB_HOUR = 0.007     # USD
HOURS_PER_MONTH = 730         # 월 평균 시간

def get_app_runner_price_table():
    """
    제시된 CPU_MEMORY_COMBINATIONS에 대한 월별 예상 비용 테이블 생성
    기준: AWS App Runner (Seoul Region, ap-northeast-2)
    가정: 24시간/30일(730시간) 내내 활성(Active) 상태로 구동 시
    """
    price_table = {}
    
    for cpu_label, memory_list in CPU_MEMORY_COMBINATIONS.items():
        # "1 vCPU" -> 1.0 (숫자 추출)
        cpu_val = float(cpu_label.split()[0])
        
        price_table[cpu_label] = {}
        
        for mem_label in memory_list:
            # "2 GB" -> 2.0 (숫자 추출)
            mem_val = float(mem_label.split()[0])
            
            # 시간당 비용 계산
            hourly_cost = (cpu_val * PRICE_PER_VCPU_HOUR) + (mem_val * PRICE_PER_GB_HOUR)
            
            # 월간 비용 계산 (24/7 가동 기준)
            monthly_cost = hourly_cost * HOURS_PER_MONTH
            
            # 결과 저장 (소수점 둘째자리까지)
            price_table[cpu_label][mem_label] = {
                "hourly_usd": round(hourly_cost, 4),
                "monthly_usd": round(monthly_cost, 2)
            }
            
    return price_table

def calculate_app_runner_cost(cpu: str, memory: str, uptime_percentage: float = 100.0, traffic_multiplier: float = 1.0) -> Dict[str, Any]:
    """
    App Runner 비용 직접 계산
    
    Args:
        cpu: CPU 스펙 (예: "1 vCPU")
        memory: Memory 스펙 (예: "2 GB")
        uptime_percentage: 가동률 (0-100%, 기본 100%)
        traffic_multiplier: 트래픽 배율 (기본 1.0 = medium traffic)
    
    Returns:
        상세 비용 정보
    """
    # CPU, Memory 숫자 추출
    cpu_val = float(cpu.split()[0])
    mem_val = float(memory.split()[0])
    
    # 시간당 컴퓨트 비용
    hourly_compute_cost = (cpu_val * PRICE_PER_VCPU_HOUR) + (mem_val * PRICE_PER_GB_HOUR)
    
    # 월간 컴퓨트 비용 (가동률 반영)
    monthly_compute_cost = hourly_compute_cost * HOURS_PER_MONTH * (uptime_percentage / 100.0)
    
    # 데이터 전송 비용 추정 (트래픽에 따라)
    # 가정: medium traffic = 월 100GB 아웃바운드 (첫 100GB 무료, 이후 $0.09/GB)
    outbound_gb = 100 * traffic_multiplier
    data_transfer_cost = max(0, (outbound_gb - 100) * 0.09)
    
    # 빌드 비용 (월 1-2회 배포 가정, 분당 $0.005)
    # 평균 10분 빌드 * 2회 = 20분
    build_cost = 20 * 0.005
    
    # 총 비용
    total_monthly_cost = monthly_compute_cost + data_transfer_cost + build_cost
    
    return {
        "service": "app_runner",
        "cpu": cpu,
        "memory": memory,
        "estimated_monthly_cost_usd": round(total_monthly_cost, 2),
        "breakdown": {
            "compute": round(monthly_compute_cost, 2),
            "data_transfer": round(data_transfer_cost, 2),
            "build": round(build_cost, 2)
        },
        "pricing_details": {
            "vcpu_price_per_hour": PRICE_PER_VCPU_HOUR,
            "memory_price_per_gb_hour": PRICE_PER_GB_HOUR,
            "hours_per_month": HOURS_PER_MONTH,
            "uptime_percentage": uptime_percentage,
            "traffic_multiplier": traffic_multiplier
        }
    }

# =============================================================================
# 1. S3 Service (기존 유지)
# =============================================================================
class S3SnapshotLoader:
    """S3에서 소스 스냅샷 로드"""
    def __init__(self):
        self.s3_client = boto3.client('s3')
    
    def list_files(self, bucket: str, s3_prefix: str, max_files: int = 50) -> List[str]:
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=s3_prefix, MaxKeys=max_files)
            files = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                if not key.endswith('/'):
                    files.append(key)
            return files
        except Exception as e:
            print(f"Error listing S3 files: {e}")
            return []
    
    def read_file(self, bucket: str, key: str, max_size: int = 50000) -> Optional[str]:
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            body = response['Body'].read(max_size)
            try:
                return body.decode('utf-8')
            except UnicodeDecodeError:
                return None
        except Exception as e:
            print(f"Error reading S3 file {key}: {e}")
            return None
    
    def load_snapshot(self, bucket: str, s3_prefix: str) -> Dict[str, str]:
        important_files = [
            'package.json', 'requirements.txt', 'pyproject.toml',
            'pom.xml', 'build.gradle', 'go.mod',
            'Dockerfile', 'docker-compose.yml', 'README.md',
            'index.html', 'vercel.json', 'next.config.js' # 정적 분석용 추가
        ]
        all_files = self.list_files(bucket, s3_prefix)
        file_contents = {}
        for file_key in all_files:
            file_name = file_key.split('/')[-1]
            if file_name in important_files:
                content = self.read_file(bucket, file_key)
                if content:
                    file_contents[file_name] = content
        return file_contents

# =============================================================================
# 2. Repository Analyzer (기존 유지)
# =============================================================================
class RepositoryAnalyzer:
    """Repository 분석"""
    def analyze(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        result = {
            "framework": "unknown",
            "language": "unknown",
            "runtime": None,
            "has_dockerfile": "Dockerfile" in file_contents,
            "dependencies": []
        }
        
        # JavaScript/TypeScript
        if "package.json" in file_contents:
            result["language"] = "javascript"
            pkg = file_contents["package.json"].lower()
            if "react" in pkg: result.update({"framework": "react", "runtime": "NODEJS_18"})
            elif "next" in pkg: result.update({"framework": "nextjs", "runtime": "NODEJS_20"})
            elif "vue" in pkg: result.update({"framework": "vue", "runtime": "NODEJS_18"})
            elif "express" in pkg: result.update({"framework": "express", "runtime": "NODEJS_18"})
            else: result.update({"framework": "nodejs", "runtime": "NODEJS_18"})
        
        # Python
        elif "requirements.txt" in file_contents:
            result["language"] = "python"
            req = file_contents["requirements.txt"].lower()
            if "fastapi" in req: result.update({"framework": "fastapi", "runtime": "PYTHON_3"})
            elif "django" in req: result.update({"framework": "django", "runtime": "PYTHON_3"})
            elif "flask" in req: result.update({"framework": "flask", "runtime": "PYTHON_3"})
            else: result.update({"framework": "python", "runtime": "PYTHON_3"})
            
        return result

# =============================================================================
# 3. AI Agents (New & Existing)
# =============================================================================

class BedrockAgent:
    """통합 Bedrock 클라이언트 (Chat, Analysis, Cost)"""
    def __init__(self):
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=os.environ.get('AWS_DEFAULT_REGION', 'ap-northeast-2')
        )
        self.model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'

    def _invoke_model(self, system_prompt: str, user_prompt: str) -> str:
        """Bedrock 호출 공통 메서드"""
        try:
            response = self.bedrock_runtime.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": user_prompt}]}],
                system=[{"text": system_prompt}],
                inferenceConfig={"maxTokens": 2000, "temperature": 0.5}
            )
            return response['output']['message']['content'][0]['text']
        except Exception as e:
            print(f"Bedrock Error: {e}")
            return "{}"

    # --- 기능 0: Main LLM (기획안 검토 및 일반 질의) ---
    def main_query(self, message: str, context: Optional[Dict] = None) -> str:
        """
        일반적인 LLM 기능 - 기획안 검토, 사용자 질의 등
        
        Args:
            message: 사용자 질문
            context: 추가 컨텍스트 (선택)
        
        Returns:
            LLM 응답
        """
        system = """You are an expert technical consultant and product advisor specializing in:
- Software architecture and system design
- Cloud infrastructure planning (AWS, Azure, GCP)
- Technical proposal and specification review
- DevOps and deployment strategies
- Cost optimization and scalability analysis

Provide detailed, professional, and actionable advice. When reviewing proposals:
1. Analyze technical feasibility
2. Identify potential risks and challenges
3. Suggest improvements and alternatives
4. Consider scalability, cost, and maintainability"""
        
        # 컨텍스트가 있으면 질문에 추가
        if context:
            context_str = "\n\n**Context:**\n" + "\n".join([f"- {k}: {v}" for k, v in context.items()])
            full_message = message + context_str
        else:
            full_message = message
        
        return self._invoke_model(system, full_message)

    # --- 기능 1: 일반 대화 ---
    def chat(self, message: str) -> str:
        system = "You are a helpful and technical AI assistant for developers."
        return self._invoke_model(system, message)

    # --- 기능 2: 배포 유형 판단 (Static vs Dynamic) ---
    def analyze_deployment_type(self, repo_analysis: Dict, file_list: Dict) -> Dict:
        system = """You are a DevOps expert. Analyze the project structure to determine the deployment type.
        
        **Rules:**
        1. STATIC: Pure HTML/CSS, or SPA (React, Vue) without backend logic (SSR).
        2. DYNAMIC: Python, Java, Go, Node.js (Express, NestJS), or Docker based apps.
        
        **Response Format (JSON Only):**
        {
            "deployment_type": "STATIC" | "DYNAMIC",
            "reason": "Explain why...",
            "recommended_service": "S3+CloudFront" | "App Runner" | "EC2"
        }
        """
        user = f"""Project Info:
        - Framework: {repo_analysis.get('framework')}
        - Language: {repo_analysis.get('language')}
        - Files present: {list(file_list.keys())}
        
        Determine the deployment type."""
        
        response_text = self._invoke_model(system, user)
        return self._parse_json(response_text)

    # --- 기능 3: 비용 추정 (LLM은 사용 패턴 예측, 실제 계산은 가격 테이블 사용) ---
    def estimate_cost(self, repo_analysis: Dict, cpu: str, memory: str) -> Dict:
        """
        비용 추정: LLM이 사용 패턴을 예측하고, 정확한 가격 테이블로 계산
        
        Args:
            repo_analysis: Repository 분석 결과
            cpu: 허용된 CPU (예: "1 vCPU")
            memory: 허용된 Memory (예: "2 GB")
        
        Returns:
            비용 추정 결과
        """
        system_prompt = self._build_usage_estimation_prompt()
        user_prompt = self._build_usage_user_prompt(repo_analysis, cpu, memory)
        
        try:
            # 1. LLM에게 사용 패턴만 예측 요청
            response_text = self._invoke_model(system_prompt, user_prompt)
            usage_prediction = self._parse_cost_json_response(response_text)
            
            # 2. 예측된 사용 패턴 추출 (기본값 설정)
            uptime_percentage = usage_prediction.get('uptime_percentage', 100.0)
            traffic_multiplier = usage_prediction.get('traffic_multiplier', 1.0)
            
            # 3. 정확한 가격 테이블로 비용 직접 계산
            cost_result = calculate_app_runner_cost(cpu, memory, uptime_percentage, traffic_multiplier)
            
            # 4. LLM의 추가 정보 병합
            cost_result['runtime'] = repo_analysis.get('runtime', 'PYTHON_3')
            cost_result['framework'] = repo_analysis.get('framework', 'unknown')
            cost_result['usage_assumptions'] = {
                'uptime_percentage': uptime_percentage,
                'traffic_level': usage_prediction.get('traffic_level', 'medium'),
                'requests_per_month': usage_prediction.get('requests_per_month', 1000000)
            }
            cost_result['cost_optimization_tips'] = usage_prediction.get('cost_optimization_tips', [
                "Enable auto-scaling to reduce idle costs",
                "Use CloudFront CDN to reduce data transfer costs"
            ])
            cost_result['reasoning'] = usage_prediction.get('reasoning', 'Standard production workload estimation')
            
            return cost_result
        
        except Exception as e:
            print(f"Cost estimation error: {e}")
            # Fallback: 기본값으로 계산
            fallback_cost = calculate_app_runner_cost(cpu, memory, 100.0, 1.0)
            fallback_cost['error'] = str(e)
            fallback_cost['fallback'] = True
            return fallback_cost
    
    def _build_usage_estimation_prompt(self) -> str:
        """사용 패턴 예측용 시스템 프롬프트"""
        return """You are an AWS workload analysis expert. Your task is to predict application usage patterns, NOT to calculate costs.

**Your Job:**
Analyze the application characteristics and predict:
1. Expected uptime percentage (0-100%)
2. Traffic level and multiplier
3. Request volume
4. Cost optimization recommendations

**Response Format (JSON ONLY):**
```json
{
  "uptime_percentage": 100.0,
  "traffic_level": "low" | "medium" | "high",
  "traffic_multiplier": 1.0,
  "requests_per_month": 1000000,
  "cost_optimization_tips": [
    "Specific tip 1",
    "Specific tip 2"
  ],
  "reasoning": "Brief explanation of your predictions"
}
```

**Guidelines:**
- uptime_percentage: 100 = 24/7, 50 = 12 hours/day, etc.
- traffic_multiplier: 0.5 = low, 1.0 = medium, 2.0 = high
- Be realistic based on the framework and use case"""
    
    def _build_usage_user_prompt(self, repo_analysis: Dict[str, Any], cpu: str, memory: str) -> str:
        """사용 패턴 예측용 사용자 프롬프트"""
        return f"""## Application Info:
- Framework: {repo_analysis['framework']}
- Language: {repo_analysis['language']}
- Runtime: {repo_analysis['runtime']}
- Has Dockerfile: {repo_analysis['has_dockerfile']}
- CPU: {cpu}
- Memory: {memory}

## Task:
Predict the typical usage pattern for this application in production.
Consider the framework type and typical deployment scenarios."""
    
    def _parse_cost_json_response(self, response: str) -> Dict[str, Any]:
        """비용 추정 LLM 응답에서 JSON 추출"""
        try:
            # JSON 코드 블록 추출
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()
            
            return json.loads(json_str)
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 기본값 반환
            print(f"Failed to parse JSON from response")
            return {"error": "JSON parse error", "raw_response": response[:500]}
    
    def _enforce_spec_constraints(
        self,
        result: Dict[str, Any],
        cpu: str,
        memory: str
    ) -> Dict[str, Any]:
        """스펙 제약 강제 적용"""
        # CPU/Memory 강제 적용
        result["cpu"] = cpu
        result["memory"] = memory
        
        # Runtime 검증
        runtime = result.get("runtime")
        if runtime not in RUNTIMES:
            # 기본값 설정
            if "python" in result.get("service", "").lower():
                result["runtime"] = "PYTHON_3"
            elif "node" in result.get("service", "").lower():
                result["runtime"] = "NODEJS_18"
            else:
                result["runtime"] = RUNTIMES[0]
        
        return result

    def _parse_json(self, text: str) -> Dict:
        """일반 JSON 파싱 (chat, deployment_check용)"""
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            return json.loads(text[start:end])
        except:
            return {"error": "JSON parsing failed", "raw": text}

# =============================================================================
# 4. Action Handlers (기능별 처리 함수)
# =============================================================================

def handle_main(event: Dict) -> Dict:
    """기능 0: Main LLM 핸들러 (기획안 검토 및 일반 질의)"""
    message = event.get('message')
    if not message:
        return {'statusCode': 400, 'body': json.dumps({'error': 'message is required'})}
    
    # 선택적 컨텍스트 정보
    context = event.get('context')
    
    agent = BedrockAgent()
    reply = agent.main_query(message, context)
    
    return {
        'statusCode': 200,
        'body': json.dumps({'reply': reply})
    }

def handle_chat(event: Dict) -> Dict:
    """기능 1: 일반 챗봇 핸들러"""
    message = event.get('message')
    if not message:
        return {'statusCode': 400, 'body': json.dumps({'error': 'message is required'})}
    
    agent = BedrockAgent()
    reply = agent.chat(message)
    
    return {
        'statusCode': 200,
        'body': json.dumps({'reply': reply})
    }

def handle_deployment_check(event: Dict) -> Dict:
    """기능 2: 정적/동적 배포 판단 핸들러 - STATIC 또는 DYNAMIC 반환"""
    s3_snapshot = event.get('s3_snapshot')
    if not s3_snapshot:
        return {'statusCode': 400, 'body': json.dumps({'error': 's3_snapshot required'})}

    # 1. 파일 로드
    loader = S3SnapshotLoader()
    files = loader.load_snapshot(s3_snapshot['bucket'], s3_snapshot['s3_prefix'])
    
    if not files:
        return {'statusCode': 404, 'body': json.dumps({'error': 'No files found'})}

    # 2. 기본 분석
    analyzer = RepositoryAnalyzer()
    analysis_result = analyzer.analyze(files)

    # 3. AI 심층 분석 (Static vs Dynamic)
    agent = BedrockAgent()
    deployment_info = agent.analyze_deployment_type(analysis_result, files)
    
    # 4. deployment_type 추출 (STATIC 또는 DYNAMIC)
    deployment_type = deployment_info.get('deployment_type', 'DYNAMIC')
    
    # 유효성 검증
    if deployment_type not in ['STATIC', 'DYNAMIC']:
        deployment_type = 'DYNAMIC'  # 기본값

    return {
        'statusCode': 200,
        'body': json.dumps({
            'deployment_type': deployment_type
        })
    }

def handle_cost_estimation(event: Dict) -> Dict:
    """기능 3: 비용 견적 핸들러 (기존 로직)"""
    s3_snapshot = event.get('s3_snapshot')
    if not s3_snapshot:
        return {'statusCode': 400, 'body': json.dumps({'error': 's3_snapshot required'})}

    cpu = event.get('cpu', '1 vCPU')
    memory = event.get('memory', '2 GB')

    # 1. 파일 로드
    loader = S3SnapshotLoader()
    files = loader.load_snapshot(s3_snapshot['bucket'], s3_snapshot['s3_prefix'])
    
    # 2. 분석
    analyzer = RepositoryAnalyzer()
    analysis_result = analyzer.analyze(files)

    # 3. 비용 견적
    agent = BedrockAgent()
    cost_info = agent.estimate_cost(analysis_result, cpu, memory)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'repository_analysis': analysis_result,
            'cost_estimation': cost_info
        })
    }

# =============================================================================
# 5. Main Dispatcher (메인 라우터)
# =============================================================================

def handler(event, context):
    """
    Lambda Handler - API Gateway와 직접 Invoke 모두 지원
    
    API Gateway 요청 시 event 구조:
    {
        "body": "{\"action\": \"main\", \"message\": \"...\"}",
        "headers": {...},
        "requestContext": {...}
    }
    
    직접 Invoke 시 event 구조:
    {
        "action": "main",
        "message": "..."
    }
    """
    print(f"Received Event: {json.dumps(event)}")
    
    try:
        # API Gateway 요청 vs 직접 Lambda Invoke 구분
        if 'body' in event and 'requestContext' in event:
            # API Gateway를 통한 요청
            print("Processing API Gateway request")
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            is_api_gateway = True
            
            # API Gateway 경로에서 action 추출 (우선순위)
            raw_path = event.get('rawPath', event.get('requestContext', {}).get('http', {}).get('path', ''))
            print(f"Request path: {raw_path}")
            
            # 경로에서 action 추출 (/main -> main, /chat -> chat)
            if raw_path and raw_path != '/':
                path_action = raw_path.strip('/').split('/')[0]  # /main, /api/main 등 처리
                # 유효한 액션인지 확인
                if path_action in ['main', 'chat', 'deployment', 'cost']:
                    action = path_action
                    print(f"Action from path: {action}")
                else:
                    # body에서 action 가져오기
                    action = body.get('action', 'cost')
            else:
                # body에서 action 가져오기
                action = body.get('action', 'cost')
        else:
            # 직접 Lambda invoke
            print("Processing direct Lambda invoke")
            body = event
            is_api_gateway = False
            action = body.get('action', 'cost')
        
        # 액션별 핸들러 호출
        if action == 'main': # 메인 화면 상 기획안 검토 및 일반 질의용 핸들러
            result = handle_main(body)
        
        elif action == 'chat': # 일반 챗봇 핸들러
            result = handle_chat(body)
        
        elif action == 'deployment_check': # 정적/동적 배포 판단 핸들러
            result = handle_deployment_check(body)
        
        elif action == 'cost': # 비용 견적 핸들러
            result = handle_cost_estimation(body)
            
        else:
            result = {
                'statusCode': 400,
                'body': json.dumps({'error': f"Unknown action: {action}. Use 'main', 'chat', 'deployment_check', or 'cost'"})
            }
        
        # API Gateway 형식으로 응답 변환
        if is_api_gateway:
            return {
                'statusCode': result['statusCode'],
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',  # CORS
                    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
                },
                'body': result['body']
            }
        else:
            # 직접 invoke는 원래 형식 그대로
            return result
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        error_response = {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e)
            })
        }
        
        # API Gateway 요청인 경우 헤더 추가
        if 'body' in event and 'requestContext' in event:
            error_response['headers'] = {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        
        return error_response