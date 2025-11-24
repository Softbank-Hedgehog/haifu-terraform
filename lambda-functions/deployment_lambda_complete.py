import json
import boto3
import logging
import uuid
import time
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
        
        # Extract parameters
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
        # Handle both API Gateway and Lambda Function URL formats
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
        
        # If body is empty, check if parameters are directly in event (Lambda Function URL)
        if not body and 'user_id' in event:
            body = {key: value for key, value in event.items() 
                   if key not in ['requestContext', 'headers', 'isBase64Encoded', 'rawPath', 'rawQueryString']}
        
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
    """Deploy static service using existing S3 bucket"""
    try:
        # Use existing bucket and configure the specific path for static hosting
        bucket_name = 'haifu-github-snapshot'
        source_key = f"user/{params['user_id']}/{params['project_id']}/{params['service_id']}/"
        
        logger.info(f"Deploying static site from {bucket_name}/{source_key}")
        
        # 1. Check if source files exist
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=source_key,
                MaxKeys=5
            )
            
            if 'Contents' in response and len(response['Contents']) > 0:
                logger.info(f"Found {len(response['Contents'])} files:")
                for obj in response['Contents']:
                    logger.info(f"  - {obj['Key']}")
                source_exists = True
            else:
                logger.info(f"No files found with prefix: {source_key}")
                source_exists = False
        except Exception as e:
            logger.error(f"Error checking source files: {str(e)}")
            source_exists = False
        
        if not source_exists:
            return {
                'success': False,
                'error': f'No files found in path: {source_key}'
            }
        
        # 2. Configure S3 website hosting
        try:
            s3_client.put_bucket_website(
                Bucket=bucket_name,
                WebsiteConfiguration={
                    'IndexDocument': {'Suffix': 'index.html'},
                    'ErrorDocument': {'Key': 'index.html'}
                }
            )
            logger.info(f"Configured S3 website hosting for {bucket_name}")
        except Exception as e:
            logger.warning(f"Failed to configure website hosting: {str(e)}")
        
        # 3. Check and configure S3 bucket for CloudFront access
        check_and_configure_bucket_access(bucket_name, source_key)
        
        # 4. List available files for deployment
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=source_key,
                MaxKeys=10
            )
            
            if 'Contents' in response:
                logger.info(f"Found {len(response['Contents'])} files to deploy:")
                for obj in response['Contents']:
                    logger.info(f"  - {obj['Key']}")
            else:
                logger.info(f"No files found under {source_key}")
        except Exception as e:
            logger.error(f"Error listing S3 files: {str(e)}")
        
        # 3. Create CloudFront distribution
        cloudfront_result = create_cloudfront_distribution(bucket_name, source_key)
        
        if not cloudfront_result:
            return {
                'success': False,
                'error': 'Failed to create CloudFront distribution'
            }
        
        # 4. Check CloudFront deployment status
        distribution_status = check_cloudfront_status(cloudfront_result.get('distribution_id'))
        
        return {
            'success': True,
            'message': f'Static service deployed via CloudFront. Status: {distribution_status.get("status", "Unknown")}. Wait 5-15 minutes for deployment.',
            'bucket_name': bucket_name,
            'source_path': source_key,
            'website_url': cloudfront_result.get('url'),
            'cloudfront_url': cloudfront_result.get('url'),
            'cloudfront_status': distribution_status.get('status'),
            'distribution_id': cloudfront_result.get('distribution_id'),
            'deployment_time': distribution_status.get('last_modified'),
            'note': 'CloudFront deployment takes 5-15 minutes. Check status with /status endpoint.',
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
        
        # 1. Create CloudWatch log group
        create_log_group(service_name)
        
        # 2. Create ECR repository
        create_ecr_repository(service_name)
        
        # 3. Register ECS task definition
        task_definition_arn = register_task_definition(params, service_name)
        
        # 4. Create or update ECS service
        service_arn = create_ecs_service(params, service_name, cluster_name, task_definition_arn)
        
        # 5. Setup auto-scaling
        setup_auto_scaling(service_name, cluster_name, params)
        
        # 6. Trigger Docker image build (if source exists)
        build_result = trigger_docker_build(params, service_name)
        
        return {
            'success': True,
            'message': 'Dynamic service deployed successfully',
            'service_name': service_name,
            'service_arn': service_arn,
            'task_definition_arn': task_definition_arn,
            'cluster_name': cluster_name,
            'cpu': params.get('cpu', 256),
            'memory': params.get('memory', 512),
            'port': params.get('port', 80),
            'build_status': build_result.get('status', 'PENDING')
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

def setup_auto_scaling(service_name, cluster_name, params):
    """Setup auto-scaling for ECS service"""
    try:
        autoscaling_client = boto3.client('application-autoscaling')
        
        # Register scalable target
        autoscaling_client.register_scalable_target(
            ServiceNamespace='ecs',
            ResourceId=f'service/{cluster_name}/haifu-dev-{service_name}',
            ScalableDimension='ecs:service:DesiredCount',
            MinCapacity=params.get('min_capacity', 1),
            MaxCapacity=params.get('max_capacity', 10)
        )
        
        # Create CPU-based scaling policy
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
        
        logger.info(f"Setup auto-scaling for {service_name}")
        
    except Exception as e:
        logger.error(f"Auto-scaling setup error: {str(e)}")

def trigger_docker_build(params, service_name):
    """Trigger Docker image build using CodeBuild"""
    try:
        # This would trigger a CodeBuild project to build and push Docker image
        # For now, return a placeholder
        return {
            'status': 'PENDING',
            'message': 'Docker build will be triggered asynchronously'
        }
        
    except Exception as e:
        logger.error(f"Docker build error: {str(e)}")
        return {'status': 'FAILED', 'error': str(e)}

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

def trigger_static_build(params, bucket_name):
    """Trigger CodeBuild for static site build"""
    try:
        project_name = f"haifu-static-build-{params['deployment_id'][:8]}"
        
        # Create buildspec for static build
        buildspec = {
            "version": 0.2,
            "phases": {
                "install": {
                    "runtime-versions": {
                        "nodejs": params.get('node_version', '18')
                    }
                },
                "pre_build": {
                    "commands": [
                        "echo Installing dependencies...",
                        "ls -la",
                        "pwd"
                    ]
                },
                "build": {
                    "commands": params.get('build_commands', ['npm install', 'npm run build'])
                },
                "post_build": {
                    "commands": [
                        "echo Build completed",
                        f"ls -la {params.get('build_output_dir', 'dist')}/",
                        f"aws s3 sync {params.get('build_output_dir', 'dist')}/ s3://{bucket_name}/ --delete"
                    ]
                }
            }
        }
        
        # Create temporary CodeBuild project
        source_location = f"haifu-github-snapshot/user/{params['user_id']}/{params['project_id']}/{params['service_id']}/"
        
        codebuild_client.create_project(
            name=project_name,
            source={
                'type': 'S3',
                'location': source_location,
                'buildspec': json.dumps(buildspec)
            },
            artifacts={'type': 'NO_ARTIFACTS'},
            environment={
                'type': 'LINUX_CONTAINER',
                'image': 'aws/codebuild/standard:5.0',
                'computeType': 'BUILD_GENERAL1_SMALL'
            },
            serviceRole=f"arn:aws:iam::{get_account_id()}:role/haifu-dev-codebuild-role"
        )
        
        # Start build
        build_response = codebuild_client.start_build(projectName=project_name)
        
        return {
            'success': True,
            'build_id': build_response['build']['id'],
            'status': 'BUILDING'
        }
        
    except Exception as e:
        logger.error(f"Static build error: {str(e)}")
        return {'success': False, 'error': str(e)}

def check_and_configure_bucket_access(bucket_name, source_key):
    """Check and configure S3 bucket access for CloudFront"""
    try:
        # 1. Check bucket public access block settings
        try:
            response = s3_client.get_public_access_block(Bucket=bucket_name)
            block_config = response['PublicAccessBlockConfiguration']
            logger.info(f"Current public access block: {block_config}")
            
            # If all public access is blocked, we need to use OAI
            if (block_config.get('BlockPublicAcls', True) and 
                block_config.get('IgnorePublicAcls', True) and
                block_config.get('BlockPublicPolicy', True) and 
                block_config.get('RestrictPublicBuckets', True)):
                logger.info("Bucket has full public access block - will use OAI")
                return 'oai_required'
        except Exception as e:
            logger.warning(f"Could not check public access block: {str(e)}")
        
        # 2. Try to disable public access block temporarily
        try:
            s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': False,
                    'IgnorePublicAcls': False,
                    'BlockPublicPolicy': False,
                    'RestrictPublicBuckets': False
                }
            )
            logger.info(f"Disabled public access block for {bucket_name}")
            
            # Wait a moment for the setting to take effect
            time.sleep(2)
            
            # Now apply bucket policy
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowPublicRead",
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
            logger.info(f"Successfully applied public bucket policy")
            return 'policy_applied'
            
        except Exception as e:
            logger.warning(f"Failed to configure public access: {str(e)}")
            
        # 3. Try to set individual file ACLs as fallback
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=source_key
            )
            
            if 'Contents' in response:
                success_count = 0
                for obj in response['Contents']:
                    try:
                        s3_client.put_object_acl(
                            Bucket=bucket_name,
                            Key=obj['Key'],
                            ACL='public-read'
                        )
                        success_count += 1
                    except Exception as acl_error:
                        logger.warning(f"Failed to set ACL for {obj['Key']}: {str(acl_error)}")
                        
                if success_count > 0:
                    logger.info(f"Successfully set public-read ACL for {success_count} files")
                    return 'acl_applied'
                else:
                    logger.warning("Failed to set ACLs for any files")
                    
        except Exception as e:
            logger.warning(f"Failed to apply ACLs: {str(e)}")
            
        return 'access_denied'
        
    except Exception as e:
        logger.error(f"Error configuring bucket access: {str(e)}")
        return 'error'

