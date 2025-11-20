import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
apigateway = boto3.client('apigatewaymanagementapi')

def handler(event, context):
    """
    WebSocket Lambda handler
    Handles real-time deployment status updates
    """
    try:
        route_key = event.get('requestContext', {}).get('routeKey')
        connection_id = event.get('requestContext', {}).get('connectionId')
        
        logger.info(f"Route: {route_key}, Connection: {connection_id}")
        
        if route_key == '$connect':
            return handle_connect(connection_id)
        elif route_key == '$disconnect':
            return handle_disconnect(connection_id)
        elif route_key == 'deploy_status':
            return handle_deploy_status(event, connection_id)
        else:
            return {'statusCode': 400, 'body': 'Unknown route'}
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}

def handle_connect(connection_id):
    """Handle WebSocket connection"""
    logger.info(f"Client connected: {connection_id}")
    return {'statusCode': 200}

def handle_disconnect(connection_id):
    """Handle WebSocket disconnection"""
    logger.info(f"Client disconnected: {connection_id}")
    return {'statusCode': 200}

def handle_deploy_status(event, connection_id):
    """Handle deployment status request"""
    try:
        body = json.loads(event.get('body', '{}'))
        deployment_id = body.get('deployment_id')
        
        if not deployment_id:
            return {'statusCode': 400, 'body': 'deployment_id required'}
        
        # Get deployment status from DynamoDB
        table = dynamodb.Table('haifu-dev-deployment-status')
        response = table.get_item(Key={'deployment_id': deployment_id})
        
        if 'Item' in response:
            status_data = response['Item']
            # Send status to client
            send_message_to_client(connection_id, status_data)
            return {'statusCode': 200}
        else:
            return {'statusCode': 404, 'body': 'Deployment not found'}
            
    except Exception as e:
        logger.error(f"Error handling deploy status: {str(e)}")
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}

def send_message_to_client(connection_id, message):
    """Send message to WebSocket client"""
    try:
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise e