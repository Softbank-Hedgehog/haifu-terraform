output "pipeline_name" {
  description = "CodePipeline name"
  value       = aws_codepipeline.backend.name
}

output "codebuild_project_name" {
  description = "CodeBuild project name"
  value       = aws_codebuild_project.backend.name
}

output "github_connection_arn" {
  description = "GitHub CodeStar connection ARN"
  value       = aws_codestarconnections_connection.github.arn
}

output "artifacts_bucket_name" {
  description = "S3 artifacts bucket name"
  value       = aws_s3_bucket.artifacts.bucket
}

output "codepipeline_role_arn" {
  description = "CodePipeline service role ARN"
  value       = aws_iam_role.codepipeline.arn
}

output "codebuild_role_arn" {
  description = "CodeBuild service role ARN"
  value       = aws_iam_role.codebuild.arn
}