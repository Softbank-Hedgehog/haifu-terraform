"""
Agent Lambda Function
S3 스냅샷 기반 Repository 분석 → Cost 추정 (이중 구조)
"""
import json
import boto3
import os
from typing import Dict, Any, List, Optional


# =============================================================================
# AWS App Runner 스펙 상수 (haifu-server/app/schemas/service.py와 동일)
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


# =============================================================================
# S3 Service (Repository 정보 로드)
# =============================================================================

class S3SnapshotLoader:
    """S3에서 소스 스냅샷 로드"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
    
    def list_files(self, bucket: str, s3_prefix: str, max_files: int = 50) -> List[str]:
        """S3 스냅샷 파일 목록 조회"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=s3_prefix,
                MaxKeys=max_files
            )
            
            files = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                if not key.endswith('/'):  # 디렉토리 제외
                    files.append(key)
            
            return files
        except Exception as e:
            print(f"Error listing S3 files: {e}")
            return []
    
    def read_file(self, bucket: str, key: str, max_size: int = 50000) -> Optional[str]:
        """S3 파일 읽기"""
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            body = response['Body'].read(max_size)
            
            try:
                return body.decode('utf-8')
            except UnicodeDecodeError:
                return None  # 바이너리 파일
        except Exception as e:
            print(f"Error reading S3 file {key}: {e}")
            return None
    
    def load_snapshot(self, bucket: str, s3_prefix: str) -> Dict[str, str]:
        """스냅샷에서 주요 파일들 로드"""
        important_files = [
            'package.json', 'requirements.txt', 'pyproject.toml',
            'pom.xml', 'build.gradle', 'go.mod',
            'Dockerfile', 'docker-compose.yml', 'README.md'
        ]
        
        all_files = self.list_files(bucket, s3_prefix)
        file_contents = {}
        
        for file_key in all_files:
            file_name = file_key.split('/')[-1]
            if file_name in important_files:
                content = self.read_file(bucket, file_key)
                if content:
                    file_contents[file_name] = content
        
        print(f"Loaded {len(file_contents)} files from S3")
        return file_contents


# =============================================================================
# Repository Analyzer (Step 1)
# =============================================================================

