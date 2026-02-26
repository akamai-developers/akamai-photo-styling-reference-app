variable "linode_token" {
  description = "Linode API token"
  type        = string
  sensitive   = true
}

variable "cluster_label" {
  description = "Label for the LKE cluster"
  type        = string
  default     = "photo-styling"
}

variable "k8s_version" {
  description = "Kubernetes version for the LKE cluster"
  type        = string
  default     = "1.34"
}

variable "region" {
  description = "Linode region for the cluster"
  type        = string
  default     = "us-sea"
}

variable "vlm_node_type" {
  description = "Linode instance type for VLM GPU node (1x RTX 4000 Ada)"
  type        = string
  default     = "g2-gpu-rtx4000a1-m"
}

variable "imagegen_node_type" {
  description = "Linode instance type for Image Generator GPU node (2x RTX 4000 Ada)"
  type        = string
  default     = "g2-gpu-rtx4000a2-m"
}

variable "app_node_type" {
  description = "Linode instance type for web app CPU node (Linode 4GB shared)"
  type        = string
  default     = "g6-standard-2"
}

variable "tags" {
  description = "Tags to apply to the cluster"
  type        = list(string)
  default     = ["photo-styling"]
}
