# S3 bucket for CodePipeline artifacts
resource "aws_s3_bucket" "pipeline_artifacts" {
  bucket = "haifu-user-${var.user_id}-${var.project_name}-artifacts"
  
  tags = merge(var.tags, {
    Type = "PipelineArtifacts"
    UserId = var.user_id
    Project = var.project_name
  })
}

resource "aws_s3_bucket_versioning" "pipeline_artifacts" {
  bucket = aws_s3_bucket.pipeline_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

# IAM role for CodePipeline
resource "aws_iam_role" "codepipeline" {
  name = "haifu-user-${var.user_id}-${var.project_name}-pipeline-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codepipeline.amazonaws.com"
        }
      }
    ]
  })
  
  tags = var.tags
}

resource "aws_iam_role_policy" "codepipeline" {
  name = "haifu-user-${var.user_id}-${var.project_name}-pipeline-policy"
  role = aws_iam_role.codepipeline.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketVersioning",
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject"
        ]
        Resource = [
          aws_s3_bucket.pipeline_artifacts.arn,
          "${aws_s3_bucket.pipeline_artifacts.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "codebuild:BatchGetBuilds",
          "codebuild:StartBuild"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM role for CodeBuild
resource "aws_iam_role" "codebuild" {
  name = "haifu-user-${var.user_id}-${var.project_name}-build-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      }
    ]
  })
  
  tags = var.tags
}

resource "aws_iam_role_policy" "codebuild" {
  name = "haifu-user-${var.user_id}-${var.project_name}-build-policy"
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          aws_s3_bucket.pipeline_artifacts.arn,
          "${aws_s3_bucket.pipeline_artifacts.arn}/*",
          aws_s3_bucket.user_site.arn,
          "${aws_s3_bucket.user_site.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudfront:CreateInvalidation"
        ]
        Resource = "*"
      }
    ]
  })
}

# CodeBuild project
resource "aws_codebuild_project" "user_site" {
  name         = "haifu-user-${var.user_id}-${var.project_name}-build"
  service_role = aws_iam_role.codebuild.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image        = "aws/codebuild/standard:7.0"
    type         = "LINUX_CONTAINER"

    dynamic "environment_variable" {
      for_each = var.environment_variables
      content {
        name  = environment_variable.key
        value = environment_variable.value
      }
    }

    environment_variable {
      name  = "S3_BUCKET"
      value = aws_s3_bucket.user_site.bucket
    }

    environment_variable {
      name  = "CLOUDFRONT_DISTRIBUTION_ID"
      value = aws_cloudfront_distribution.user_site.id
    }
  }

  source {
    type = "CODEPIPELINE"
    buildspec = "version: 0.2\nphases:\n  install:\n    runtime-versions:\n      nodejs: ${var.node_version}\n    commands:\n      - echo Installing dependencies...\n      - npm install\n  build:\n    commands:\n      - echo Building project...\n      - ${var.build_command}\n  post_build:\n    commands:\n      - echo Deploying to S3...\n      - aws s3 sync ${var.build_output_dir}/ s3://$$S3_BUCKET --delete\n      - echo Creating CloudFront invalidation...\n      - aws cloudfront create-invalidation --distribution-id $$CLOUDFRONT_DISTRIBUTION_ID --paths \"/*\"\nartifacts:\n  files:\n    - '**/*'\n  base-directory: ${var.build_output_dir}"
  }
  
  tags = var.tags
}

# CodePipeline (GitHub webhook based)
resource "aws_codepipeline" "user_site" {
  name     = "haifu-user-${var.user_id}-${var.project_name}-pipeline"
  role_arn = aws_iam_role.codepipeline.arn

  artifact_store {
    location = aws_s3_bucket.pipeline_artifacts.bucket
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "ThirdParty"
      provider         = "GitHub"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        Owner      = split("/", replace(var.github_repo_url, "https://github.com/", ""))[0]
        Repo       = split("/", replace(var.github_repo_url, "https://github.com/", ""))[1]
        Branch     = var.github_branch
        OAuthToken = "{{resolve:secretsmanager:github-token:SecretString:token}}"
      }
    }
  }

  stage {
    name = "Build"

    action {
      name             = "Build"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      version          = "1"

      configuration = {
        ProjectName = aws_codebuild_project.user_site.name
      }
    }
  }
  
  tags = var.tags
}