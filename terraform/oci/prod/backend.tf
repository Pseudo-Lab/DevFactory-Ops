# #############################################################################
# [Backend 설정]
# OCI Object Storage를 S3 호환 모드로 사용하여 Terraform State를 저장합니다.
# 1. OCI 콘솔에서 'terraform-state-prod' 버킷 생성
# 2. Customer Secret Key 생성 후 Access/Secret Key 확보
# #############################################################################

terraform {
  backend "oci" {
    bucket    = "terraform-state-prod"
    key       = "prod/terraform.tfstate"
    region    = "ap-chuncheon-1"
    namespace = "axnda59strvy"

    # Credentials (Backend blocks cannot use variables, so these must be literal or from env)
    # Alternatively, you can run: 
    # terraform init -backend-config="tenancy_ocid=..." -backend-config="user_ocid=..." ...
    # But let's see if it can pick up from terraform.tfvars or env.
    # Actually, let's use the 'oci' backend which supports OCI CLI config or env vars.
  }
}
