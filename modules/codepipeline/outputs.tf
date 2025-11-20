output "pipeline_id" {
  description = "CodePipeline ID"
  value       = aws_codepipeline.main.id
}

output "pipeline_arn" {
  description = "CodePipeline ARN"
  value       = aws_codepipeline.main.arn
}

output "codebuild_project_name" {
  description = "CodeBuild project name"
  value       = aws_codebuild_project.main.name
}

output "codebuild_project_arn" {
  description = "CodeBuild project ARN"
  value       = aws_codebuild_project.main.arn
}