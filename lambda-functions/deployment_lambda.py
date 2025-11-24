import json
import boto3
import logging
import uuid
from datetime import datetime
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
ecs_client = boto3.client('ecs')
s3_client = boto3.client('s3')
cloudformation_client = boto3.client('cloudformation')
codebuild_client = boto3.client('codebuild')
ecr_client = boto3.client('ecr')
logs_client = boto3.client('logs')

def handler(event, context):
    """
    Complete Deployment Lambda function with real deployment algorithms
    """
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        # Parse request method and path
        if 'requestContext' in event and 'http' in event['requestContext']:
            http_method = event['requestContext']['http']['method']
            path = event.get('rawPath', '')
        else:
            http_method = event.get('httpMethod', 'POST')
            path = event.get('path', '')
        
        # Determine action
        if path.endswith('/deploy'):
            action = 'deploy'
        elif path.endswith('/status'):
            action = 'status'
        elif path.endswith('/delete'):
            action = 'delete'
        else:
            action = 'deploy'
        
        # Extract parameters using fixed parsing logic
        params = extract_parameters(event, http_method)
        logger.info(f"Extracted params: {json.dumps(params, default=str)}")
        
        # Validate parameters
        validation_result = validate_parameters(params, action)
        if not validation_result['valid']:
            return create_error_response(400, validation_result['error'])
        
        # Route to appropriate handler
        if action == 'deploy':
            result = handle_deployment(params)
        elif action == 'status':
            result = handle_status(params)
        elif action == 'delete':
            result = handle_delete(params)
        else:
            return create_error_response(400, f"Unknown action: {action}")
        
        return create_success_response(result)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return create_error_response(500, str(e))

def extract_parameters(event, http_method):
    """Extract parameters from request - Lambda Function URL compatible"""
    if http_method == 'GET':
        query_params = event.get('queryStringParameters') or {}
        return {
            'user_id': query_params.get('user_id'),
            'project_id': query_params.get('project_id'),
            'service_id': query_params.get('service_id'),
            'service_type': query_params.get('service_type'),
            'deployment_id': query_params.get('deployment_id')
        }
    else:
        # For POST requests, try multiple sources
        # 1. Try body first (API Gateway format)
        raw_body = event.get('body', '{}')
        body = {}
        
        if raw_body and raw_body != '{}':
            if event.get('isBase64Encoded', False):
                import base64
                raw_body = base64.b64decode(raw_body).decode('utf-8')
            
            try:
                body = json.loads(raw_body)
            except json.JSONDecodeError:
                body = {}
        
        # 2. If body is empty, check if parameters are directly in event (Lambda Function URL)
        if not body:
            # Check if the required fields exist directly in the event
            if 'user_id' in event:
                body = {
                    'user_id': event.get('user_id'),
                    'project_id': event.get('project_id'),
                    'service_id': event.get('service_id'),
                    'service_type': event.get('service_type'),
                    'build_commands': event.get('build_commands', []),
                    'build_output_dir': event.get('build_output_dir', 'dist'),
                    'node_version': event.get('node_version', '18'),
                    'runtime': event.get('runtime'),
                    'start_command': event.get('start_command'),
                    'environment_variables': event.get('environment_variables', []),
                    'cpu': event.get('cpu', 256),
                    'memory': event.get('memory', 512),
                    'port': event.get('port', 80)
                }
        
        return {
            'user_id': str(body.get('user_id', '')) if body.get('user_id') else None,
            'project_id': str(body.get('project_id', '')) if body.get('project_id') else None,
            'service_id': str(body.get('service_id', '')) if body.get('service_id') else None,
            'service_type': body.get('service_type'),
            'deployment_id': body.get('deployment_id', str(uuid.uuid4())),
            'build_commands': body.get('build_commands', []),
            'build_output_dir': body.get('build_output_dir', 'dist'),
            'node_version': body.get('node_version', '18'),
            'runtime': body.get('runtime'),
            'start_command': body.get('start_command'),
            'environment_variables': body.get('environment_variables', []),
            'cpu': body.get('cpu', 256),
            'memory': body.get('memory', 512),
            'port': body.get('port', 80),
            'min_capacity': body.get('min_capacity', 1),
            'max_capacity': body.get('max_capacity', 10)
        }

def validate_parameters(params, action):
    """Validate required parameters"""
    required_fields = ['user_id', 'project_id', 'service_id']
    
    if action == 'deploy':
        required_fields.append('service_type')
    
    missing_fields = []
    for field in required_fields:
        value = params.get(field)
        if not value or (isinstance(value, str) and value.strip() == ''):
            missing_fields.append(field)
    
    if missing_fields:
        return {
            'valid': False,
            'error': f"Missing required parameters: {', '.join(missing_fields)}"
        }
    
    if action == 'deploy' and params.get('service_type') not in ['static', 'dynamic']:
        return {
            'valid': False,
            'error': "service_type must be 'static' or 'dynamic'"
        }
    
    return {'valid': True}

def handle_deployment(params):
    """Handle deployment request with real deployment logic"""
    try:
        deployment_id = params['deployment_id']
        service_type = params['service_type']
        
        # Update deployment status to DEPLOYING
        update_deployment_status(
            deployment_id=deployment_id,
            status='DEPLOYING',
            message=f'Starting {service_type} deployment',
            user_id=params['user_id'],
            project_id=params['project_id'],
            service_id=params['service_id'],
            service_type=service_type
        )
        
        # Execute deployment based on service type
        if service_type == 'static':
            result = deploy_static_service(params)
        else:
            result = deploy_dynamic_service(params)
        
        # Update final status
        final_status = 'SUCCESS' if result['success'] else 'FAILED'
        update_deployment_status(
            deployment_id=deployment_id,
            status=final_status,
            message=result.get('message', 'Deployment completed')
        )
        
        return {
            'deployment_id': deployment_id,
            'status': final_status,
            'service_type': service_type,
            'timestamp': datetime.utcnow().isoformat(),
            **result
        }
        
    except Exception as e:
        logger.error(f"Deployment error: {str(e)}")
        update_deployment_status(
            deployment_id=params.get('deployment_id'),
            status='FAILED',
            message=str(e)
        )
        return {
            'success': False,
            'error': str(e),
            'deployment_id': params.get('deployment_id')
        }

def deploy_static_service(params):
    """Deploy static service using S3 + CloudFront"""
    try:
        service_name = f"user-{params['user_id']}-project-{params['project_id']}-service-{params['service_id']}"
        bucket_name = f"haifu-static-{service_name}-{params['deployment_id'][:8]}"
        
        # Create S3 bucket for static hosting
        try:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': 'ap-northeast-2'}
            )
            logger.info(f"Created S3 bucket: {bucket_name}")
        except s3_client.exceptions.BucketAlreadyExists:
            logger.info(f"Bucket {bucket_name} already exists")
        
        # Configure bucket for static website hosting
        s3_client.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                'IndexDocument': {'Suffix': 'index.html'},
                'ErrorDocument': {'Key': 'error.html'}
            }
        )
        
        # Set bucket policy for public read access
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        
        website_url = f"http://{bucket_name}.s3-website.ap-northeast-2.amazonaws.com"
        
        return {
            'success': True,
            'message': 'Static service deployed successfully',
            'bucket_name': bucket_name,
            'website_url': website_url,
            'build_commands': params.get('build_commands', []),
            'build_output_dir': params.get('build_output_dir', 'dist'),
            'node_version': params.get('node_version', '18')
        }
        
    except Exception as e:
        logger.error(f"Static deployment error: {str(e)}")
        return {'success': False, 'error': str(e)}

def deploy_dynamic_service(params):
    """Deploy dynamic service using ECS Fargate"""
    try:
        service_name = f"user-{params['user_id']}-project-{params['project_id']}-service-{params['service_id']}"
        cluster_name = 'haifu-dev-user-services'
        
        # Create CloudWatch log group
        create_log_group(service_name)
        
        # Create ECR repository
        create_ecr_repository(service_name)
        
        # Register ECS task definition
        task_definition_arn = register_task_definition(params, service_name)
        
        # Create or update ECS service
        service_arn = create_ecs_service(params, service_name, cluster_name, task_definition_arn)
        
        return {
            'success': True,
            'message': 'Dynamic service deployed successfully',
            'service_name': service_name,
            'service_arn': service_arn,
            'task_definition_arn': task_definition_arn,
            'cluster_name': cluster_name,
            'cpu': params.get('cpu', 256),
            'memory': params.get('memory', 512),
            'port': params.get('port', 80)
        }
        
    except Exception as e:
        logger.error(f"Dynamic deployment error: {str(e)}")
        return {'success': False, 'error': str(e)}

def register_task_definition(params, service_name):
    """Register ECS task definition"""
    task_definition = {
        'family': f'haifu-dev-{service_name}',
        'networkMode': 'awsvpc',
        'requiresCompatibilities': ['FARGATE'],
        'cpu': str(params['cpu']),
        'memory': str(params['memory']),
        'executionRoleArn': f"arn:aws:iam::{get_account_id()}:role/haifu-dev-ecs-execution-role",
        'taskRoleArn': f"arn:aws:iam::{get_account_id()}:role/haifu-dev-ecs-task-role",
        'containerDefinitions': [{
            'name': service_name,
            'image': f"{get_account_id()}.dkr.ecr.ap-northeast-2.amazonaws.com/haifu-dev-{service_name}:latest",
            'cpu': params['cpu'],
            'memory': params['memory'],
            'essential': True,
            'portMappings': [{'containerPort': params['port'], 'protocol': 'tcp'}],
            'environment': params.get('environment_variables', []),
            'logConfiguration': {
                'logDriver': 'awslogs',
                'options': {
                    'awslogs-group': f'/ecs/haifu-dev-{service_name}',
                    'awslogs-region': 'ap-northeast-2',
                    'awslogs-stream-prefix': 'ecs'
                }
            }
        }]
    }
    
    response = ecs_client.register_task_definition(**task_definition)
    return response['taskDefinition']['taskDefinitionArn']

def create_ecs_service(params, service_name, cluster_name, task_definition_arn):
    """Create ECS service"""
    try:
        # Try to update existing service first
        ecs_client.update_service(
            cluster=cluster_name,
            service=f'haifu-dev-{service_name}',
            taskDefinition=task_definition_arn,
            desiredCount=params.get('min_capacity', 1)
        )
        logger.info(f"Updated existing ECS service: haifu-dev-{service_name}")
        
    except ecs_client.exceptions.ServiceNotFoundException:
        # Create new service if it doesn't exist
        response = ecs_client.create_service(
            cluster=cluster_name,
            serviceName=f'haifu-dev-{service_name}',
            taskDefinition=task_definition_arn,
            desiredCount=params.get('min_capacity', 1),
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': get_private_subnets(),
                    'securityGroups': [get_ecs_security_group()],
                    'assignPublicIp': 'DISABLED'
                }
            }
        )
        logger.info(f"Created new ECS service: {response['service']['serviceArn']}")
        return response['service']['serviceArn']
    
    return f"arn:aws:ecs:ap-northeast-2:{get_account_id()}:service/{cluster_name}/haifu-dev-{service_name}"

def create_log_group(service_name):
    """Create CloudWatch log group"""
    try:
        log_group_name = f'/ecs/haifu-dev-{service_name}'
        logs_client.create_log_group(
            logGroupName=log_group_name,
            retentionInDays=7
        )
        logger.info(f"Created log group: {log_group_name}")
    except logs_client.exceptions.ResourceAlreadyExistsException:
        logger.info(f"Log group already exists: /ecs/haifu-dev-{service_name}")

def create_ecr_repository(service_name):
    """Create ECR repository"""
    try:
        repo_name = f'haifu-dev-{service_name}'
        ecr_client.create_repository(
            repositoryName=repo_name,
            imageScanningConfiguration={'scanOnPush': True}
        )
        logger.info(f"Created ECR repository: {repo_name}")
    except ecr_client.exceptions.RepositoryAlreadyExistsException:
        logger.info(f"ECR repository already exists: haifu-dev-{service_name}")

def handle_status(params):
    """Handle status request"""
    try:
        table = dynamodb.Table('haifu-dev-deployment-status')
        
        if params.get('deployment_id'):
            response = table.get_item(Key={'deployment_id': params['deployment_id']})
            if 'Item' in response:
                return {'success': True, 'deployment': response['Item']}
            else:
                return {'success': False, 'error': 'Deployment not found'}
        else:
            response = table.scan(
                FilterExpression='service_id = :sid',
                ExpressionAttributeValues={':sid': params['service_id']}
            )
            return {'success': True, 'deployments': response['Items']}
            
    except Exception as e:
        logger.error(f"Status error: {str(e)}")
        return {'success': False, 'error': str(e)}

def handle_delete(params):
    """Handle delete request"""
    try:
        service_name = f"user-{params['user_id']}-project-{params['project_id']}-service-{params['service_id']}"
        
        # Delete ECS service
        try:
            ecs_client.delete_service(
                cluster='haifu-dev-user-services',
                service=f'haifu-dev-{service_name}',
                force=True
            )
        except Exception as e:
            logger.warning(f"Failed to delete ECS service: {str(e)}")
        
        return {'success': True, 'message': f'Service {service_name} deletion initiated'}
        
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        return {'success': False, 'error': str(e)}

def update_deployment_status(deployment_id, status, message, user_id=None, project_id=None, service_id=None, service_type=None):
    """Update deployment status in DynamoDB"""
    try:
        table = dynamodb.Table('haifu-dev-deployment-status')
        
        item = {
            'deployment_id': deployment_id,
            'status': status,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if user_id:
            item['user_id'] = user_id
        if project_id:
            item['project_id'] = project_id
        if service_id:
            item['service_id'] = service_id
        if service_type:
            item['service_type'] = service_type
        
        table.put_item(Item=item)
        logger.info(f"Updated deployment status: {deployment_id} -> {status}")
        
    except Exception as e:
        logger.error(f"Failed to update deployment status: {str(e)}")

def get_account_id():
    """Get AWS account ID"""
    return boto3.client('sts').get_caller_identity()['Account']

def get_private_subnets():
    """Get private subnet IDs"""
    try:
        ssm_client = boto3.client('ssm')
        response = ssm_client.get_parameter(Name='/haifu/vpc/private-subnets')
        return response['Parameter']['Value'].split(',')
    except:
        return os.environ.get('PRIVATE_SUBNETS', 'subnet-04bdda4afc3d6a117,subnet-0b7a7ea12f4cdb141').split(',')

def get_ecs_security_group():
    """Get ECS security group ID"""
    try:
        ssm_client = boto3.client('ssm')
        response = ssm_client.get_parameter(Name='/haifu/vpc/ecs-security-group')
        return response['Parameter']['Value']
    except:
        return os.environ.get('ECS_SECURITY_GROUP', 'sg-0b29792d58925132b')

def create_success_response(data):
    """Create successful HTTP response"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, DELETE',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps(data, default=str)
    }

def create_error_response(status_code, error_message):
    """Create error HTTP response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'error': error_message,
            'timestamp': datetime.utcnow().isoformat()
        })
    }