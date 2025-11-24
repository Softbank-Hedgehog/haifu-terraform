import json
import boto3
import logging
from datetime import datetime

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
        elif route_key == 'message':
            return handle_message(event, connection_id)
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

def handle_message(event, connection_id):
    """Handle WebSocket messages (subscribe/unsubscribe logs)"""
    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        
        if action == 'subscribe_logs':
            return subscribe_to_logs(body, connection_id)
        elif action == 'unsubscribe_logs':
            return unsubscribe_from_logs(body, connection_id)
        else:
            return {'statusCode': 400, 'body': 'Invalid action'}
            
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}

def subscribe_to_logs(body, connection_id):
    """Subscribe to real-time pipeline logs"""
    try:
        user_id = body.get('user_id')
        project_id = body.get('project_id')
        service_id = body.get('service_id')
        
        if not all([user_id, project_id, service_id]):
            return {'statusCode': 400, 'body': 'user_id, project_id, service_id required'}
        
        # Store subscription in DynamoDB
        table = dynamodb.Table('websocket-connections')
        table.put_item(
            Item={
                'connection_id': connection_id,
                'user_id': user_id,
                'project_id': project_id,
                'service_id': service_id,
                'subscribed_at': datetime.utcnow().isoformat()
            }
        )
        
        # Get current pipeline status
        pipeline_name = f'user-{user_id}-project-{project_id}-service-{service_id}-pipeline'
        pipeline_logs = get_pipeline_logs(pipeline_name)
        
        # Send current status
        send_message_to_client(connection_id, {
            'type': 'pipeline_logs',
            'service_id': service_id,
            'logs': pipeline_logs
        })
        
        return {'statusCode': 200}
        
    except Exception as e:
        logger.error(f"Error subscribing to logs: {str(e)}")
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}

def unsubscribe_from_logs(body, connection_id):
    """Unsubscribe from pipeline logs"""
    try:
        table = dynamodb.Table('websocket-connections')
        table.delete_item(Key={'connection_id': connection_id})
        return {'statusCode': 200}
        
    except Exception as e:
        logger.error(f"Error unsubscribing: {str(e)}")
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}

def get_pipeline_logs(pipeline_name):
    """Get CodePipeline execution logs"""
    try:
        codepipeline = boto3.client('codepipeline')
        
        # Get pipeline executions
        response = codepipeline.list_pipeline_executions(
            pipelineName=pipeline_name,
            maxResults=5
        )
        
        logs = []
        for execution in response.get('pipelineExecutionSummaries', []):
            logs.append({
                'execution_id': execution['pipelineExecutionId'],
                'status': execution['status'],
                'start_time': execution.get('startTime', '').isoformat() if execution.get('startTime') else '',
                'last_update': execution.get('lastUpdateTime', '').isoformat() if execution.get('lastUpdateTime') else ''
            })
        
        return logs
        
    except Exception as e:
        logger.error(f"Error getting pipeline logs: {str(e)}")
        return []

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