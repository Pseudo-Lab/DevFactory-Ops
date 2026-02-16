resource "oci_load_balancer" "prod_lb" {
  compartment_id = var.compartment_id
  display_name   = "devfactory-prod-lb"
  shape          = "flexible"
  subnet_ids     = [oci_core_subnet.prod_subnet.id]
  is_private     = false

  shape_details {
    minimum_bandwidth_in_mbps = 10
    maximum_bandwidth_in_mbps = 10
  }
}

# --- HTTP (80) ---

resource "oci_load_balancer_backend_set" "prod_lb_bs" {
  name             = "prod-lb-bs"
  load_balancer_id = oci_load_balancer.prod_lb.id
  policy           = "ROUND_ROBIN"

  health_checker {
    protocol          = "HTTP"
    port              = 30080
    url_path          = "/healthz"
    interval_ms       = 10000
    timeout_in_millis = 3000
    retries           = 3
    return_code       = 200
  }
}

resource "oci_load_balancer_listener" "prod_lb_listener" {
  load_balancer_id         = oci_load_balancer.prod_lb.id
  name                     = "http"
  default_backend_set_name = oci_load_balancer_backend_set.prod_lb_bs.name
  port                     = 80
  protocol                 = "HTTP"
}

resource "oci_load_balancer_backend" "prod_lb_backend" {
  load_balancer_id = oci_load_balancer.prod_lb.id
  backendset_name  = oci_load_balancer_backend_set.prod_lb_bs.name
  ip_address       = oci_core_instance.prod_instance.private_ip
  port             = 30080
  backup           = false
  drain            = false
  offline          = false
  weight           = 1
}

# --- HTTPS (443 - TCP Passthrough) ---

resource "oci_load_balancer_backend_set" "prod_lb_bs_https" {
  name             = "prod-lb-bs-https"
  load_balancer_id = oci_load_balancer.prod_lb.id
  policy           = "ROUND_ROBIN"

  health_checker {
    protocol          = "TCP"
    port              = 30443 # Health check on 30443 (Server must be listening!)
    interval_ms       = 10000
    timeout_in_millis = 3000
    retries           = 3
  }
}

resource "oci_load_balancer_listener" "prod_lb_listener_https" {
  load_balancer_id         = oci_load_balancer.prod_lb.id
  name                     = "https-tcp"
  default_backend_set_name = oci_load_balancer_backend_set.prod_lb_bs_https.name
  port                     = 443
  protocol                 = "TCP" # Passthrough
}

resource "oci_load_balancer_backend" "prod_lb_backend_https" {
  load_balancer_id = oci_load_balancer.prod_lb.id
  backendset_name  = oci_load_balancer_backend_set.prod_lb_bs_https.name
  ip_address       = oci_core_instance.prod_instance.private_ip
  port             = 30443
  backup           = false
  drain            = false
  offline          = false
  weight           = 1
}
