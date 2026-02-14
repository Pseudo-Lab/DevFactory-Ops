resource "oci_core_instance" "prod_instance" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_id
  display_name        = "soo-server"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    memory_in_gbs = 24
    ocpus         = 4
  }

  source_details {
    source_id   = var.boot_image_id # Fixed image ID to prevent accidental replacement
    source_type = "image"
  }

  create_vnic_details {
    subnet_id      = oci_core_subnet.prod_subnet.id
    display_name   = "soo-server"
    hostname_label = "soo-server"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data = base64encode(templatefile("${path.module}/../scripts/install-k3s.sh", {
      k3s_version = var.k3s_version
    }))
  }

  lifecycle {
    prevent_destroy = true

    # Ignore changes to these attributes to prevent unnecessary replacements
    ignore_changes = [
      metadata,
      extended_metadata,
      freeform_tags,
      defined_tags
    ]
  }

  preserve_boot_volume = true
}
