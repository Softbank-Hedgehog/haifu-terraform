# S3 bucket for user static site
resource "aws_s3_bucket" "user_site" {
  bucket = "haifu-user-${var.user_id}-${var.project_name}"
  
  tags = merge(var.tags, {
    Type = "UserStaticSite"
    UserId = var.user_id
    Project = var.project_name
  })
}

resource "aws_s3_bucket_versioning" "user_site" {
  bucket = aws_s3_bucket.user_site.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_website_configuration" "user_site" {
  bucket = aws_s3_bucket.user_site.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

resource "aws_s3_bucket_public_access_block" "user_site" {
  bucket = aws_s3_bucket.user_site.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "user_site" {
  bucket = aws_s3_bucket.user_site.id
  depends_on = [aws_s3_bucket_public_access_block.user_site]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.user_site.arn}/*"
      }
    ]
  })
}