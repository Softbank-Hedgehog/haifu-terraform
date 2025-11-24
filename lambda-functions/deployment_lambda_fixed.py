import json
import boto3
import logging
import uuid
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Fixed Deployment Lambda function - handles Lambda Function URL format
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
        
        # Extract parameters - Lambda Function URL puts JSON data directly in event
        params = {}
        
        if http_method == 'GET':
            # For GET requests, use query parameters
            query_params = event.get('queryStringParameters') or {}
            params = {
                'user_id': query_params.get('user_id'),
                'project_id': query_params.get('project_id'),
                'service_id': query_params.get('service_id'),
                'service_type': query_params.get('service_type')
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
            
            params = {
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
                'port': body.get('port', 80)
            }
        
        logger.info(f"Extracted params: {json.dumps(params, default=str)}")
        
        # Validate required parameters
        required_fields = ['user_id', 'project_id', 'service_id', 'service_type']
        missing_fields = []
        
        for field in required_fields:
            value = params.get(field)
            if not value or (isinstance(value, str) and value.strip() == ''):
                missing_fields.append(field)
        
        if missing_fields:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': f"Missing required parameters: {', '.join(missing_fields)}",
                    'received_params': params,
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
        
        # Validate service_type
        if params.get('service_type') not in ['static', 'dynamic']:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': "service_type must be 'static' or 'dynamic'",
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
        
        # Process deployment
        deployment_id = params['deployment_id']
        service_type = params['service_type']
        
        # Update deployment status in DynamoDB
        try:
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table('haifu-dev-deployment-status')
            
            table.put_item(Item={
                'deployment_id': deployment_id,
                'user_id': params['user_id'],
                'project_id': params['project_id'],
                'service_id': params['service_id'],
                'service_type': service_type,
                'status': 'DEPLOYING',
                'message': f'Starting {service_type} deployment',
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to update DynamoDB: {str(e)}")
        
        # Simulate deployment process
        if service_type == 'static':
            result = {
                'success': True,
                'message': 'Static deployment initiated successfully',
                'bucket_name': f"haifu-static-{params['user_id']}-{params['project_id']}-{params['service_id']}",
                'build_commands': params.get('build_commands', []),
                'build_output_dir': params.get('build_output_dir', 'dist'),
                'node_version': params.get('node_version', '18')
            }
        else:
            result = {
                'success': True,
                'message': 'Dynamic deployment initiated successfully',
                'service_name': f"user-{params['user_id']}-project-{params['project_id']}-service-{params['service_id']}",
                'cpu': params.get('cpu', 256),
                'memory': params.get('memory', 512),
                'port': params.get('port', 80)
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, DELETE',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': json.dumps({
                'deployment_id': deployment_id,
                'service_type': service_type,
                'status': 'DEPLOYING',
                'timestamp': datetime.utcnow().isoformat(),
                **result
            }, default=str)
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }