import json
import boto3
import logging
import uuid
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Debug version - returns all received data
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
        
        # Parse body
        raw_body = event.get('body', '{}')
        logger.info(f"Raw body: {raw_body}")
        
        body = {}
        if raw_body:
            if event.get('isBase64Encoded', False):
                import base64
                raw_body = base64.b64decode(raw_body).decode('utf-8')
                logger.info(f"Decoded body: {raw_body}")
            
            try:
                body = json.loads(raw_body)
                logger.info(f"Parsed body: {json.dumps(body, default=str)}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                body = {}
        
        # Extract parameters
        if http_method == 'GET':
            query_params = event.get('queryStringParameters') or {}
            params = {
                'user_id': query_params.get('user_id'),
                'project_id': query_params.get('project_id'),
                'service_id': query_params.get('service_id'),
                'service_type': query_params.get('service_type')
            }
        else:
            params = {
                'user_id': body.get('user_id'),
                'project_id': body.get('project_id'),
                'service_id': body.get('service_id'),
                'service_type': body.get('service_type')
            }
        
        logger.info(f"Extracted params: {json.dumps(params, default=str)}")
        
        # Return debug information
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, DELETE',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': json.dumps({
                'debug': True,
                'http_method': http_method,
                'path': path,
                'raw_body': raw_body,
                'parsed_body': body,
                'extracted_params': params,
                'event_keys': list(event.keys()),
                'isBase64Encoded': event.get('isBase64Encoded', False),
                'timestamp': datetime.utcnow().isoformat()
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
                'event': str(event)[:1000]  # Limit size
            })
        }