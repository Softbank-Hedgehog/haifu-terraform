import json
import boto3
import logging
import uuid
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Simple Deployment Lambda function for testing
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse request
        if 'requestContext' in event and 'http' in event['requestContext']:
            http_method = event['requestContext']['http']['method']
            path = event.get('rawPath', '')
        else:
            http_method = event.get('httpMethod', 'POST')
            path = event.get('path', '')
        
        # Parse body
        raw_body = event.get('body', '{}')
        if raw_body:
            if event.get('isBase64Encoded', False):
                import base64
                raw_body = base64.b64decode(raw_body).decode('utf-8')
            body = json.loads(raw_body)
        else:
            body = {}
        
        # Extract parameters
        user_id = None
        project_id = None
        service_id = None
        
        if http_method == 'GET':
            query_params = event.get('queryStringParameters') or {}
            user_id = query_params.get('user_id')
            project_id = query_params.get('project_id')
            service_id = query_params.get('service_id')
        else:
            user_id = body.get('user_id')
            project_id = body.get('project_id')
            service_id = body.get('service_id')
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Lambda function is working correctly',
                'method': http_method,
                'path': path,
                'user_id': user_id,
                'project_id': project_id,
                'service_id': service_id,
                'service_type': body.get('service_type'),
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Internal server error'
            })
        }