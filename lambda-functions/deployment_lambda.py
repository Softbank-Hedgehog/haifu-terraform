import json
import boto3
import logging
import uuid
from datetime import datetime
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ecs_client = boto3.client('ecs')
codepipeline_client = boto3.client('codepipeline')
cloudformation_client = boto3.client('cloudformation')
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Enhanced Deployment Lambda function
    Handles both static and dynamic service deployments
    """
    try:
        # Parse deployment request
        body = json.loads(event.get('body', '{}'))
        
        service_type = body.get('service_type')  # "static" or "dynamic"
        runtime = body.get('runtime')
        build_config = body.get('build_config', {})
        start_command = body.get('start_command')
        dockerfile_content = body.get('dockerfile_content')
        
        # Generate deployment ID if not provided
        deployment_id = body.get('deployment_id', str(uuid.uuid4()))
        service_name = body.get('service_name', f'service-{deployment_id[:8]}')
        
        if not service_type:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'service_type is required'})
            }
        
        # Update deployment status
        update_deployment_status(deployment_id, 'DEPLOYING', f'Starting {service_type} deployment')
        
        # Route to appropriate deployment handler
        if service_type == 'static':
            result = deploy_static_service(deployment_id, service_name, build_config)
        elif service_type == 'dynamic':
            result = deploy_dynamic_service(
                deployment_id, service_name, runtime, 
                build_config, start_command, dockerfile_content
            )
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid service_type. Must be "static" or "dynamic"'})
            }
        
        if result['success']:
            update_deployment_status(deployment_id, 'SUCCESS', 'Deployment completed')
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'deployment_id': deployment_id,
                    'service_name': service_name,
                    'service_type': service_type,
                    'status': 'SUCCESS',
                    **result['data']
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

def deploy_static_service(deployment_id, service_name, build_config):
    """
    Deploy static service using S3 + CloudFront via CloudFormation
    """
    try:
        stack_name = f'haifu-static-{service_name}'
        
        # CloudFormation template for static deployment
        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                "S3Bucket": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {
                        "BucketName": f"haifu-static-{service_name}-{deployment_id[:8]}",
                        "WebsiteConfiguration": {
                            "IndexDocument": "index.html",
                            "ErrorDocument": "error.html"
                        },
                        "PublicAccessBlockConfiguration": {
                            "BlockPublicAcls": False,
                            "BlockPublicPolicy": False,
                            "IgnorePublicAcls": False,
                            "RestrictPublicBuckets": False
                        }
                    }
                },
                "CloudFrontDistribution": {
                    "Type": "AWS::CloudFront::Distribution",
                    "Properties": {
                        "DistributionConfig": {
                            "Origins": [{
                                "DomainName": {"Fn::GetAtt": ["S3Bucket", "RegionalDomainName"]},
                                "Id": "S3Origin",
                                "S3OriginConfig": {}
                            }],
                            "DefaultCacheBehavior": {
                                "TargetOriginId": "S3Origin",
                                "ViewerProtocolPolicy": "redirect-to-https",
                                "AllowedMethods": ["GET", "HEAD"],
                                "CachedMethods": ["GET", "HEAD"],
                                "ForwardedValues": {"QueryString": False}
                            },
                            "Enabled": True,
                            "DefaultRootObject": "index.html"
                        }
                    }
                }
            },
            "Outputs": {
                "BucketName": {"Value": {"Ref": "S3Bucket"}},
                "CloudFrontURL": {"Value": {"Fn::GetAtt": ["CloudFrontDistribution", "DomainName"]}}
            }
        }
        
        # Create CloudFormation stack
        cloudformation_client.create_stack(
            StackName=stack_name,
            TemplateBody=json.dumps(template),
            Capabilities=['CAPABILITY_IAM']
        )
        
        # Create CodePipeline for continuous deployment
        create_static_pipeline(service_name, build_config)
        
        return {
            'success': True,
            'data': {
                'stack_name': stack_name,
                'deployment_type': 'static'
            }
        }
        
    except Exception as e:
        logger.error(f"Static deployment error: {str(e)}")
        return {'success': False, 'error': str(e)}

def deploy_dynamic_service(deployment_id, service_name, runtime, build_config, start_command, dockerfile_content):
    """
    Deploy dynamic service to ECS Fargate with auto-scaling
    """
    try:
        cluster_name = 'haifu-dev-user-services'
        
        # Create task definition with runtime-specific configuration
        cpu, memory = get_resource_specs(runtime)
        
        task_def_response = ecs_client.register_task_definition(
            family=f'haifu-dev-{service_name}',
            networkMode='awsvpc',
            requiresCompatibilities=['FARGATE'],
            cpu=str(cpu),
            memory=str(memory),
            executionRoleArn=f'arn:aws:iam::{context.invoked_function_arn.split(":")[4]}:role/haifu-dev-ecs-execution-role',
            containerDefinitions=[{
                'name': service_name,
                'image': f'{context.invoked_function_arn.split(":")[4]}.dkr.ecr.ap-northeast-2.amazonaws.com/haifu-dev-{service_name}:latest',
                'cpu': cpu,
                'memory': memory,
                'essential': True,
                'portMappings': [{'containerPort': 80, 'protocol': 'tcp'}],
                'environment': [
                    {'name': 'START_COMMAND', 'value': start_command or 'npm start'},
                    {'name': 'RUNTIME', 'value': runtime}
                ],
                'logConfiguration': {
                    'logDriver': 'awslogs',
                    'options': {
                        'awslogs-group': f'/ecs/haifu-dev-{service_name}',
                        'awslogs-region': 'ap-northeast-2',
                        'awslogs-stream-prefix': 'ecs'
                    }
                }
            }]
        )
        
        # Create ECS service with auto-scaling
        service_response = ecs_client.create_service(
            cluster=cluster_name,
            serviceName=f'haifu-dev-{service_name}',
            taskDefinition=task_def_response['taskDefinition']['taskDefinitionArn'],
            desiredCount=1,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': get_private_subnets(),
                    'securityGroups': [get_ecs_security_group()],
                    'assignPublicIp': 'DISABLED'
                }
            },
            loadBalancers=[{
                'targetGroupArn': get_target_group_arn(service_name),
                'containerName': service_name,
                'containerPort': 80
            }]
        )
        
        # Setup auto-scaling
        setup_auto_scaling(service_name, cluster_name)
        
        # Create CodePipeline for CI/CD
        create_dynamic_pipeline(service_name, runtime, build_config, dockerfile_content)
        
        return {
            'success': True,
            'data': {
                'service_arn': service_response['service']['serviceArn'],
                'deployment_type': 'dynamic',
                'runtime': runtime
            }
        }
        
    except Exception as e:
        logger.error(f"Dynamic deployment error: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_resource_specs(runtime):
    """Get CPU and memory specs based on runtime"""
    specs = {
        'nodejs18': (256, 512),
        'python3.11': (256, 512),
        'java17': (512, 1024),
        'go1.21': (256, 512)
    }
    return specs.get(runtime, (256, 512))

def setup_auto_scaling(service_name, cluster_name):
    """Setup auto-scaling for ECS service"""
    autoscaling_client = boto3.client('application-autoscaling')
    
    # Register scalable target
    autoscaling_client.register_scalable_target(
        ServiceNamespace='ecs',
        ResourceId=f'service/{cluster_name}/haifu-dev-{service_name}',
        ScalableDimension='ecs:service:DesiredCount',
        MinCapacity=1,
        MaxCapacity=10
    )
    
    # Create scaling policy
    autoscaling_client.put_scaling_policy(
        PolicyName=f'{service_name}-cpu-scaling',
        ServiceNamespace='ecs',
        ResourceId=f'service/{cluster_name}/haifu-dev-{service_name}',
        ScalableDimension='ecs:service:DesiredCount',
        PolicyType='TargetTrackingScaling',
        TargetTrackingScalingPolicyConfiguration={
            'TargetValue': 70.0,
            'PredefinedMetricSpecification': {
                'PredefinedMetricType': 'ECSServiceAverageCPUUtilization'
            }
        }
    )

def create_static_pipeline(service_name, build_config):
    """Create CodePipeline for static deployment"""
    try:
        # Invoke Terraform manager to create static service config
        lambda_client = boto3.client('lambda')
        
        payload = {
            'action': 'create',
            'service_type': 'static',
            'service_name': service_name,
            'deployment_config': {
                'build_config': build_config,
                'github_owner': 'user',  # This should come from user context
                'github_repo': service_name,
                'github_branch': 'main'
            }
        }
        
        response = lambda_client.invoke(
            FunctionName='haifu-dev-terraform-manager',
            InvocationType='RequestResponse',
            Payload=json.dumps({'body': json.dumps(payload)})
        )
        
        result = json.loads(response['Payload'].read())
        logger.info(f"Terraform config created: {result}")
        
    except Exception as e:
        logger.error(f"Static pipeline creation error: {str(e)}")

def create_dynamic_pipeline(service_name, runtime, build_config, dockerfile_content):
    """Create CodePipeline for dynamic deployment"""
    try:
        # Invoke Terraform manager to create dynamic service config
        lambda_client = boto3.client('lambda')
        
        payload = {
            'action': 'create',
            'service_type': 'dynamic',
            'service_name': service_name,
            'deployment_config': {
                'runtime': runtime,
                'build_config': build_config,
                'start_command': 'npm start',  # This should be determined by AI
                'github_repository': f'user/{service_name}',  # This should come from user context
                'github_branch': 'main'
            }
        }
        
        response = lambda_client.invoke(
            FunctionName='haifu-dev-terraform-manager',
            InvocationType='RequestResponse',
            Payload=json.dumps({'body': json.dumps(payload)})
        )
        
        result = json.loads(response['Payload'].read())
        logger.info(f"Terraform config created: {result}")
        
    except Exception as e:
        logger.error(f"Dynamic pipeline creation error: {str(e)}")

def get_private_subnets():
    """Get private subnet IDs from environment or SSM"""
    return ['subnet-xxx', 'subnet-yyy']  # Replace with actual subnet lookup

def get_ecs_security_group():
    """Get ECS security group ID"""
    return 'sg-xxx'  # Replace with actual security group lookup

def get_target_group_arn(service_name):
    """Get or create target group for the service"""
    return f'arn:aws:elasticloadbalancing:ap-northeast-2:ACCOUNT:targetgroup/{service_name}/xxx'  # Replace with actual target group creation

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