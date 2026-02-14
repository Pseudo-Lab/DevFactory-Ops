data "oci_objectstorage_namespace" "ns" {
  compartment_id = var.tenancy_ocid
}

resource "oci_objectstorage_bucket" "terraform_state" {
  compartment_id = var.tenancy_ocid
  name           = "terraform-state-prod"
  namespace      = data.oci_objectstorage_namespace.ns.namespace
  storage_tier   = "Standard"
  versioning     = "Enabled"
}

output "object_storage_namespace" {
  value = data.oci_objectstorage_namespace.ns.namespace
}
