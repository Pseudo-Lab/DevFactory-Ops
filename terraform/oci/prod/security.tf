
resource "oci_core_security_list" "prod_security_list" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.prod_vcn.id
  display_name   = "security-list-20241028-0116"

  egress_security_rules {
    destination      = "0.0.0.0/0"
    protocol         = "all"
    destination_type = "CIDR_BLOCK"
    stateless        = false
  }

  ingress_security_rules {
    description = "SSH"
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    tcp_options {
      max = 22
      min = 22
    }
  }

  ingress_security_rules {
    description = "HTTP"
    protocol    = "6"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    tcp_options {
      max = 80
      min = 80
    }
  }

  ingress_security_rules {
    description = "HTTPS"
    protocol    = "6"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    tcp_options {
      max = 443
      min = 443
    }
  }

  ingress_security_rules {
    description = "PostgreSQL"
    protocol    = "6"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    tcp_options {
      max = 5432
      min = 5432
    }
  }

  ingress_security_rules {
    description = "빙고 DB, 수현 집"
    protocol    = "6"
    source      = var.home_ip_cidr
    source_type = "CIDR_BLOCK"
    stateless   = false
    tcp_options {
      max = 3306
      min = 3306
    }
  }

  ingress_security_rules {
    description = "k3s API Server (Antigravity Remote)"
    protocol    = "6"
    source      = var.k3s_api_ip_cidr
    source_type = "CIDR_BLOCK"
    stateless   = false
    tcp_options {
      max = 6443
      min = 6443
    }
  }

  ingress_security_rules {
    description = "Nginx Ingress HTTP (NodePort)"
    protocol    = "6"
    source      = "10.0.0.0/24"
    source_type = "CIDR_BLOCK"
    stateless   = false
    tcp_options {
      max = 30080
      min = 30080
    }
  }

  ingress_security_rules {
    description = "Nginx Ingress HTTPS (NodePort)"
    protocol    = "6"
    source      = "10.0.0.0/24"
    source_type = "CIDR_BLOCK"
    stateless   = false
    tcp_options {
      max = 30443
      min = 30443
    }
  }
}