class RepositoryAnalyzer:
    """Repository 분석 (간단한 패턴 매칭 기반)"""
    
    def analyze(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        """
        파일 내용으로부터 프레임워크, 언어, 런타임 감지
        
        Returns:
            {
                "framework": "fastapi",
                "language": "python",
                "runtime": "PYTHON_3",
                "has_dockerfile": true,
                "dependencies": [...]
            }
        """
        result = {
            "framework": "unknown",
            "language": "unknown",
            "runtime": None,
            "has_dockerfile": False,
            "has_docker_compose": False,
            "dependencies": []
        }
        
        # Dockerfile 확인
        if "Dockerfile" in file_contents:
            result["has_dockerfile"] = True
        
        if "docker-compose.yml" in file_contents or "docker-compose.yaml" in file_contents:
            result["has_docker_compose"] = True
        
        # JavaScript/TypeScript 감지
        if "package.json" in file_contents:
            result["language"] = "javascript"
            package_json = file_contents["package.json"].lower()
            
            if "react" in package_json:
                result["framework"] = "react"
                result["runtime"] = "NODEJS_18"
            elif "next" in package_json:
                result["framework"] = "nextjs"
                result["runtime"] = "NODEJS_20"
            elif "vue" in package_json:
                result["framework"] = "vue"
                result["runtime"] = "NODEJS_18"
            elif "express" in package_json:
                result["framework"] = "express"
                result["runtime"] = "NODEJS_18"
            else:
                result["framework"] = "nodejs"
                result["runtime"] = "NODEJS_18"
        
        # Python 감지
        elif "requirements.txt" in file_contents:
            result["language"] = "python"
            requirements = file_contents["requirements.txt"].lower()
            
            if "fastapi" in requirements:
                result["framework"] = "fastapi"
                result["runtime"] = "PYTHON_3"
            elif "django" in requirements:
                result["framework"] = "django"
                result["runtime"] = "PYTHON_3"
            elif "flask" in requirements:
                result["framework"] = "flask"
                result["runtime"] = "PYTHON_3"
            else:
                result["framework"] = "python"
                result["runtime"] = "PYTHON_3"
        
        elif "pyproject.toml" in file_contents:
            result["language"] = "python"
            result["framework"] = "python"
            result["runtime"] = "PYTHON_3"
        
        # Java 감지
        elif "pom.xml" in file_contents:
            result["language"] = "java"
            result["framework"] = "java"
            result["runtime"] = "JAVA_17"
        
        elif "build.gradle" in file_contents:
            result["language"] = "java"
            result["framework"] = "java"
            result["runtime"] = "JAVA_17"
        
        # Go 감지
        elif "go.mod" in file_contents:
            result["language"] = "go"
            result["framework"] = "go"
            result["runtime"] = "GO_1"
        
        print(f"Analysis result: {result['framework']} ({result['runtime']})")
        return result


# =============================================================================
# Bedrock Client
# =============================================================================

class BedrockCostEstimator:
    """Bedrock Claude를 사용한 비용 추정"""
    
    def __init__(self):
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        )
        self.model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
    
    def estimate_cost(
        self,
        repo_analysis: Dict[str, Any],
        cpu_constraint: str,
        memory_constraint: str
    ) -> Dict[str, Any]:
        """
        Bedrock Claude를 호출하여 비용 추정
        
        Args:
            repo_analysis: Repository 분석 결과
            cpu_constraint: 허용된 CPU (예: "1 vCPU")
            memory_constraint: 허용된 Memory (예: "2 GB")
        
        Returns:
            비용 추정 결과
        """
        system_prompt = self._build_system_prompt(cpu_constraint, memory_constraint)
        user_prompt = self._build_user_prompt(repo_analysis)
        
        try:
            # Bedrock Converse API 호출
            response = self.bedrock_runtime.converse(
                modelId=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": user_prompt}]
                    }
                ],
                system=[{"text": system_prompt}],
                inferenceConfig={
                    "maxTokens": 2000,
                    "temperature": 0.3,
                    "topP": 0.9
                }
            )
            
            # 응답 파싱
            output_text = response['output']['message']['content'][0]['text']
            
            # JSON 추출
            result = self._parse_json_response(output_text)
            
            # 스펙 강제 적용
            result = self._enforce_spec_constraints(result, cpu_constraint, memory_constraint)
            
            return result
        
        except Exception as e:
            print(f"Bedrock API error: {e}")
            return {
                "error": str(e),
                "fallback": True,
                "estimated_monthly_cost_usd": 50.0,
                "cpu": cpu_constraint,
                "memory": memory_constraint
            }
    
    def _build_system_prompt(self, cpu: str, memory: str) -> str:
        """시스템 프롬프트 생성 (스펙 제약 포함)"""
        return f"""You are an AWS App Runner cost estimation specialist.

**STRICT CONSTRAINTS - YOU MUST FOLLOW:**
- CPU: {cpu} (ONLY this value is allowed)
- Memory: {memory} (ONLY this value is allowed)
- Runtime: Must be one of {', '.join(RUNTIMES)}

**AWS App Runner Pricing (2024):**
- vCPU: $0.064 per vCPU per hour
- Memory: $0.007 per GB per hour
- Build: Included in pricing
- Data Transfer: $0.09/GB out (after 100GB free)

**Response Format (JSON ONLY):**
```json
{{
  "service": "app_runner",
  "runtime": "PYTHON_3 | NODEJS_18 | etc.",
  "cpu": "{cpu}",
  "memory": "{memory}",
  "estimated_monthly_cost_usd": 45.0,
  "breakdown": {{
    "compute": 30.0,
    "data_transfer": 5.0,
    "other": 10.0
  }},
  "cost_assumptions": {{
    "uptime": "24/7",
    "traffic": "medium",
    "requests_per_month": 1000000
  }},
  "cost_optimization_tips": [
    "Enable auto-scaling to reduce idle costs",
    "Use CloudFront CDN"
  ],
  "reasoning": "Explanation"
}}
```

YOU MUST use EXACTLY {cpu} and {memory}. DO NOT suggest alternatives."""
    
    def _build_user_prompt(self, repo_analysis: Dict[str, Any]) -> str:
        """사용자 프롬프트 생성"""
        return f"""## Repository Analysis:
- Framework: {repo_analysis['framework']}
- Language: {repo_analysis['language']}
- Runtime: {repo_analysis['runtime']}
- Has Dockerfile: {repo_analysis['has_dockerfile']}

## Task:
Estimate the monthly AWS App Runner cost for this application.
Use the EXACT CPU and Memory specified in the system prompt.
Provide realistic estimates based on typical production usage."""
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """LLM 응답에서 JSON 추출"""
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


# =============================================================================
# Lambda Handler
# =============================================================================

def handler(event, context):
    """
    Agent Lambda Handler (이중 구조)
    
    Step 1: S3에서 Repository 정보 로드 및 분석
    Step 2: Bedrock으로 비용 추정 (service.py 스펙 강제)
    
    Event 구조:
    {
        "s3_snapshot": {
            "bucket": "haifu-dev-source-bucket",
            "s3_prefix": "user/123/proj/svc/20251122-sourcefile"
        },
        "cpu": "1 vCPU",  # Optional (기본값: 1 vCPU)
        "memory": "2 GB"   # Optional (기본값: 2 GB)
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "repository_analysis": {...},
            "cost_estimation": {...}
        }
    }
    """
    print(f"Event: {json.dumps(event)}")
    
    try:
        # 입력 검증
        s3_snapshot = event.get('s3_snapshot')
        if not s3_snapshot or not s3_snapshot.get('bucket') or not s3_snapshot.get('s3_prefix'):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 's3_snapshot is required with bucket and s3_prefix'
                })
            }
        
        # CPU/Memory 제약 (기본값 또는 요청값)
        cpu = event.get('cpu', '1 vCPU')
        memory = event.get('memory', '2 GB')
        
        # CPU/Memory 검증
        if cpu not in CPU_OPTIONS:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Invalid CPU. Must be one of: {CPU_OPTIONS}'
                })
            }
        
        if memory not in MEMORY_OPTIONS:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Invalid memory. Must be one of: {MEMORY_OPTIONS}'
                })
            }
        
        # CPU-Memory 조합 검증
        allowed_memory = CPU_MEMORY_COMBINATIONS.get(cpu, [])
        if memory not in allowed_memory:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Invalid CPU-Memory combination. {cpu} supports: {allowed_memory}'
                })
            }
        
        # ===================================================================
        # Step 1: S3에서 Repository 정보 로드 및 분석
        # ===================================================================
        print(f"Step 1: Loading from S3 - {s3_snapshot['s3_prefix']}")
        
        s3_loader = S3SnapshotLoader()
        file_contents = s3_loader.load_snapshot(
            bucket=s3_snapshot['bucket'],
            s3_prefix=s3_snapshot['s3_prefix']
        )
        
        if not file_contents:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'No files found in S3 snapshot'
                })
            }
        
        # Repository 분석
        analyzer = RepositoryAnalyzer()
        repo_analysis = analyzer.analyze(file_contents)
        
        print(f"Repository analysis complete: {repo_analysis['framework']}")
        
        # ===================================================================
        # Step 2: Bedrock으로 비용 추정 (스펙 강제)
        # ===================================================================
        print(f"Step 2: Cost estimation with CPU={cpu}, Memory={memory}")
        
        estimator = BedrockCostEstimator()
        cost_estimation = estimator.estimate_cost(
            repo_analysis=repo_analysis,
            cpu_constraint=cpu,
            memory_constraint=memory
        )
        
        print(f"Cost estimation complete: ${cost_estimation.get('estimated_monthly_cost_usd', 0)}/month")
        
        # ===================================================================
        # 최종 응답
        # ===================================================================
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'repository_analysis': repo_analysis,
                'cost_estimation': cost_estimation,
                'constraints': {
                    'cpu': cpu,
                    'memory': memory,
                    'allowed_runtimes': RUNTIMES,
                    'allowed_cpu_options': CPU_OPTIONS,
                    'allowed_memory_options': MEMORY_OPTIONS
                }
            })
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
