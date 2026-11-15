# Existing NLB/NSG state was migrated to this key on 2026-10-11.
# Use this backend; do not apply with an empty or old local state.
terraform {
  backend "oci" {
    bucket    = "terraform-state-prod"
    key       = "nlb/terraform.tfstate"
    region    = "ap-chuncheon-1"
    namespace = "axnda59strvy"
  }
}
