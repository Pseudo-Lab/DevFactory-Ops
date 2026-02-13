# __generated__ by Terraform
# Please review these resources and move them into your main configuration files.

# __generated__ by Terraform from "ocid1.vcn.oc1.ap-chuncheon-1.amaaaaaa7rlw6kaam6u523nqzl4l4urgflqnccy4hemezdeshfyn5zfggbla"
resource "oci_core_vcn" "prod_vcn" {
  cidr_block              = "10.0.0.0/16"
  cidr_blocks             = ["10.0.0.0/16"]
  compartment_id          = "ocid1.compartment.oc1..aaaaaaaa5homz3zv47kbptbom4zuhieqwrb3xqujpze52bjo7ufabwuvrx4a"
  defined_tags            = {}
  display_name            = "vcn-20241028-0116"
  dns_label               = "vcn10280116"
  freeform_tags           = {}
  ipv6private_cidr_blocks = []
  is_ipv6enabled          = false
  security_attributes     = {}
}

# __generated__ by Terraform from "ocid1.subnet.oc1.ap-chuncheon-1.aaaaaaaazrjpegygezejzytqi2z6kd5reacfsrtn3klsvluleqr53kqhzrqa"
resource "oci_core_subnet" "prod_subnet" {
  cidr_block                 = "10.0.0.0/24"
  compartment_id             = "ocid1.compartment.oc1..aaaaaaaa5homz3zv47kbptbom4zuhieqwrb3xqujpze52bjo7ufabwuvrx4a"
  defined_tags               = {}
  dhcp_options_id            = "ocid1.dhcpoptions.oc1.ap-chuncheon-1.aaaaaaaay5aemkuotgscbc7saqd5yw4wvhz5436fnowlbd7edwrc2cn7tlra"
  display_name               = "subnet-20241028-0116"
  dns_label                  = "subnet10280116"
  freeform_tags              = {}
  ipv4cidr_blocks            = ["10.0.0.0/24"]
  ipv6cidr_blocks            = []
  prohibit_internet_ingress  = false
  prohibit_public_ip_on_vnic = false
  route_table_id             = "ocid1.routetable.oc1.ap-chuncheon-1.aaaaaaaa6cdbswnfi7magv2sxt2htu2s7g5dca2xhfqfm2itpjpca2zw7mbq"
  security_list_ids          = ["ocid1.securitylist.oc1.ap-chuncheon-1.aaaaaaaaqth4u5te5qxw7rqfr7g7tcxw2gjacvhovdi656jzyxwdocxjtxpa"]
  vcn_id                     = "ocid1.vcn.oc1.ap-chuncheon-1.amaaaaaa7rlw6kaam6u523nqzl4l4urgflqnccy4hemezdeshfyn5zfggbla"
}

# __generated__ by Terraform from "ocid1.instance.oc1.ap-chuncheon-1.an4w4ljr7rlw6kacaz47ncs6ci7m7a7umwbt5fmh6t3ntxxiatzxadxoh6jq"
resource "oci_core_instance" "prod_instance" {
  async                      = null
  availability_domain        = "nHgk:AP-CHUNCHEON-1-AD-1"
  cluster_placement_group_id = null
  compartment_id             = "ocid1.compartment.oc1..aaaaaaaa5homz3zv47kbptbom4zuhieqwrb3xqujpze52bjo7ufabwuvrx4a"
  defined_tags               = {}
  display_name               = "soo-server"
  extended_metadata          = {}
  fault_domain               = "FAULT-DOMAIN-2"
  freeform_tags              = {}
  metadata = {
    ssh_authorized_keys = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwamtkp2xazR4mWOGb6966OhO8r+pDKM5lW8AFY2oxPNtN2EoD3ZVS9dPFHUKIRJbPHcF0H3usY+vHoMiZL4oUS55W315GozOn0YZ4I+MP076ZPaj/Rq8JAAsTQewN9frlmTyZjNQZXqipQB7KkAELM/GdF+IZY4xRug2i+hwA7D+lvkIfOTVmw08b2OhxSHwM7sIoi/ZrQjAmnNKyW/cDdlKqi2G+Mhcsdap5RGa4qz+5+JPtaSxEOCF6v2Do+8BJFiAtSjGF0hLlSfl+pi2OWtgm2jHOzFXuzr/eWFXPpqSP/ZBU8sCh9+AYHsL8CJfxA3SQW+XBcydJNsEvWuo1 ssh-key-2024-11-02"
  }
  preserve_boot_volume                    = null
  preserve_data_volumes_created_at_launch = null
  security_attributes                     = {}
  shape                                   = "VM.Standard.A1.Flex"
  state                                   = "RUNNING"
  update_operation_constraint             = null
  agent_config {
    are_all_plugins_disabled = false
    is_management_disabled   = false
    is_monitoring_disabled   = false
    plugins_config {
      desired_state = "DISABLED"
      name          = "Vulnerability Scanning"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Oracle Java Management Service"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Oracle Autonomous Linux"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "OS Management Service Agent"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "OS Management Hub Agent"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Management Agent"
    }
    plugins_config {
      desired_state = "ENABLED"
      name          = "Custom Logs Monitoring"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Compute RDMA GPU Monitoring"
    }
    plugins_config {
      desired_state = "ENABLED"
      name          = "Compute Instance Run Command"
    }
    plugins_config {
      desired_state = "ENABLED"
      name          = "Compute Instance Monitoring"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Compute HPC RDMA Auto-Configuration"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Compute HPC RDMA Authentication"
    }
    plugins_config {
      desired_state = "ENABLED"
      name          = "Cloud Guard Workload Protection"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Block Volume Management"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Bastion"
    }
  }
  availability_config {
    is_live_migration_preferred = false
    recovery_action             = "RESTORE_INSTANCE"
  }
  create_vnic_details {
    assign_ipv6ip             = false
    assign_private_dns_record = false
    assign_public_ip          = "true"
    defined_tags              = {}
    display_name              = "soo-server"
    freeform_tags             = {}
    hostname_label            = "soo-server"
    nsg_ids                   = []
    private_ip                = "10.0.0.158"
    security_attributes       = {}
    skip_source_dest_check    = false
    subnet_id                 = "ocid1.subnet.oc1.ap-chuncheon-1.aaaaaaaazrjpegygezejzytqi2z6kd5reacfsrtn3klsvluleqr53kqhzrqa"
  }
  instance_options {
    are_legacy_imds_endpoints_disabled = false
  }
  launch_options {
    boot_volume_type                    = "PARAVIRTUALIZED"
    firmware                            = "UEFI_64"
    is_consistent_volume_naming_enabled = true
    is_pv_encryption_in_transit_enabled = true
    network_type                        = "PARAVIRTUALIZED"
    remote_data_volume_type             = "PARAVIRTUALIZED"
  }
  shape_config {
    memory_in_gbs = 24
    nvmes         = 0
    ocpus         = 4
    vcpus         = 4
  }
  source_details {
    boot_volume_size_in_gbs         = "200"
    boot_volume_vpus_per_gb         = "10"
    is_preserve_boot_volume_enabled = false
    kms_key_id                      = null
    source_id                       = "ocid1.image.oc1.ap-chuncheon-1.aaaaaaaatt7p3d4qxx5y4g43mkqd6eljvq7d44ja7kdgpo2phwnche75ukgq"
    source_type                     = "image"
  }
}
