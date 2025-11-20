import json
import boto3
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ecs_client = boto3.client('ecs')
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Deployment Lambda function
    Handles user service deployment to ECS Fargate
    """
    try:
        # Parse deployment request
        body = json.loads(event.get('body', '{}'))
        
        deployment_id = body.get('deployment_id')
        service_name = body.get('service_name')
        container_image = body.get('container_image')
        container_port = body.get('container_port', 80)
        
        if not all([deployment_id, service_name, container_image]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Update deployment status
        update_deployment_status(deployment_id, 'DEPLOYING', 'Starting deployment')
        
        # Deploy to ECS
        result = deploy_to_ecs(
            service_name=service_name,
            container_image=container_image,
            container_port=container_port
        )
        
        if result['success']:
            update_deployment_status(deployment_id, 'SUCCESS', 'Deployment completed')
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'deployment_id': deployment_id,
                    'status': 'SUCCESS',
                    'service_arn': result['service_arn']
                })
            }
        else:
            update_deployment_status(deployment_id, 'FAILED', result['error'])
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'deployment_id': deployment_id,
                    'status': 'FAILED',
                    'error': result['error']
                })
            }
            
    except Exception as e:
        logger.error(f"Deployment error: {str(e)}")
        if 'deployment_id' in locals():
            update_deployment_status(deployment_id, 'FAILED', str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def deploy_to_ecs(service_name, container_image, container_port):
    """
    Deploy service to ECS Fargate
    """
    try:
        cluster_name = 'haifu-dev-user-services'  # From Terraform output
        
        # Create or update task definition
        task_def_response = ecs_client.register_task_definition(
            family=f'haifu-dev-{service_name}',
            networkMode='awsvpc',
            requiresCompatibilities=['FARGATE'],
            cpu='256',
            memory='512',
            executionRoleArn='arn:aws:iam::ACCOUNT:role/haifu-dev-ecs-execution-role',
            containerDefinitions=[
                {
                    'name': service_name,
                    'image': container_image,
                    'cpu': 256,
                    'memory': 512,
                    'essential': True,
                    'portMappings': [
                        {
                            'containerPort': container_port,
                            'protocol': 'tcp'
                        }
                    ],
                    'logConfiguration': {
                        'logDriver': 'awslogs',
                        'options': {
                            'awslogs-group': f'/ecs/haifu-dev-{service_name}',
                            'awslogs-region': 'ap-northeast-2',
                            'awslogs-stream-prefix': 'ecs'
                        }
                    }
                }
            ]
        )
        
        # Create or update service
        service_response = ecs_client.create_service(
            cluster=cluster_name,
            serviceName=f'haifu-dev-{service_name}',
            taskDefinition=task_def_response['taskDefinition']['taskDefinitionArn'],
            desiredCount=1,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': ['subnet-xxx', 'subnet-yyy'],  # From Terraform
                    'securityGroups': ['sg-xxx'],  # From Terraform
                    'assignPublicIp': 'DISABLED'
                }
            }
        )
        
        return {
            'success': True,
            'service_arn': service_response['service']['serviceArn']
        }
        
    except Exception as e:
        logger.error(f"ECS deployment error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def update_deployment_status(deployment_id, status, message):
    """
    Update deployment status in DynamoDB
    """
    try:
        table = dynamodb.Table('haifu-dev-deployment-status')
        table.put_item(
            Item={
                'deployment_id': deployment_id,
                'status': status,
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"DynamoDB update error: {str(e)}")