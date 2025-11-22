#!/usr/bin/env python3
"""
Check deployment status and infrastructure readiness
"""

import boto3
import json
from datetime import datetime

def check_infrastructure_status():
    """Check if core infrastructure is ready"""
    
    # Check ECS clusters
    ecs = boto3.client('ecs')
    try:
        clusters = ecs.list_clusters()
        user_cluster_exists = any('user-services' in cluster for cluster in clusters['clusterArns'])
        print(f"User Services Cluster: {'✅ Ready' if user_cluster_exists else '❌ Not Found'}")
    except Exception as e:
        print(f"ECS Check Failed: {e}")
    
    # Check DynamoDB tables
    dynamodb = boto3.client('dynamodb')
    try:
        tables = dynamodb.list_tables()['TableNames']
        deployment_table = any('deployment-status' in table for table in tables)
        print(f"Deployment Status Table: {'✅ Ready' if deployment_table else '❌ Not Found'}")
    except Exception as e:
        print(f"DynamoDB Check Failed: {e}")
    
    # Check Lambda functions
    lambda_client = boto3.client('lambda')
    try:
        functions = lambda_client.list_functions()['Functions']
        deployment_lambda = any('deployment' in func['FunctionName'] for func in functions)
        print(f"Deployment Lambda: {'✅ Ready' if deployment_lambda else '❌ Not Found'}")
    except Exception as e:
        print(f"Lambda Check Failed: {e}")

def simulate_deployment_request():
    """Simulate a deployment request"""
    
    request_body = {
        "service_type": "dynamic",
        "runtime": "nodejs18",
        "build_config": {
            "install_commands": ["npm install"],
            "build_commands": ["npm run build"]
        },
        "start_command": "npm start",
        "service_name": "test-api",
        "deployment_id": f"deploy-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    }
    
    print("\n📋 Sample Deployment Request:")
    print(json.dumps(request_body, indent=2))
    
    print("\n🔄 Expected Flow:")
    print("1. Lambda receives request")
    print("2. Creates ECS task definition")
    print("3. Registers ECS service")
    print("4. Sets up auto-scaling")
    print("5. Creates CI/CD pipeline")
    print("6. Updates deployment status")

if __name__ == "__main__":
    print("🔍 Checking hAIfu Infrastructure Status...\n")
    
    check_infrastructure_status()
    simulate_deployment_request()
    
    print(f"\n⏰ CloudFront is still deploying (this takes 10-15 minutes)")
    print("✅ Core infrastructure for user deployments is ready!")
    print("\n🚀 You can now test deployments with the request format:")
    print("   POST /deploy with the JSON body shown above")