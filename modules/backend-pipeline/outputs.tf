output "pipeline_name" {
  description = "CodePipeline name"
  value       = aws_codepipeline.backend.name
}

output "codebuild_project_name" {
  description = "CodeBuild project name"
  value       = aws_codebuild_project.backend.name
}