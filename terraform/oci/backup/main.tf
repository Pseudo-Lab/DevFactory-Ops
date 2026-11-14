terraform {
  required_version = ">= 1.14.4"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "9.9.0"
    }
  }
  backend "oci" {
    bucket    = "terraform-state-prod"
    key       = "backup/terraform.tfstate"
    region    = "ap-chuncheon-1"
    namespace = "axnda59strvy"
  }
}

provider "oci" {
  region              = "ap-chuncheon-1"
  config_file_profile = "DEFAULT"
}

variable "tenancy_ocid" { type = string }
variable "compartment_ocid" { type = string }
variable "instance_ocid" { type = string }

resource "oci_objectstorage_bucket" "backup" {
  compartment_id = var.compartment_ocid
  namespace      = "axnda59strvy"
  name           = "devfactory-cluster-backups"
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  versioning     = "Disabled"
  lifecycle { prevent_destroy = true }
}

resource "oci_identity_dynamic_group" "backup" {
  compartment_id = var.tenancy_ocid
  name           = "devfactory-cluster-backup"
  description    = "Only the production k3s instance can run cluster backups"
  matching_rule  = "ALL {instance.id = '${var.instance_ocid}'}"
}

resource "oci_identity_policy" "backup" {
  compartment_id = var.compartment_ocid
  name           = "devfactory-cluster-backup"
  description    = "Read private bucket settings and create/read/delete backup objects; no overwrite or bucket administration"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.backup.name} to read buckets in compartment id ${var.compartment_ocid} where target.bucket.name = '${oci_objectstorage_bucket.backup.name}'",
    "Allow dynamic-group ${oci_identity_dynamic_group.backup.name} to manage objects in compartment id ${var.compartment_ocid} where all {target.bucket.name = '${oci_objectstorage_bucket.backup.name}', any {request.permission = 'OBJECT_INSPECT', request.permission = 'OBJECT_READ', request.permission = 'OBJECT_CREATE', request.permission = 'OBJECT_DELETE'}}"
  ]
}