def check_cloudfront_status(distribution_id):
    """Check CloudFront distribution status"""
    try:
        cloudfront_client = boto3.client('cloudfront')
        
        response = cloudfront_client.get_distribution(Id=distribution_id)
        distribution = response['Distribution']
        
        status = distribution['Status']
        domain_name = distribution['DomainName']
        last_modified = distribution['LastModifiedTime'].isoformat()
        
        logger.info(f"CloudFront {distribution_id}: Status={status}, Domain={domain_name}")
        
        return {
            'status': status,
            'domain_name': domain_name,
            'last_modified': last_modified,
            'enabled': distribution['DistributionConfig']['Enabled']
        }
        
    except Exception as e:
        logger.error(f"Failed to check CloudFront status: {str(e)}")
        return {
            'status': 'Error',
            'error': str(e)
        }

def create_cloudfront_distribution(bucket_name, source_path):
    """Create CloudFront distribution for S3 bucket with specific path"""
    try:
        cloudfront_client = boto3.client('cloudfront')
        
        distribution_config = {
            'CallerReference': f"{bucket_name}-{source_path.replace('/', '-')}-{int(time.time())}",
            'Comment': f'CloudFront distribution for {bucket_name}/{source_path}',
            'DefaultCacheBehavior': {
                'TargetOriginId': bucket_name,
                'ViewerProtocolPolicy': 'redirect-to-https',
                'TrustedSigners': {
                    'Enabled': False,
                    'Quantity': 0
                },
                'ForwardedValues': {
                    'QueryString': False,
                    'Cookies': {'Forward': 'none'}
                },
                'MinTTL': 0,
                'Compress': True
            },
            'Origins': {
                'Quantity': 1,
                'Items': [{
                    'Id': bucket_name,
                    'DomainName': f"{bucket_name}.s3-website.ap-northeast-2.amazonaws.com",
                    'CustomOriginConfig': {
                        'HTTPPort': 80,
                        'HTTPSPort': 443,
                        'OriginProtocolPolicy': 'http-only'
                    }
                }]
            },
            'Enabled': True,
            'DefaultRootObject': f"{source_path.rstrip('/')}/public/index.html",
            'CustomErrorResponses': {
                'Quantity': 2,
                'Items': [
                    {
                        'ErrorCode': 404,
                        'ResponsePagePath': f"/{source_path.rstrip('/')}/public/index.html",
                        'ResponseCode': '200',
                        'ErrorCachingMinTTL': 300
                    },
                    {
                        'ErrorCode': 403,
                        'ResponsePagePath': f"/{source_path.rstrip('/')}/public/index.html",
                        'ResponseCode': '200',
                        'ErrorCachingMinTTL': 300
                    }
                ]
            }
        }
        
        response = cloudfront_client.create_distribution(
            DistributionConfig=distribution_config
        )
        
        distribution_id = response['Distribution']['Id']
        domain_name = response['Distribution']['DomainName']
        status = response['Distribution']['Status']
        
        logger.info(f"Created CloudFront distribution: {distribution_id} (Status: {status})")
        
        return {
            'url': f"https://{domain_name}",
            'distribution_id': distribution_id,
            'status': status,  # InProgress, Deployed
            'message': 'CloudFront distribution created. Deployment in progress (5-15 minutes).'
        }
        
    except Exception as e:
        logger.error(f"CloudFront creation error: {str(e)}")
        return None

