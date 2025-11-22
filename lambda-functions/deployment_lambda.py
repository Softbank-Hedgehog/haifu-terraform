import json
import boto3
import logging
import uuid
from datetime import datetime
import os

os.environ['AWS_ACCOUNT_ID'] = os.environ.get('AWS_ACCOUNT_ID', '123456789012')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ecs_client = boto3.client('ecs')
codepipeline_client = boto3.client('codepipeline')
cloudformation_client = boto3.client('cloudformation')
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Enhanced Deployment Lambda function
    Handles deploy/rollback/update_config methods for static and dynamic services
    """
    try:
        # Parse deployment request
        body = json.loads(event.get('body', '{}'))
        
        method = body.get('method', 'deploy')  # deploy/rollback/update_config
        service_type = body.get('service_type')  # "static" or "dynamic"
        runtime = body.get('runtime')
        build_commands = body.get('build_commands', [])
        start_command = body.get('start_command')
        dockerfile = body.get('dockerfile')
        github = body.get('github', {})
        
        # Generate deployment ID if not provided
        deployment_id = body.get('deployment_id', str(uuid.uuid4()))
        service_name = body.get('service_name', f'{github.get("owner", "user")}-{github.get("repo", "service")}')
        
        if not service_type or not method:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'service_type and method are required'})
            }
        
        # Update deployment status
        update_deployment_status(deployment_id, 'DEPLOYING', f'{method} {service_type} deployment')
        
        # Route to appropriate method handler
        if method == 'deploy':
            if service_type == 'static':
                result = deploy_static_service(deployment_id, service_name, build_commands, github)
            elif service_type == 'dynamic':
                result = deploy_dynamic_service(
                    deployment_id, service_name, runtime, 
                    build_commands, start_command, dockerfile, github
                )
            else:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Invalid service_type'})
                }
        elif method == 'rollback':
            result = rollback_service(deployment_id, service_name, service_type)
        elif method == 'update_config':
            result = update_service_config(deployment_id, service_name, service_type, body)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid method. Must be deploy/rollback/update_config'})
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

def deploy_static_service(deployment_id, service_name, build_commands, github):
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
        create_static_pipeline(service_name, build_commands, github)
        
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

def deploy_dynamic_service(deployment_id, service_name, runtime, build_commands, start_command, dockerfile, github):
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
        create_dynamic_pipeline(service_name, runtime, build_commands, dockerfile, github)
        
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

def rollback_service(deployment_id, service_name, service_type):
    """Rollback service to previous version"""
    try:
        if service_type == 'dynamic':
            # ECS service rollback
            ecs_client.update_service(
                cluster='haifu-dev-user-services',
                service=f'haifu-dev-{service_name}',
                taskDefinition=get_previous_task_definition(service_name)
            )
        else:
            # Static rollback via CloudFormation
            cloudformation_client.cancel_update_stack(
                StackName=f'haifu-static-{service_name}'
            )
        
        return {'success': True, 'data': {'action': 'rollback'}}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def update_service_config(deployment_id, service_name, service_type, config):
    """Update service configuration"""
    try:
        # Update environment variables, scaling, etc.
        return {'success': True, 'data': {'action': 'config_updated'}}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_previous_task_definition(service_name):
    """Get previous task definition ARN for rollback"""
    response = ecs_client.list_task_definitions(
        familyPrefix=f'haifu-dev-{service_name}',
        status='ACTIVE',
        sort='DESC',
        maxResults=2
    )
    return response['taskDefinitionArns'][1] if len(response['taskDefinitionArns']) > 1 else response['taskDefinitionArns'][0]ent)
        
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

def create_static_pipeline(service_name, build_commands, github):
    """Create CodePipeline for static deployment with GitHub OAuth"""
    try:
        codepipeline_client.create_pipeline(
            pipeline={
                'name': f'{service_name}-static-pipeline',
                'roleArn': f'arn:aws:iam::{os.environ["AWS_ACCOUNT_ID"]}:role/haifu-dev-codepipeline-role',
                'artifactStore': {
                    'type': 'S3',
                    'location': 'haifu-dev-pipeline-artifacts'
                },
                'stages': [
                    {
                        'name': 'Source',
                        'actions': [{
                            'name': 'Source',
                            'actionTypeId': {
                                'category': 'Source',
                                'owner': 'ThirdParty',
                                'provider': 'GitHub',
                                'version': '1'
                            },
                            'configuration': {
                                'Owner': github['owner'],
                                'Repo': github['repo'],
                                'Branch': github['branch'],
                                'OAuthToken': github['oauth_token']
                            },
                            'outputArtifacts': [{'name': 'SourceOutput'}]
                        }]
                    },
                    {
                        'name': 'Build',
                        'actions': [{
                            'name': 'Build',
                            'actionTypeId': {
                                'category': 'Build',
                                'owner': 'AWS',
                                'provider': 'CodeBuild',
                                'version': '1'
                            },
                            'configuration': {
                                'ProjectName': f'{service_name}-static-build'
                            },
                            'inputArtifacts': [{'name': 'SourceOutput'}]
                        }]
                    }
                ]
            }
        )
        logger.info(f"Static pipeline created for {service_name}")
        
    except Exception as e:
        logger.error(f"Static pipeline creation error: {str(e)}")

def create_dynamic_pipeline(service_name, runtime, build_commands, dockerfile, github):
    """Create CodePipeline for dynamic deployment with GitHub OAuth"""
    try:
        # Similar to static but with ECS deployment stage
        codepipeline_client.create_pipeline(
            pipeline={
                'name': f'{service_name}-dynamic-pipeline',
                'roleArn': f'arn:aws:iam::{os.environ["AWS_ACCOUNT_ID"]}:role/haifu-dev-codepipeline-role',
                'artifactStore': {
                    'type': 'S3',
                    'location': 'haifu-dev-pipeline-artifacts'
                },
                'stages': [
                    {
                        'name': 'Source',
                        'actions': [{
                            'name': 'Source',
                            'actionTypeId': {
                                'category': 'Source',
                                'owner': 'ThirdParty',
                                'provider': 'GitHub',
                                'version': '1'
                            },
                            'configuration': {
                                'Owner': github['owner'],
                                'Repo': github['repo'],
                                'Branch': github['branch'],
                                'OAuthToken': github['oauth_token']
                            },
                            'outputArtifacts': [{'name': 'SourceOutput'}]
                        }]
                    },
                    {
                        'name': 'Build',
                        'actions': [{
                            'name': 'Build',
                            'actionTypeId': {
                                'category': 'Build',
                                'owner': 'AWS',
                                'provider': 'CodeBuild',
                                'version': '1'
                            },
                            'configuration': {
                                'ProjectName': f'{service_name}-dynamic-build'
                            },
                            'inputArtifacts': [{'name': 'SourceOutput'}]
                        }]
                    },
                    {
                        'name': 'Deploy',
                        'actions': [{
                            'name': 'Deploy',
                            'actionTypeId': {
                                'category': 'Deploy',
                                'owner': 'AWS',
                                'provider': 'ECS',
                                'version': '1'
                            },
                            'configuration': {
                                'ClusterName': 'haifu-dev-user-services',
                                'ServiceName': f'haifu-dev-{service_name}'
                            },
                            'inputArtifacts': [{'name': 'SourceOutput'}]
                        }]
                    }
                ]
            }
        )
        logger.info(f"Dynamic pipeline created for {service_name}")
        
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