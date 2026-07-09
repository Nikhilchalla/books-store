#!/bin/bash
# Run this on a fresh EC2 instance (Ubuntu 22.04/24.04, t3.medium or larger recommended)
# Usage: bash ec2-setup.sh

set -e

echo "=== Updating packages ==="
sudo apt-get update -y

echo "=== Installing Docker (for building/pushing images) ==="
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"

echo "=== Installing k3s (lightweight Kubernetes) ==="
curl -sfL https://get.k3s.io | sh -

echo "=== Waiting for k3s to be ready ==="
sudo k3s kubectl wait --for=condition=Ready node --all --timeout=120s

echo "=== Setting up kubectl access for your user ==="
mkdir -p "$HOME/.kube"
sudo cp /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
sudo chown "$USER:$USER" "$HOME/.kube/config"
echo 'alias kubectl="k3s kubectl"' >> "$HOME/.bashrc"

echo "=== Done. Log out and back in (for docker group), then verify with: ==="
echo "    k3s kubectl get nodes"
echo ""
echo "Note: k3s ships with Traefik as its default Ingress controller — already running."
echo "Check it with: k3s kubectl get pods -n kube-system | grep traefik"