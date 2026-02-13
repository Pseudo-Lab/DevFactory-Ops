# #############################################################################
# [Backend 설정]
# OCI Object Storage를 S3 호환 모드로 사용하여 Terraform State를 저장합니다.
# 1. OCI 콘솔에서 'terraform-state-prod' 버킷 생성
# 2. Customer Secret Key 생성 후 Access/Secret Key 확보
# #############################################################################

# terraform {
#   backend "s3" {
#     bucket   = "terraform-state-prod"
#     key      = "prod/terraform.tfstate"
#     region   = "ap-chuncheon-1"
#     endpoint = "https://[namespace].compat.objectstorage.ap-chuncheon-1.oraclecloud.com"
#     
#     skip_region_validation      = true
#     skip_credentials_validation = true
#     skip_metadata_api_check     = true
#     force_path_style            = true
#   }
# }
