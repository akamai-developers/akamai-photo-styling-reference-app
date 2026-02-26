output "cluster_id" {
  description = "ID of the LKE cluster"
  value       = linode_lke_cluster.photo_styling.id
}

output "cluster_status" {
  description = "Status of the LKE cluster"
  value       = linode_lke_cluster.photo_styling.status
}

output "kubeconfig" {
  description = "Base64-encoded kubeconfig for the LKE cluster"
  value       = linode_lke_cluster.photo_styling.kubeconfig
  sensitive   = true
}

output "api_endpoints" {
  description = "Kubernetes API server endpoints"
  value       = linode_lke_cluster.photo_styling.api_endpoints
}

output "pool_ids" {
  description = "IDs of the node pools"
  value       = linode_lke_cluster.photo_styling.pool[*].id
}

output "deployment_instructions" {
  description = "Instructions for deploying the application"
  value       = <<-EOT

  ===== LKE CLUSTER READY =====

  Cluster: ${var.cluster_label}
  Region:  ${var.region}

  Next steps:

  1. Save kubeconfig:
     terraform output -raw kubeconfig | base64 -d > kubeconfig.yaml
     export KUBECONFIG=$(pwd)/kubeconfig.yaml

  2. Verify cluster:
     kubectl get nodes

  3. Set environment variables and deploy:
     export DOCKERHUB_USER=your-dockerhub-username
     export HF_TOKEN=hf_your_token_here
     ./k8s/deploy.sh

  4. Get external IP:
     kubectl get svc app-service -n photo-styling

  5. Access at: http://<external-ip>

  =============================
  EOT
}
