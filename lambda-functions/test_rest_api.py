"""
REST API Gateway 테스트 스크립트
실제 배포된 API Gateway 엔드포인트를 테스트합니다.
"""
import requests
import json
import time

# REST API Gateway 엔드포인트
BASE_URL = "https://ax1iakl8t8.execute-api.ap-northeast-2.amazonaws.com/prod"

def print_header(title):
    print("\n" + "=" * 80)
    print(f"🧪 {title}")
    print("=" * 80)

def print_response(response):
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"Response (raw):\n{response.text}")

# =============================================================================
# Test 1: Main Query (기획안 검토)
# =============================================================================
def test_main_query():
    print_header("Test 1: Main Query - 기획안 검토")
    
    payload = {
        "message": "React와 FastAPI를 사용한 웹 애플리케이션을 AWS에 배포하려고 합니다. 추천하는 아키텍처를 알려주세요.",
        "context": {
            "frontend": "React",
            "backend": "FastAPI",
            "scale": "medium"
        }
    }
    
    print(f"\nRequest URL: {BASE_URL}/main")
    print(f"Payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/main",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            reply = data.get('reply', '')
            print(f"\n✅ Success! Reply length: {len(reply)} characters")
            print(f"First 200 chars: {reply[:200]}...")
        else:
            print(f"\n❌ Failed with status code: {response.status_code}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")

# =============================================================================
# Test 2: Chat (일반 대화)
# =============================================================================
def test_chat():
    print_header("Test 2: Chat - 일반 대화")
    
    payload = {
        "message": "AWS Lambda의 주요 장점과 단점을 설명해주세요."
    }
    
    print(f"\nRequest URL: {BASE_URL}/chat")
    print(f"Payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            reply = data.get('reply', '')
            print(f"\n✅ Success! Reply length: {len(reply)} characters")
        else:
            print(f"\n❌ Failed with status code: {response.status_code}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")

# =============================================================================
# Test 3: Deployment Check (배포 타입 판단)
# =============================================================================
def test_deployment_check():
    print_header("Test 3: Deployment Check - 배포 타입 판단")
    
    # Note: 실제 S3 스냅샷이 필요합니다
    payload = {
        "s3_snapshot": {
            "bucket": "haifu-dev-source-bucket",
            "s3_prefix": "user/123456/project-test/service-web/20251122T100000Z-sourcefile"
        }
    }
    
    print(f"\nRequest URL: {BASE_URL}/deployment")
    print(f"Payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
    print("\n⚠️ Note: This test requires a valid S3 snapshot")
    
    try:
        response = requests.post(
            f"{BASE_URL}/deployment",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            deployment_type = data.get('deployment_type', 'UNKNOWN')
            print(f"\n✅ Success! Deployment Type: {deployment_type}")
        elif response.status_code == 404:
            print(f"\n⚠️ S3 snapshot not found (expected for test)")
        else:
            print(f"\n❌ Failed with status code: {response.status_code}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")

# =============================================================================
# Test 4: Cost Estimation (비용 견적)
# =============================================================================
def test_cost_estimation():
    print_header("Test 4: Cost Estimation - 비용 견적")
    
    # Note: 실제 S3 스냅샷이 필요합니다
    payload = {
        "s3_snapshot": {
            "bucket": "haifu-dev-source-bucket",
            "s3_prefix": "user/123456/project-test/service-backend/20251122T100000Z-sourcefile"
        },
        "cpu": "1 vCPU",
        "memory": "2 GB"
    }
    
    print(f"\nRequest URL: {BASE_URL}/cost")
    print(f"Payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
    print("\n⚠️ Note: This test requires a valid S3 snapshot")
    
    try:
        response = requests.post(
            f"{BASE_URL}/cost",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            cost = data.get('cost_estimation', {}).get('estimated_monthly_cost_usd', 0)
            print(f"\n✅ Success! Estimated Monthly Cost: ${cost}")
        elif response.status_code == 404:
            print(f"\n⚠️ S3 snapshot not found (expected for test)")
        else:
            print(f"\n❌ Failed with status code: {response.status_code}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")

# =============================================================================
# Test 5: Invalid Action
# =============================================================================
def test_invalid_action():
    print_header("Test 5: Invalid Action - 에러 처리")
    
    payload = {
        "message": "This should fail"
    }
    
    # 잘못된 경로 테스트
    invalid_url = f"{BASE_URL}/invalid-endpoint"
    
    print(f"\nRequest URL: {invalid_url}")
    print(f"Payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            invalid_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        print_response(response)
        
        if response.status_code == 400:
            print(f"\n✅ Success! Correctly rejected invalid action")
        else:
            print(f"\n⚠️ Unexpected status code: {response.status_code}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")

# =============================================================================
# Main Test Runner
# =============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("REST API Gateway 테스트")
    print("=" * 80)
    print(f"\nBase URL: {BASE_URL}")
    print("\n⚠️ 주의:")
    print("  - Test 3, 4는 실제 S3 스냅샷이 필요합니다")
    print("  - 없으면 404 에러가 발생합니다 (정상)")
    print("  - Test 1, 2는 독립적으로 실행 가능합니다")
    
    # 테스트 선택
    print("\n실행할 테스트를 선택하세요:")
    print("  1 - Main Query (기획안 검토)")
    print("  2 - Chat (일반 대화)")
    print("  3 - Deployment Check (S3 필요)")
    print("  4 - Cost Estimation (S3 필요)")
    print("  5 - Invalid Action")
    print("  a - All Tests")
    
    choice = input("\n선택 (1-5, a): ").strip().lower()
    
    tests = {
        '1': test_main_query,
        '2': test_chat,
        '3': test_deployment_check,
        '4': test_cost_estimation,
        '5': test_invalid_action
    }
    
    if choice == 'a':
        for test_func in tests.values():
            test_func()
            time.sleep(2)  # Rate limiting 방지
    elif choice in tests:
        tests[choice]()
    else:
        print("❌ Invalid choice")
    
    print("\n" + "=" * 80)
    print("✅ 테스트 완료!")
    print("=" * 80 + "\n")

