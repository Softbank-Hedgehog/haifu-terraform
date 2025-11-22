# Reference existing Secrets Manager Secret
data "aws_secretsmanager_secret" "haifu_server" {
  name = "haifu-server-main"
}