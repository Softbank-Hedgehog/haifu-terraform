# CloudFront distribution for user static site
resource "aws_cloudfront_distribution" "user_site" {
  origin {
    domain_name = aws_s3_bucket_website_configuration.user_site.website_endpoint
    origin_id   = "S3-${aws_s3_bucket.user_site.bucket}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  aliases = var.custom_domain != "" ? [var.custom_domain] : []

  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.user_site.bucket}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  # SPA routing support
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = var.custom_domain == ""
    # For custom domain, you would need to add ACM certificate
    # acm_certificate_arn = var.custom_domain != "" ? var.certificate_arn : null
    # ssl_support_method  = var.custom_domain != "" ? "sni-only" : null
  }

  tags = merge(var.tags, {
    Type = "UserStaticSite"
    UserId = var.user_id
    Project = var.project_name
  })
}