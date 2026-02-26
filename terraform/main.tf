# Terraform configuration for Photo Styling App on LKE
# Creates a single LKE cluster with GPU and CPU node pools
# for running VLM, Image Generator, and FastAPI app as Deployments

terraform {
  required_version = ">= 1.0"

  required_providers {
    linode = {
      source  = "linode/linode"
      version = "~> 2.0"
    }
  }
}

provider "linode" {
  token = var.linode_token
}

# LKE Kubernetes Cluster
resource "linode_lke_cluster" "photo_styling" {
  label       = var.cluster_label
  k8s_version = var.k8s_version
  region      = var.region
  tags        = var.tags

  # GPU node pool for VLM (1x RTX 4000 Ada)
  pool {
    type  = var.vlm_node_type
    count = 1

    autoscaler {
      min = 1
      max = 1
    }
  }

  # GPU node pool for Image Generator (2x RTX 4000 Ada)
  pool {
    type  = var.imagegen_node_type
    count = 1

    autoscaler {
      min = 1
      max = 1
    }
  }

  # CPU node pool for the web app
  pool {
    type  = var.app_node_type
    count = 2

    autoscaler {
      min = 2
      max = 3
    }
  }
}
