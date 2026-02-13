# 🏪 Kubernetes Store Provisioning Platform

A production-ready platform for automatically provisioning and managing multiple WooCommerce e-commerce stores on Kubernetes with complete isolation, persistent storage, and automated orchestration.

![Project Status](https://img.shields.io/badge/status-active-success.svg)
![Kubernetes](https://img.shields.io/badge/kubernetes-v1.35-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start (Local)](#quick-start-local)
- [Production Deployment](#production-deployment)
- [How to Create a Store and Place an Order](#how-to-create-a-store-and-place-an-order)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## 🎯 Overview

This platform enables users to provision multiple isolated WooCommerce stores through a web dashboard, with each store running as a fully-functional e-commerce site on Kubernetes. The system handles:

- **Automated provisioning** of WordPress + WooCommerce + MariaDB
- **Namespace isolation** - each store in its own Kubernetes namespace
- **Persistent storage** - databases and file uploads survive pod restarts
- **Ingress routing** - unique URLs for each store
- **Resource management** - configurable CPU/memory limits
- **Clean teardown** - complete resource cleanup on store deletion

**Key Deliverable:** Complete end-to-end order placement flow (browse → cart → checkout → order confirmed)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User's Browser                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              React Dashboard (Port 3000)                │
│  - Create Store Form                                    │
│  - Store List Table                                     │
│  - Delete Store Actions                                 │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP API Calls
                     ▼
┌─────────────────────────────────────────────────────────┐
│            FastAPI Backend (Port 8000)                  │
│  - POST /stores   - Create new store                    │
│  - GET /stores    - List all stores                     │
│  - DELETE /stores/{name} - Delete store                 │
└────────────────────┬────────────────────────────────────┘
                     │ Kubernetes API + Helm CLI
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Kubernetes Cluster (kind/k3s)              │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Namespace: Prajwal-Store                        │    │
│  │  ├── WordPress Pod (WooCommerce)               │    │
│  │  ├── MariaDB StatefulSet                       │    │
│  │  ├── PVCs (WordPress data + MariaDB)           │    │
│  │  ├── Services (ClusterIP)                      │    │
│  │  └── Ingress (alice.localhost)                 │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Namespace: store-bob                          │    │
│  │  ├── WordPress Pod (WooCommerce)               │    │
│  │  ├── MariaDB StatefulSet                       │    │
│  │  └── ... (isolated resources)                  │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Namespace: ingress-nginx                      │    │
│  │  └── nginx-ingress-controller                  │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### Core Features
- ✅ **Web Dashboard** - React-based UI for store management
- ✅ **REST API** - FastAPI backend with Create/Read/Delete operations
- ✅ **Automated Provisioning** - One-click WooCommerce store creation
- ✅ **Namespace Isolation** - Each store in separate Kubernetes namespace
- ✅ **Persistent Storage** - PersistentVolumeClaims for data persistence
- ✅ **Ingress Routing** - HTTP routing to individual stores
- ✅ **Resource Management** - CPU/memory requests and limits
- ✅ **Clean Deletion** - Complete resource cleanup including PVCs

### E-commerce Features
- ✅ **WooCommerce 10.5.0** - Latest version with all features
- ✅ **End-to-end checkout** - Full order placement flow
- ✅ **Payment methods** - Cash on Delivery (COD) enabled
- ✅ **Admin panel** - Full WordPress + WooCommerce admin access
- ✅ **Persistent orders** - Database survives pod restarts

### DevOps Features
- ✅ **Helm-based deployment** - Production-ready packaging
- ✅ **Environment separation** - values-local.yaml vs values-prod.yaml
- ✅ **Secret management** - Auto-generated secure passwords
- ✅ **Health checks** - Readiness/liveness probes
- ✅ **Local development** - Works on kind/k3d/minikube
- ✅ **Production ready** - Deployable to k3s on VPS

---

## 📦 Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Docker Desktop** | Latest | Container runtime + local Kubernetes |
| **kubectl** | 1.28+ | Kubernetes CLI |
| **Helm** | 3.x | Kubernetes package manager |
| **kind** | Latest | Local Kubernetes cluster (or k3d/minikube) |
| **Node.js** | 16+ | Dashboard development |
| **Python** | 3.9+ | Backend development |

### Installation Commands

**Windows (PowerShell):**
```powershell
# Install Chocolatey (if not installed)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install tools
choco install docker-desktop kubectl kubernetes-helm kind nodejs python -y

# Verify installations
docker --version
kubectl version --client
helm version
kind version
node --version
python --version
```

**macOS:**
```bash
brew install docker kubectl kubernetes-helm kind node python3
```

**Linux:**
```bash
# Follow official installation guides for each tool
```

---

## 🚀 Quick Start (Local)

### Step 1: Create Kubernetes Cluster

```powershell
# Create kind cluster with extra port mapping for ingress
kind create cluster --name woocommerce-saas --config kind-config.yaml

# Verify cluster is running
kubectl cluster-info
kubectl get nodes
```

### Step 2: Install Ingress Controller

```powershell
# Install nginx ingress controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx `
  --namespace ingress-nginx `
  --create-namespace `
  --set controller.service.type=NodePort `
  --set controller.service.nodePorts.http=30080 `
  --set controller.service.nodePorts.https=30443

# Wait for ingress to be ready (takes ~1 minute)
kubectl wait --namespace ingress-nginx `
  --for=condition=ready pod `
  --selector=app.kubernetes.io/component=controller `
  --timeout=120s
```

### Step 3: Start Backend API

```powershell
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate    # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn app.main:app --reload

# Backend will run at: http://localhost:8000
# API docs available at: http://localhost:8000/docs
```

**Keep this terminal open!**

### Step 4: Start Dashboard (New Terminal)

```powershell
# Open NEW terminal window
# Navigate to dashboard directory
cd dashboard

# Install dependencies
npm install

# Start development server
npm start

# Dashboard will automatically open at: http://localhost:3000
```

**Keep this terminal open too!**

### Step 5: Port-forward Ingress (New Terminal)

```powershell
# Open THIRD terminal window
# Port-forward ingress controller for store access
kubectl port-forward --namespace ingress-nginx service/ingress-nginx-controller 8888:80

# This allows accessing stores at: http://<store-name>.localhost:8888
```

**Keep this terminal open as well!**

---

## 🛒 How to Create a Store and Place an Order

### Creating Your First Store

1. **Open Dashboard**
   - Navigate to http://localhost:3000 in your browser

2. **Fill in Store Details**
   - **Store Name:** `my-awesome-store` (lowercase, alphanumeric, hyphens only, 3-20 chars)
   - **Owner Email:** `owner@example.com`

3. **Click "Create Store"**
   - Provisioning takes 2-3 minutes
   - Status will change: `Provisioning` → `Ready`
   - You'll see:
     - Store URL: `http://my-awesome-store.localhost:8888`
     - Admin URL: `http://my-awesome-store.localhost:8888/wp-admin`
     - Admin credentials (username + password)

4. **Wait for "Active" Status**
   - Green badge indicates store is ready
   - Click "Refresh" button to update status

### Placing an Order (End-to-End)

**IMPORTANT:** This demonstrates the complete e-commerce flow required by the assignment.

#### Step 1: Access Store Frontend
```
URL: http://my-awesome-store.localhost:8888
```
- Opens the WooCommerce storefront
- Default theme with sample products

#### Step 2: Add Product to Cart
1. Click on any product (e.g., "Album", "Beanie", "Cap")
2. Click **"Add to Cart"** button
3. Click **"View Cart"** (top right corner)

#### Step 3: Proceed to Checkout
1. In cart page, click **"Proceed to Checkout"**
2. Fill in billing details:
   - First Name: Your Name
   - Last Name: Your Surname
   - Email: youremail@example.com
   - Phone: 1234567890
   - Address: 123 Main Street
   - City: Mumbai
   - State: Maharashtra
   - PIN Code: 400001

#### Step 4: Select Payment Method
1. Choose **"Cash on Delivery"** (enabled by default)
2. Click **"Place Order"** button

#### Step 5: Order Confirmation
- You'll see: **"Order received"** page
- Order number displayed (e.g., Order #15)
- Order details, total amount, billing address shown

#### Step 6: Verify in Admin Panel
1. Open admin panel: `http://my-awesome-store.localhost:8888/wp-admin`
2. Login with provided credentials
3. Navigate to: **WooCommerce → Orders**
4. You'll see your order with:
   - Order number
   - Customer name
   - Total amount
   - Status: "Processing"
   - Date/time

**✅ This completes the required end-to-end order flow!**

### Deleting a Store

1. In dashboard, find your store in the table
2. Click **"Delete"** button (red)
3. Confirm deletion in popup
4. All resources cleaned up:
   - Namespace deleted
   - All pods terminated
   - PVCs removed
   - Ingress rules removed

---

## 📁 Project Structure

```
urumi-submission/
├── README.md                      # This file
├── SYSTEM_DESIGN.md              # Architecture & design decisions
├── .gitignore                    # Git ignore rules
├── kind-config.yaml              # Local cluster configuration
│
├── backend/                      # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app & routes
│   │   ├── models.py            # Pydantic data models
│   │   ├── kubernetes_manager.py # K8s API operations
│   │   └── store_manager.py     # Store creation/deletion logic
│   ├── Dockerfile               # Backend container image
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example            # Environment variables template
│   └── README.md               # Backend documentation
│
├── dashboard/                    # React frontend
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   ├── src/
│   │   ├── App.js              # Main React component
│   │   ├── App.css             # Styling
│   │   ├── index.js            # Entry point
│   │   └── services/
│   │       └── api.js          # API client
│   ├── Dockerfile              # Dashboard container image
│   ├── nginx.conf              # Production web server config
│   ├── package.json            # Node.js dependencies
│   └── .gitignore
│
└── helm-charts/                  # Helm charts
    ├── README.md
    └── platform/                # Platform chart (optional)
        ├── Chart.yaml
        ├── values-local.yaml   # Local environment config
        ├── values-prod.yaml    # Production environment config
        └── templates/
            ├── backend-deployment.yaml
            ├── backend-service.yaml
            ├── dashboard-deployment.yaml
            ├── dashboard-service.yaml
            └── ingress.yaml
```

---

## 🛠️ Tech Stack

### Frontend
- **React** 18.x - UI framework
- **Axios** - HTTP client for API calls
- **CSS3** - Styling

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **Kubernetes Python Client** - K8s API interaction
- **Pydantic** - Data validation

### Infrastructure
- **Kubernetes** 1.35+ - Container orchestration
- **Helm** 3.x - Package manager
- **kind** - Local Kubernetes
- **nginx-ingress** - HTTP routing

### E-commerce
- **WordPress** 6.9.1 - CMS platform
- **WooCommerce** 10.5.0 - E-commerce plugin
- **MariaDB** 12.0.x - Database
- **Bitnami Helm Chart** - Pre-packaged deployment

### Storage
- **PersistentVolumeClaim** - Data persistence
- **local-path-provisioner** - Local storage (kind)
- **hostPath** - Direct host access (alternative)

---

## 🔧 Troubleshooting

### Issue: Dashboard can't connect to backend

**Symptom:** API calls fail with "Network Error"

**Solution:**
```powershell
# Check backend is running
curl http://localhost:8000/health

# If not running, restart backend
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### Issue: Store provisioning stuck in "Provisioning" status

**Symptom:** Store creation takes longer than 5 minutes

**Solution:**
```powershell
# Check pod status
kubectl get pods -n store-<your-store-name>

# Check pod logs
kubectl logs -n store-<your-store-name> <pod-name>

# Common issues:
# 1. Image pull errors - check internet connection
# 2. Resource limits - check cluster has enough resources
# 3. PVC binding issues - check storage provisioner
```

### Issue: Can't access store at localhost:8888

**Symptom:** Browser shows "Can't reach this page"

**Solution:**
```powershell
# Ensure port-forward is running
kubectl port-forward --namespace ingress-nginx service/ingress-nginx-controller 8888:80

# Check ingress exists
kubectl get ingress -n store-<your-store-name>

# Check ingress controller is running
kubectl get pods -n ingress-nginx
```

### Issue: Order placement fails at checkout

**Symptom:** "Payment error" or blank page after clicking "Place Order"

**Solution:**
1. Ensure Cash on Delivery is enabled (enabled by default in Bitnami chart)
2. Check WordPress admin: **WooCommerce → Settings → Payments**
3. Enable "Cash on delivery" if disabled
4. Save changes and retry

### Issue: Pod keeps restarting

**Symptom:** Pod status shows "CrashLoopBackOff"

**Solution:**
```powershell
# Check pod events
kubectl describe pod -n store-<store-name> <pod-name>

# Check pod logs
kubectl logs -n store-<store-name> <pod-name> --previous

# Common fixes:
# 1. Insufficient memory - increase limits in values
# 2. Database connection failure - check MariaDB pod status
# 3. PVC mount issues - check PVC is bound
```

### Issue: Cleanup after kind cluster deletion

**Solution:**
```powershell
# Delete cluster completely
kind delete cluster --name woocommerce-saas

# Recreate fresh cluster
kind create cluster --name woocommerce-saas --config kind-config.yaml

# Reinstall ingress controller (see Step 2 above)
```

---

## 🌐 Production Deployment

### Prerequisites

- **VPS with k3s installed** (Ubuntu 20.04+ recommended)
- **Public IP address**
- **Domain name** (optional but recommended)
- **Docker registry** for images (Docker Hub, GCR, ECR)

### Deployment Steps

#### Step 1: Build and Push Images

```bash
# Build backend image
cd backend
docker build -t yourusername/store-backend:v1.0 .
docker push yourusername/store-backend:v1.0

# Build dashboard image
cd ../dashboard
docker build -t yourusername/store-dashboard:v1.0 .
docker push yourusername/store-dashboard:v1.0
```

#### Step 2: Setup k3s on VPS

```bash
# SSH to VPS
ssh user@your-vps-ip

# Install k3s
curl -sfL https://get.k3s.io | sh -

# Verify installation
sudo k3s kubectl get nodes

# Copy kubeconfig for remote access
sudo cat /etc/rancher/k3s/k3s.yaml
# Save this to your local ~/.kube/config (replace server IP)
```

#### Step 3: Deploy Platform

```bash
# From your local machine with kubeconfig configured
helm install platform ./helm-charts/platform -f ./helm-charts/platform/values-prod.yaml \
  --set backend.image.repository=yourusername/store-backend \
  --set backend.image.tag=v1.0 \
  --set dashboard.image.repository=yourusername/store-dashboard \
  --set dashboard.image.tag=v1.0
```

#### Step 4: Configure DNS (Optional)

If you have a domain:
```bash
# Add A record in DNS provider
platform.yourdomain.com → <VPS-IP>

# Update Ingress in values-prod.yaml
ingress:
  host: platform.yourdomain.com
```

#### Step 5: Add TLS (Optional - Recommended)

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Configure Let's Encrypt in Ingress
# See helm-charts/platform/templates/ingress.yaml for TLS configuration
```

### Key Differences: Local vs Production

| Aspect | Local (kind) | Production (k3s) |
|--------|--------------|------------------|
| **Cluster** | kind | k3s on VPS |
| **Ingress** | NodePort + port-forward | LoadBalancer / NodePort with public IP |
| **Storage** | local-path | Block storage (AWS EBS, GCP PD, etc.) |
| **Images** | Local builds | Docker registry (Docker Hub, GCR, ECR) |
| **Domains** | `*.localhost:8888` | Real domains with DNS |
| **TLS** | Not needed | cert-manager + Let's Encrypt |
| **Secrets** | Generated in cluster | External secrets manager (Sealed Secrets, Vault) |
| **Resources** | Minimal | Production-grade CPU/memory |
| **Monitoring** | kubectl logs | Prometheus + Grafana |
| **Backups** | Not needed | Regular PVC snapshots |

---

## 📊 System Design

For detailed architecture decisions, tradeoffs, and scaling strategies, see [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md).

Key topics covered:
- Architecture choices and rationale
- Idempotency and failure handling
- Cleanup guarantees
- Security posture
- Horizontal scaling approach
- Production deployment strategy

---

## 📝 License

This project was created as part of the Urumi AI SDE Internship - Round 1 assessment.

**Copyright:** © 2026 Prajwal Aswar. All rights reserved.

As per the assessment disclaimer, this work is completely owned by the creator and Urumi will not use this code in production.

---

## 👤 Author

**Prajwal Aswar**
- Email: prajwalaswar0@.com
- Project: Urumi AI SDE Internship - Round 1
- Date: February 2026

---

## 🙏 Acknowledgments

- **Bitnami** for the excellent WordPress Helm chart
- **Kubernetes community** for amazing documentation
- **FastAPI** and **React** teams for great frameworks
- **Urumi AI** for the challenging and educational assignment

---

**Built with ❤️ using Kubernetes, Helm, FastAPI, and React**



<!-- apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    kind: Deployment
    name: platform-backend
  minReplicas: 2
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70 -->