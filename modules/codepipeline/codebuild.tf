resource "aws_codebuild_project" "main" {
  name          = "${var.name_prefix}-build"
  description   = "Build project for ${var.name_prefix}"
  service_role  = aws_iam_role.codebuild_role.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = var.compute_type
    image                      = var.build_image
    type                       = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"

    dynamic "environment_variable" {
      for_each = var.environment_variables
      content {
        name  = environment_variable.key
        value = environment_variable.value
      }
    }
  }

  source {
    type = "CODEPIPELINE"
    buildspec = var.buildspec_file != null ? var.buildspec_file : "buildspec.yml"
  }

  tags = var.tags
}