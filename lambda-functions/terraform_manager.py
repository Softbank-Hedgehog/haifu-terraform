import json
import boto3
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Terraform Manager Lambda
    Dynamically creates and manages Terraform configurations for user deployments
    """
    try:
        body = json.loads(event.get('body', '{}'))
        
        action = body.get('action')  # 'create', 'update', 'destroy'
        service_type = body.get('service_type')  # 'static' or 'dynamic'
        service_name = body.get('service_name')
        deployment_config = body.get('deployment_config', {})
        
        if action == 'create':
            result = create_service_config(service_type, service_name, deployment_config)
        elif action == 'update':
            result = update_service_config(service_type, service_name, deployment_config)
        elif action == 'destroy':
            result = destroy_service_config(service_type, service_name)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid action'})
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Terraform manager error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def create_service_config(service_type, service_name, config):
    """Create Terraform configuration for new service"""
    
    # Generate Terraform variable configuration
    if service_type == 'static':
        tf_config = generate_static_config(service_name, config)
    else:
        tf_config = generate_dynamic_config(service_name, config)
    
    # Store configuration in S3
    config_key = f"terraform-configs/{service_type}/{service_name}.tfvars"
    s3_client.put_object(
        Bucket='haifu-terraform-configs',
        Key=config_key,
        Body=tf_config,
        ContentType='text/plain'
    )
    
    # Update service registry in DynamoDB
    update_service_registry(service_name, service_type, 'active', config_key)
    
    return {
        'service_name': service_name,
        'service_type': service_type,
        'config_path': config_key,
        'status': 'created'
    }

def generate_static_config(service_name, config):
    """Generate Terraform variables for static service"""
    
    runtime = config.get('runtime', 'nodejs18')
    build_config = config.get('build_config', {})
    
    tf_vars = {
        'user_static_services': {
            service_name: {
                'github_owner': config.get('github_owner', ''),
                'github_repo': config.get('github_repo', ''),
                'github_branch': config.get('github_branch', 'main'),
                'install_commands': build_config.get('install_commands', ['npm install']),
                'build_commands': build_config.get('build_commands', ['npm run build'])
            }
        }
    }
    
    return format_terraform_vars(tf_vars)

def generate_dynamic_config(service_name, config):
    """Generate Terraform variables for dynamic service"""
    
    runtime = config.get('runtime', 'nodejs18')
    build_config = config.get('build_config', {})
    start_command = config.get('start_command', 'npm start')
    
    # Determine resource specs based on runtime
    cpu, memory = get_resource_specs_for_runtime(runtime)
    
    tf_vars = {
        'user_dynamic_services': {
            service_name: {
                'runtime': runtime,
                'cpu': cpu,
                'memory': memory,
                'github_repository': config.get('github_repository', ''),
                'github_branch': config.get('github_branch', 'main'),
                'install_commands': build_config.get('install_commands', []),
                'build_commands': build_config.get('build_commands', []),
                'start_command': start_command
            }
        }
    }
    
    return format_terraform_vars(tf_vars)

def get_resource_specs_for_runtime(runtime):
    """Get CPU and memory specs based on runtime"""
    specs = {
        'nodejs18': (256, 512),
        'nodejs20': (256, 512),
        'python3.11': (256, 512),
        'python3.12': (256, 512),
        'java17': (512, 1024),
        'java21': (512, 1024),
        'go1.21': (256, 512),
        'dotnet8': (512, 1024)
    }
    return specs.get(runtime, (256, 512))

def format_terraform_vars(vars_dict):
    """Format Python dict as Terraform variables"""
    
    def format_value(value, indent=0):
        spaces = "  " * indent
        
        if isinstance(value, dict):
            lines = ["{"]
            for k, v in value.items():
                lines.append(f'{spaces}  "{k}" = {format_value(v, indent + 1)}')
            lines.append(f"{spaces}}}")
            return "\n".join(lines)
        elif isinstance(value, list):
            if not value:
                return "[]"
            items = [f'"{item}"' for item in value]
            return f"[{', '.join(items)}]"
        elif isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return f'"{str(value)}"'
    
    lines = []
    for key, value in vars_dict.items():
        lines.append(f'{key} = {format_value(value)}')
    
    return "\n".join(lines)

def update_service_config(service_type, service_name, config):
    """Update existing service configuration"""
    
    # Generate new configuration
    if service_type == 'static':
        tf_config = generate_static_config(service_name, config)
    else:
        tf_config = generate_dynamic_config(service_name, config)
    
    # Update configuration in S3
    config_key = f"terraform-configs/{service_type}/{service_name}.tfvars"
    s3_client.put_object(
        Bucket='haifu-terraform-configs',
        Key=config_key,
        Body=tf_config,
        ContentType='text/plain'
    )
    
    # Update service registry
    update_service_registry(service_name, service_type, 'updated', config_key)
    
    return {
        'service_name': service_name,
        'service_type': service_type,
        'config_path': config_key,
        'status': 'updated'
    }

def destroy_service_config(service_type, service_name):
    """Remove service configuration"""
    
    # Delete configuration from S3
    config_key = f"terraform-configs/{service_type}/{service_name}.tfvars"
    try:
        s3_client.delete_object(
            Bucket='haifu-terraform-configs',
            Key=config_key
        )
    except Exception as e:
        logger.warning(f"Could not delete S3 object {config_key}: {str(e)}")
    
    # Update service registry
    update_service_registry(service_name, service_type, 'destroyed', config_key)
    
    return {
        'service_name': service_name,
        'service_type': service_type,
        'status': 'destroyed'
    }

def update_service_registry(service_name, service_type, status, config_path):
    """Update service registry in DynamoDB"""
    
    try:
        table = dynamodb.Table('haifu-dev-service-registry')
        table.put_item(
            Item={
                'service_name': service_name,
                'service_type': service_type,
                'status': status,
                'config_path': config_path,
                'updated_at': datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"DynamoDB update error: {str(e)}")

def get_all_active_services():
    """Get all active services from registry"""
    
    try:
        table = dynamodb.Table('haifu-dev-service-registry')
        response = table.scan(
            FilterExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': 'active'}
        )
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"DynamoDB scan error: {str(e)}")
        return []