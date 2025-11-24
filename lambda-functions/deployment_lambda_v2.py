import json
import boto3
import logging
import uuid
from datetime import datetime
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
ecs_client = boto3.client('ecs')
s3_client = boto3.client('s3')
cloudformation_client = boto3.client('cloudformation')

def handler(event, context):
    """
    Enhanced Deployment Lambda function for hAIfu platform
    Handles deployment, status, and management of static and dynamic services
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
        
        logger.info(f"HTTP Method: {http_method}, Path: {path}")
        
        # Determine action based on path
        if path.endswith('/deploy'):
            action = 'deploy'
        elif path.endswith('/status'):
            action = 'status'
        elif path.endswith('/delete'):
            action = 'delete'
        elif path.endswith('/rollback'):
            action = 'rollback'
        else:
            action = 'deploy'  # Default action
        
        # Parse request body
        body = parse_request_body(event)
        logger.info(f"Parsed body: {json.dumps(body, default=str)}")
        
        # Extract parameters
        params = extract_parameters(event, body, http_method)
        logger.info(f"Extracted params: {json.dumps(params, default=str)}")
        
        # Validate required parameters
        validation_result = validate_parameters(params, action)
        if not validation_result['valid']:
            return create_error_response(400, validation_result['error'])
        
        # Route to appropriate handler
        if action == 'deploy':
            result = handle_deploy(params)
        elif action == 'status':
            result = handle_status(params)
        elif action == 'delete':
            result = handle_delete(params)
        elif action == 'rollback':
            result = handle_rollback(params)
        else:
            return create_error_response(400, f"Unknown action: {action}")
        
        return create_success_response(result)
        
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return create_error_response(500, f"Internal server error: {str(e)}")

def parse_request_body(event):
    """Parse and decode request body"""
    try:
        raw_body = event.get('body', '{}')
        logger.info(f"Raw body: {raw_body}")
        
        if not raw_body or raw_body == '{}':
            return {}
        
        # Handle base64 encoded body
        if event.get('isBase64Encoded', False):
            import base64
            raw_body = base64.b64decode(raw_body).decode('utf-8')
            logger.info(f"Decoded body: {raw_body}")
        
        parsed_body = json.loads(raw_body)
        logger.info(f"Parsed JSON body: {json.dumps(parsed_body, default=str)}")
        return parsed_body
        
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Failed to parse body: {str(e)}, raw_body: {raw_body}")
        return {}

def extract_parameters(event, body, http_method):
    """Extract parameters from request"""
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
        # Convert all values to strings to ensure they exist
        params = {
            'user_id': str(body.get('user_id', '')) if body.get('user_id') else None,
            'project_id': str(body.get('project_id', '')) if body.get('project_id') else None,
            'service_id': str(body.get('service_id', '')) if body.get('service_id') else None,
            'service_type': body.get('service_type'),
            'deployment_id': body.get('deployment_id', str(uuid.uuid4())),
            'runtime': body.get('runtime'),
            'build_commands': body.get('build_commands', []),
            'start_command': body.get('start_command'),
            'environment_variables': body.get('environment_variables', []),
            'cpu': body.get('cpu', 256),
            'memory': body.get('memory', 512),
            'port': body.get('port', 80),
            'min_capacity': body.get('min_capacity', 1),
            'max_capacity': body.get('max_capacity', 10),
            'build_output_dir': body.get('build_output_dir', 'dist'),
            'node_version': body.get('node_version', '18')
        }
        return params

def validate_parameters(params, action):
    """Validate required parameters"""
    required_fields = ['user_id', 'project_id', 'service_id']
    
    if action == 'deploy':
        required_fields.append('service_type')
    
    # Check for missing or empty fields
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
    
    # Validate service_type for deploy action
    if action == 'deploy' and params.get('service_type') not in ['static', 'dynamic']:
        return {
            'valid': False,
            'error': "service_type must be 'static' or 'dynamic'"
        }
    
    return {'valid': True}

def handle_deploy(params):
    """Handle deployment request"""
    try:
        deployment_id = params['deployment_id']
        service_type = params['service_type']
        
        # Update deployment status
        update_deployment_status(
            deployment_id=deployment_id,
            status='DEPLOYING',
            message=f'Starting {service_type} deployment',
            user_id=params['user_id'],
            project_id=params['project_id'],
            service_id=params['service_id'],
            service_type=service_type
        )
        
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
            **result
        }
        
    except Exception as e:
        logger.error(f"Deploy error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'deployment_id': params.get('deployment_id')
        }

def handle_status(params):
    """Handle status request"""
    try:
        # Get deployment status from DynamoDB
        table = dynamodb.Table('haifu-dev-deployment-status')
        
        if params.get('deployment_id'):
            # Get specific deployment status
            response = table.get_item(
                Key={'deployment_id': params['deployment_id']}
            )
            if 'Item' in response:
                return {'success': True, 'deployment': response['Item']}
            else:
                return {'success': False, 'error': 'Deployment not found'}
        else:
            # Get all deployments for service
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
        
        # Mark as deleting
        update_deployment_status(
            deployment_id=str(uuid.uuid4()),
            status='DELETING',
            message='Deleting service',
            user_id=params['user_id'],
            project_id=params['project_id'],
            service_id=params['service_id']
        )
        
        # TODO: Implement actual deletion logic
        # This would involve deleting ECS services, CloudFormation stacks, etc.
        
        return {
            'success': True,
            'message': f'Service {service_name} deletion initiated'
        }
        
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        return {'success': False, 'error': str(e)}

def handle_rollback(params):
    """Handle rollback request"""
    try:
        # TODO: Implement rollback logic
        return {
            'success': True,
            'message': 'Rollback initiated'
        }
        
    except Exception as e:
        logger.error(f"Rollback error: {str(e)}")
        return {'success': False, 'error': str(e)}

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
            
            # Configure bucket for static website hosting
            s3_client.put_bucket_website(
                Bucket=bucket_name,
                WebsiteConfiguration={
                    'IndexDocument': {'Suffix': 'index.html'},
                    'ErrorDocument': {'Key': 'error.html'}
                }
            )
            
            logger.info(f"Created S3 bucket: {bucket_name}")
            
        except s3_client.exceptions.BucketAlreadyExists:
            logger.info(f"Bucket {bucket_name} already exists")
        
        return {
            'success': True,
            'message': 'Static service deployed successfully',
            'bucket_name': bucket_name,
            'website_url': f"http://{bucket_name}.s3-website.ap-northeast-2.amazonaws.com"
        }
        
    except Exception as e:
        logger.error(f"Static deployment error: {str(e)}")
        return {'success': False, 'error': str(e)}

def deploy_dynamic_service(params):
    """Deploy dynamic service using ECS Fargate"""
    try:
        service_name = f"user-{params['user_id']}-project-{params['project_id']}-service-{params['service_id']}"
        cluster_name = 'haifu-dev-user-services'
        
        # Create ECS task definition
        task_definition = {
            'family': f'haifu-dev-{service_name}',
            'networkMode': 'awsvpc',
            'requiresCompatibilities': ['FARGATE'],
            'cpu': str(params['cpu']),
            'memory': str(params['memory']),
            'executionRoleArn': get_execution_role_arn(),
            'containerDefinitions': [{
                'name': service_name,
                'image': f'{get_account_id()}.dkr.ecr.ap-northeast-2.amazonaws.com/haifu-dev-{service_name}:latest',
                'cpu': params['cpu'],
                'memory': params['memory'],
                'essential': True,
                'portMappings': [{'containerPort': params['port'], 'protocol': 'tcp'}],
                'environment': params['environment_variables'],
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
        
        # Register task definition
        task_def_response = ecs_client.register_task_definition(**task_definition)
        
        logger.info(f"Registered task definition: {task_def_response['taskDefinition']['taskDefinitionArn']}")
        
        return {
            'success': True,
            'message': 'Dynamic service deployed successfully',
            'task_definition_arn': task_def_response['taskDefinition']['taskDefinitionArn']
        }
        
    except Exception as e:
        logger.error(f"Dynamic deployment error: {str(e)}")
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
        
        # Add optional fields
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

def get_execution_role_arn():
    """Get ECS execution role ARN"""
    return f"arn:aws:iam::{get_account_id()}:role/haifu-dev-ecs-execution-role"

def get_account_id():
    """Get AWS account ID"""
    return boto3.client('sts').get_caller_identity()['Account']

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
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, DELETE',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps({
            'error': error_message,
            'timestamp': datetime.utcnow().isoformat()
        })
    }