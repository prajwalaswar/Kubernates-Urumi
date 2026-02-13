# Helm Charts - Store Provisioning Platform

## Overview

This directory contains Helm charts for deploying the Store Provisioning Platform to Kubernetes.

## Structure

```
helm-charts/
└── platform/
    ├── Chart.yaml              # Chart metadata
    ├── values-local.yaml       # Local (Kind) configuration
    ├── values-prod.yaml        # Production (k3s/VPS) configuration
    └── templates/              # Kubernetes manifest templates
        ├── backend-deployment.yaml
        ├── backend-service.yaml
        ├── dashboard-deployment.yaml
        ├── dashboard-service.yaml
        └── ingress.yaml
```

## Prerequisites

### For Local Deployment (Kind):
- Docker Desktop installed
- Kind cluster running
- kubectl configured
- Helm 3.x installed
- Images built locally

### For Production Deployment (k3s):
- k3s cluster running on VPS
- kubectl configured for remote cluster
- Helm 3.x installed
- Docker registry with images pushed
- DNS configured

## Local Deployment (Kind Cluster)

### Step 1: Build Docker Images

```powershell
# Build backend image
cd backend
docker build -t store-platform-backend:latest .

# Build dashboard image
cd ../dashboard
docker build -t store-platform-dashboard:latest .

# Load images into Kind cluster
kind load docker-image store-platform-backend:latest --name woocommerce-saas
kind load docker-image store-platform-dashboard:latest --name woocommerce-saas
```

### Step 2: Deploy with Helm

```powershell
# From project root
helm install platform ./helm-charts/platform -f ./helm-charts/platform/values-local.yaml

# Verify deployment
kubectl get pods
kubectl get svc
kubectl get ingress
```

### Step 3: Access the Platform

**Option 1: Port-forward**
```powershell
kubectl port-forward svc/platform-dashboard 3000:80
kubectl port-forward svc/platform-backend 8000:8000
```

**Option 2: Via Ingress**
```powershell
# Add to hosts file: C:\Windows\System32\drivers\etc\hosts
127.0.0.1 platform.localhost

# Port-forward ingress
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8888:80

# Access: http://platform.localhost:8888
```

### Step 4: Upgrade Deployment

```powershell
# After code changes, rebuild images and upgrade
helm upgrade platform ./helm-charts/platform -f ./helm-charts/platform/values-local.yaml
```

### Step 5: Uninstall

```powershell
helm uninstall platform
```

## Production Deployment (k3s on VPS)

### Step 1: Prepare Docker Images

```bash
# Tag images for registry
docker tag store-platform-backend:latest your-registry.com/store-platform-backend:v1.0.0
docker tag store-platform-dashboard:latest your-registry.com/store-platform-dashboard:v1.0.0

# Push to registry
docker push your-registry.com/store-platform-backend:v1.0.0
docker push your-registry.com/store-platform-dashboard:v1.0.0
```

### Step 2: Update values-prod.yaml

Edit `values-prod.yaml`:
- Update `image.repository` with your registry URL
- Update `ingress.hosts[0].host` with your domain
- Configure TLS settings

### Step 3: Deploy to k3s

```bash
# Connect to your VPS
ssh user@your-vps-ip

# Deploy with Helm
helm install platform ./helm-charts/platform -f ./helm-charts/platform/values-prod.yaml

# Verify
kubectl get pods -o wide
kubectl get svc
kubectl get ingress
```

### Step 4: Configure DNS

Point your domain to VPS IP:
```
A record: platform.yourdomain.com → YOUR_VPS_IP
```

### Step 5: Setup TLS (Optional but Recommended)

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

## Differences: Local vs Production

| Aspect | Local (values-local.yaml) | Production (values-prod.yaml) |
|--------|---------------------------|-------------------------------|
| **Replicas** | 1 | 2 (HA) |
| **Image Pull Policy** | Never (local build) | Always (from registry) |
| **Image Repository** | local names | registry.com/images |
| **Ingress Host** | platform.localhost | platform.yourdomain.com |
| **TLS** | Disabled | Enabled with Let's Encrypt |
| **Resources** | Lower limits | Higher limits |
| **Storage Class** | standard (local-path) | Production storage class |

## Customization

### Scaling

```powershell
# Scale backend
helm upgrade platform ./helm-charts/platform \
  --set backend.replicas=3 \
  -f ./helm-charts/platform/values-local.yaml

# Scale dashboard
helm upgrade platform ./helm-charts/platform \
  --set dashboard.replicas=3 \
  -f ./helm-charts/platform/values-local.yaml
```

### Resource Limits

Edit values file:
```yaml
backend:
  resources:
    requests:
      memory: "512Mi"
      cpu: "500m"
    limits:
      memory: "1Gi"
      cpu: "1000m"
```

## Troubleshooting

### Check Pod Status
```powershell
kubectl get pods
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### Check Ingress
```powershell
kubectl get ingress
kubectl describe ingress platform-ingress
```

### Test Services
```powershell
# Test backend health
kubectl port-forward svc/platform-backend 8000:8000
curl http://localhost:8000/health

# Test dashboard
kubectl port-forward svc/platform-dashboard 3000:80
curl http://localhost:3000
```

### Common Issues

**Images not found:**
- Local: Run `kind load docker-image` again
- Production: Verify images are pushed to registry

**Ingress not working:**
- Verify ingress controller is running
- Check ingress class name matches

**Pods crashing:**
- Check logs: `kubectl logs <pod-name>`
- Verify resource limits are sufficient
- Check environment variables

## Rollback

```powershell
# List releases
helm history platform

# Rollback to previous version
helm rollback platform

# Rollback to specific version
helm rollback platform <revision-number>
```

## Monitoring

```powershell
# Watch pod status
kubectl get pods -w

# View logs
kubectl logs -f deployment/platform-backend
kubectl logs -f deployment/platform-dashboard

# Check resource usage
kubectl top pods
```
