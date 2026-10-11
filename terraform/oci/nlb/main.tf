terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "9.9.0"
    }
  }
}

provider "oci" {
  region              = "ap-chuncheon-1"
  config_file_profile = "DEFAULT"
}

resource "oci_network_load_balancer_network_load_balancer" "validation" {
  compartment_id                 = "ocid1.compartment.oc1..aaaaaaaa5homz3zv47kbptbom4zuhieqwrb3xqujpze52bjo7ufabwuvrx4a"
  display_name                   = "devfactory-nlb-validation-20261009"
  subnet_id                      = "ocid1.subnet.oc1.ap-chuncheon-1.aaaaaaaazrjpegygezejzytqi2z6kd5reacfsrtn3klsvluleqr53kqhzrqa"
  is_private                     = false
  is_preserve_source_destination = false
  freeform_tags = {
    purpose = "devday-isolated-nlb-validation"
  }
}

resource "oci_network_load_balancer_backend_set" "validation" {
  for_each = {
    http  = 31080
    https = 31443
  }
  name                     = each.key
  network_load_balancer_id = oci_network_load_balancer_network_load_balancer.validation.id
  policy                   = "FIVE_TUPLE"
  is_preserve_source       = false
  is_fail_open             = false

  health_checker {
    protocol           = "HTTP"
    port               = 31081
    url_path           = "/healthz"
    return_code        = 200
    interval_in_millis = 10000
    timeout_in_millis  = 3000
    retries            = 3
  }
}

resource "oci_network_load_balancer_backend" "validation" {
  for_each                 = oci_network_load_balancer_backend_set.validation
  network_load_balancer_id = oci_network_load_balancer_network_load_balancer.validation.id
  backend_set_name         = each.value.name
  ip_address               = "10.0.0.158"
  port                     = each.key == "http" ? 31080 : 31443
  weight                   = 1
}

resource "oci_network_load_balancer_listener" "validation" {
  for_each = {
    http  = 80
    https = 443
  }
  name                     = each.key
  network_load_balancer_id = oci_network_load_balancer_network_load_balancer.validation.id
  default_backend_set_name = oci_network_load_balancer_backend_set.validation[each.key].name
  port                     = each.value
  protocol                 = "TCP"
  tcp_idle_timeout         = 360
  is_ppv2enabled           = true
}

output "nlb_id" {
  value = oci_network_load_balancer_network_load_balancer.validation.id
}

output "nlb_addresses" {
  value = oci_network_load_balancer_network_load_balancer.validation.ip_addresses
}

# Existing VM attachment is recorded separately; preserve it during state migration.
# Only the NLB private IP may reach the data and health NodePorts.
resource "oci_core_network_security_group" "validation" {
  compartment_id = "ocid1.compartment.oc1..aaaaaaaa5homz3zv47kbptbom4zuhieqwrb3xqujpze52bjo7ufabwuvrx4a"
  vcn_id         = "ocid1.vcn.oc1.ap-chuncheon-1.amaaaaaa7rlw6kaam6u523nqzl4l4urgflqnccy4hemezdeshfyn5zfggbla"
  display_name   = "devday-nlb-validation-nodeports-20261009"
}

resource "oci_core_network_security_group_security_rule" "validation" {
  for_each = {
    health_http  = { source = "10.0.0.184/32", port = 31080 }
    health_https = { source = "10.0.0.184/32", port = 31443 }
    health_check = { source = "10.0.0.184/32", port = 31081 }
  }
  network_security_group_id = oci_core_network_security_group.validation.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source_type               = "CIDR_BLOCK"
  source                    = each.value.source
  stateless                 = false
  description               = "Isolated NLB validation: ${each.key}"
  tcp_options {
    destination_port_range {
      min = each.value.port
      max = each.value.port
    }
  }
}

output "validation_nsg_id" {
  value = oci_core_network_security_group.validation.id
}
