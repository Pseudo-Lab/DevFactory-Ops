variable "tenancy_ocid" {
  description = "OCI Tenancy OCID"
  type        = string
}

variable "user_ocid" {
  description = "OCI User OCID"
  type        = string
}

variable "fingerprint" {
  description = "OCI API Key Fingerprint"
  type        = string
}

variable "private_key_path" {
  description = "Path to the OCI API Private Key"
  type        = string
}

variable "region" {
  description = "OCI Region"
  type        = string
  default     = "ap-chuncheon-1"
}

variable "compartment_id" {
  description = "OCI Compartment OCID"
  type        = string
}

variable "ssh_public_key" {
  description = "SSH Public Key for instances"
  type        = string
}

variable "boot_image_id" {
  description = "Fixed Boot Image OCID - DO NOT CHANGE without full backup"
  type        = string
  default     = "ocid1.image.oc1.ap-chuncheon-1.aaaaaaaav7cuhv3ncaub55ecxjp6zgo6eevb7w32mv5tq34pfadhulgydf5q"

  validation {
    condition     = can(regex("^ocid1\\.image\\.", var.boot_image_id))
    error_message = "boot_image_id must be a valid OCI image OCID starting with 'ocid1.image.'"
  }
}

variable "home_ip_cidr" {
  description = "CIDR block for Home/Office IP (Allowed access to certain services)"
  type        = string
}

variable "k3s_api_ip_cidr" {
  description = "CIDR block for K3s API Server (Antigravity Remote)"
  type        = string
}