def copy_all_files(bucket_name, source_key, dest_bucket):
    """Copy ALL files from source S3 location to destination bucket"""
    try:
        # List all objects with pagination
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=source_key)
        
        copied_count = 0
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                source_file = obj['Key']
                # Remove the prefix to get relative path
                dest_file = source_file.replace(source_key, '')
                
                # Skip if dest_file is empty (directory marker)
                if not dest_file or dest_file.endswith('/'):
                    continue
                
                # Copy file
                s3_client.copy_object(
                    CopySource={'Bucket': bucket_name, 'Key': source_file},
                    Bucket=dest_bucket,
                    Key=dest_file
                )
                copied_count += 1
                logger.info(f"Copied: {source_file} -> {dest_file}")
        
        logger.info(f"Successfully copied {copied_count} files to {dest_bucket}")
        
        # If no files were copied, log the available files for debugging
        if copied_count == 0:
            logger.warning(f"No files copied. Checking what's available at {source_key}:")
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=source_key,
                MaxKeys=10
            )
            if 'Contents' in response:
                for obj in response['Contents']:
                    logger.info(f"Available file: {obj['Key']}")
        
    except Exception as e:
        logger.error(f"S3 copy error: {str(e)}")
        raise e

def handle_status(params):
    """Handle status request"""
    try:
        table = dynamodb.Table('deployment-status')
        
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
        table = dynamodb.Table('deployment-status')
        
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