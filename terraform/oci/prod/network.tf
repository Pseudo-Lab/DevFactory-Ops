resource "oci_core_vcn" "prod_vcn" {
  cidr_block     = "10.0.0.0/16"
  compartment_id = var.compartment_id
  display_name   = "vcn-20241028-0116"
  dns_label      = "vcn10280116"
}

resource "oci_core_subnet" "prod_subnet" {
  cidr_block        = "10.0.0.0/24"
  compartment_id    = var.compartment_id
  display_name      = "subnet-20241028-0116"
  dns_label         = "subnet10280116"
  route_table_id    = oci_core_vcn.prod_vcn.default_route_table_id
  security_list_ids = [oci_core_security_list.prod_security_list.id]
  vcn_id            = oci_core_vcn.prod_vcn.id
}
