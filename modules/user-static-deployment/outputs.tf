output "s3_bucket_name" {
  description = "S3 bucket name for the static site"
  value       = aws_s3_bucket.user_site.bucket
}

output "s3_website_endpoint" {
  description = "S3 website endpoint"
  value       = aws_s3_bucket_website_configuration.user_site.website_endpoint
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.user_site.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.user_site.id
}

output "website_url" {
  description = "Website URL (CloudFront or custom domain)"
  value       = var.custom_domain != "" ? "https://${var.custom_domain}" : "https://${aws_cloudfront_distribution.user_site.domain_name}"
}

output "codepipeline_name" {
  description = "CodePipeline name"
  value       = aws_codepipeline.user_site.name
}

output "codebuild_project_name" {
  description = "CodeBuild project name"
  value       = aws_codebuild_project.user_site.name
}