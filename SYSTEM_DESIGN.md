# 📐 System Design & Technical Decisions

**Project:** Kubernetes Store Provisioning Platform  
**Author:** Prajwal Aswar  
**Date:** February 2026  
**Purpose:** Urumi AI SDE Internship - Round 1

---

## 🎯 Executive Summary

This document explains the architectural decisions, tradeoffs, and design rationale for the Store Provisioning Platform. It covers why specific technologies and approaches were chosen, how the system handles failures, and what changes are needed for production deployment.

---

## 🏗️ Architectural Decisions

### 1. Why Bitnami WordPress Helm Chart?

**Decision:** Use Bitnami's official WordPress chart instead of building a custom chart from scratch.

**Rationale:**
- ✅ **Production-tested:** Used by thousands in production, battle-tested
- ✅ **Best practices:** Implements readiness/liveness probes, security contexts, resource limits
- ✅ **Maintenance:** Bitnami handles updates, security patches, bug fixes
- ✅ **WooCommerce support:** Built-in WooCommerce installation via environment variables
- ✅ **Database included:** MariaDB StatefulSet with proper replication support
- ✅ **Time-saving:** Weeks of work already done and tested

**Tradeoffs:**
- ❌ Less control over individual components
- ❌ Larger image sizes (includes extras we don't need)
- ❌ Learning curve to understand chart customization

**Alternative Considered:** Custom Dockerfile + custom Helm chart
- **Rejected because:** Would take 20+ hours to implement properly, higher risk of bugs, ongoing maintenance burden

---

### 2. Why Namespace-per-Store Isolation?

**Decision:** Each store runs in a dedicated Kubernetes namespace (e.g., `store-alice`, `store-bob`).

**Rationale:**
- ✅ **Strong isolation:** Network policies, RBAC, resource quotas per namespace
- ✅ **Clean deletion:** `kubectl delete namespace` removes everything atomically
- ✅ **No naming conflicts:** Same resource names can exist in different namespaces
- ✅ **Tenant separation:** Logical boundary matching business requirement (one store = one tenant)
- ✅ **Debugging:** Easy to see all resources for a specific store (`kubectl get all -n store-alice`)

**Tradeoffs:**
- ❌ Namespace overhead: Each namespace consumes ~10-20MB of etcd space
- ❌ Scaling limits: Kubernetes has soft limit of ~10,000 namespaces per cluster
- ❌ Cross-namespace communication requires explicit network policies

**Alternative Considered:** All stores in one namespace with label selectors
- **Rejected because:** Harder cleanup, no resource quotas per store, naming conflicts

---

### 3. Why FastAPI for Backend?

**Decision:** Use FastAPI (Python) instead of Node.js, Go, or other frameworks.

**Rationale:**
- ✅ **Kubernetes Python Client:** Official, well-maintained library for K8s API
- ✅ **Development speed:** Fast prototyping with automatic API docs (OpenAPI/Swagger)
- ✅ **Type safety:** Pydantic models prevent bugs, great developer experience
- ✅ **Async support:** Handle multiple store creations concurrently
- ✅ **Familiar:** Python is widely known, easy to onboard developers

**Tradeoffs:**
- ❌ Slower than Go/Rust (but sufficient for this use case)
- ❌ Requires virtual environment setup locally

**Alternative Considered:** Node.js with Express
- **Rejected because:** JavaScript's Kubernetes client less mature, no native async/await type safety

---

### 4. Why Helm CLI Execution Instead of Helm SDK?

**Decision:** Backend calls `helm install/delete` commands via subprocess instead of using Helm SDK/library.

**Rationale:**
- ✅ **Simplicity:** Leverages existing Helm CLI, no need to learn SDK
- ✅ **Reliability:** Helm CLI is the reference implementation
- ✅ **Debugging:** Can test exact same commands manually
- ✅ **No version lock-in:** Works with any Helm version installed on system

**Tradeoffs:**
- ❌ Subprocess overhead (~100-200ms per call)
- ❌ Harder to unit test (mocking subprocess calls)
- ❌ Requires Helm installed on backend container

**Alternative Considered:** Helm SDK (Go client or Python wrapper)
- **Rejected because:** SDK not officially supported in Python, unstable, and complex

---

### 5. Why React for Dashboard?

**Decision:** Plain React (Create React App) instead of Next.js, Vue, or Angular.

**Rationale:**
- ✅ **Simplicity:** No SSR complexity, purely client-side rendering
- ✅ **Fast development:** Create React App scaffolds everything
- ✅ **Widely known:** Most developers familiar with React
- ✅ **No backend needed:** Static files served by nginx in production

**Tradeoffs:**
- ❌ No SEO (but not needed for internal dashboard)
- ❌ No server-side rendering (not needed)

**Alternative Considered:** Next.js
- **Rejected because:** Overkill for simple dashboard, requires Node.js server in production

---

## 🔄 Idempotency & Failure Handling

### Store Creation Idempotency

**Challenge:** What if `POST /stores` is called twice with same store name?

**Current Implementation:**
```python
# backend/app/store_manager.py
def create_store(self, store_name: str, owner_email: str):
    # Check if namespace already exists
    if self.k8s.namespace_exists(store_name):
        raise Exception(f"Store '{store_name}' already exists")
    
    # Create namespace
    # Deploy Helm chart
    # ...
```

**Behavior:**
- ✅ First call: Creates store successfully
- ✅ Second call: Returns error "Store already exists" (HTTP 409 Conflict)
- ✅ No duplicate resources created
- ✅ Safe to retry after fixing issues

**Future Enhancement:**
- Implement true idempotency: return existing store details instead of error
- Check Helm release status: if failed, re-run; if succeeded, return existing

---

### Failure Scenarios & Handling

#### Scenario 1: Helm Install Fails Mid-deployment

**Example:** Database PVC fails to bind due to storage issues.

**Current Behavior:**
- Helm release marked as "failed"
- Namespace exists but pods stuck in Pending state
- Dashboard shows "Provisioning" status indefinitely

**Recovery:**
```python
# Manual cleanup required:
helm delete <store-name> -n <namespace>
kubectl delete namespace <namespace>
```

**Future Enhancement:**
```python
# Add timeout and auto-cleanup
def create_store_with_timeout(self, store_name, owner_email, timeout=300):
    try:
        result = self.create_store(store_name, owner_email)
        # Poll status for 5 minutes
        if not self.wait_for_ready(store_name, timeout):
            self.delete_store(store_name)  # Auto-cleanup
            raise Exception("Store creation timed out")
    except Exception as e:
        self.delete_store(store_name)  # Cleanup on any error
        raise
```

#### Scenario 2: Backend Crashes Mid-provisioning

**Example:** Backend pod killed while Helm is installing a store.

**Current Behavior:**
- Helm continues running independently (separate process)
- Store may complete successfully OR fail silently
- Dashboard loses track of creation status

**Current Mitigation:**
- User can check store status manually via dashboard "Refresh" button
- Helm release exists in cluster (survives backend restart)

**Future Enhancement:**
- Use Kubernetes Jobs for provisioning (survives backend restart)
- Store creation state in database (Redis/PostgreSQL)
- Background reconciliation loop to detect orphaned resources

#### Scenario 3: Delete Called on Non-existent Store

**Current Behavior:**
```python
def delete_store(self, store_name):
    if not self.k8s.namespace_exists(store_name):
        raise Exception(f"Store '{store_name}' not found")
    
    # Helm delete
    # Delete namespace
```

- Returns HTTP 404 Not Found
- No resources deleted
- Idempotent (safe to retry)

---

## 🧹 Cleanup Guarantees

### What Gets Deleted?

When `DELETE /stores/{name}` is called:

```python
# backend/app/store_manager.py
def delete_store(self, store_name: str):
    namespace = f"store-{store_name}"
    
    # 1. Delete Helm release (removes Deployments, StatefulSets, Services, ConfigMaps, Secrets)
    subprocess.run(["helm", "delete", store_name, "-n", namespace])
    
    # 2. Delete namespace (removes PVCs, remaining resources)
    self.k8s.delete_namespace(namespace)
```

**Resources Cleaned Up:**
- ✅ WordPress Deployment/Pods
- ✅ MariaDB StatefulSet/Pods
- ✅ Services (WordPress, MariaDB)
- ✅ PersistentVolumeClaims (WordPress data, MariaDB data)
- ✅ ConfigMaps
- ✅ Secrets (passwords, credentials)
- ✅ Ingress rules
- ✅ Namespace itself

**Cleanup Order:**
1. Helm delete removes most resources gracefully
2. Namespace deletion cascades to remaining resources
3. PVCs deleted with `kubectl delete namespace` (finalizers handled)

**PersistentVolume Behavior:**
- **Local (kind):** PV marked as "Released", can be reclaimed manually
- **Production:** Depends on storage class `reclaimPolicy`:
  - `Delete`: PV auto-deleted (cloud disks destroyed)
  - `Retain`: PV kept for manual backup/inspection

---

## 🔐 Security Posture

### Secret Handling

**Current Implementation:**
```python
# Auto-generate secure passwords
admin_password = secrets.token_urlsafe(16)  # 128-bit entropy
db_password = secrets.token_urlsafe(16)

# Pass via Helm values (NOT environment variables or config files)
helm install ... --set wordpressPassword=$admin_password --set mariadb.auth.password=$db_password
```

**Security Features:**
- ✅ Passwords never hardcoded in source code
- ✅ Unique password per store (no shared secrets)
- ✅ Stored in Kubernetes Secrets (base64-encoded at rest)
- ✅ Secrets scoped to namespace (isolated per store)

**Production Enhancements:**
- Use **Sealed Secrets** (encrypt secrets in Git)
- Use **External Secrets Operator** (fetch from Vault/AWS Secrets Manager)
- Enable **encryption-at-rest** in etcd (Kubernetes control plane)

### RBAC (Future Enhancement)

**Not Implemented Yet:**
```yaml
# Create ServiceAccount for backend
apiVersion: v1
kind: ServiceAccount
metadata:
  name: store-provisioner
  namespace: default

---
# Grant minimal permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: store-provisioner
rules:
- apiGroups: [""]
  resources: ["namespaces"]
  verbs: ["create", "delete", "list"]
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["list", "get"]
```

**Why Not Implemented:**
- Backend currently uses default service account (full cluster admin in kind)
- Production deployment MUST implement least-privilege RBAC

### What's Exposed Publicly vs Internal

**Public (Accessible from Internet in Production):**
- Dashboard (React app)
- Backend API (if deployed with LoadBalancer)
- Individual store frontends (via Ingress)

**Internal (ClusterIP services, not exposed):**
- MariaDB databases (no external access)
- WordPress admin panels (accessible via storefront, authenticated)

**Network Isolation (Future Enhancement):**
```yaml
# NetworkPolicy: Deny all traffic except explicitly allowed
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
  namespace: store-alice
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

---

## 📈 Horizontal Scaling Strategy

### What Scales Horizontally?

#### 1. Backend API (Platform)
**Current:** 1 replica (local), 2 replicas (production)

**Scaling Approach:**
- Increase replica count in `values-prod.yaml`
- Add Horizontal Pod Autoscaler (HPA):
```yaml
apiVersion: autoscaling/v2
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
        averageUtilization: 70
```

**Challenges:**
- Store creation uses Helm CLI (subprocess) - no shared state
- Multiple backend pods might provision simultaneously → race condition

**Solution:**
- Use distributed lock (Redis) before Helm install
- OR use Kubernetes Job for each store creation (one Job = one store)

#### 2. Dashboard (React)
**Current:** 1 replica

**Scaling Approach:**
- Stateless static files served by nginx
- Can scale to 100+ replicas without issues
- HPA based on CPU or request rate

**No Challenges:** Completely stateless

#### 3. Individual Stores (WordPress)
**Current:** 1 WordPress pod per store

**Scaling Approach:**
```yaml
# In store Helm values
replicaCount: 3  # Run 3 WordPress pods

# Shared storage required
persistence:
  storageClass: "aws-efs"  # Network filesystem (EFS, NFS, CephFS)
```

**Challenges:**
- WordPress uploads stored on disk → needs ReadWriteMany PVC
- Local storage (hostPath) doesn't support multiple pods
- Solution: Use network storage (NFS, EFS, Azure Files)

#### 4. MariaDB (Per Store)
**Current:** 1 MariaDB pod per store (StatefulSet with 1 replica)

**Scaling Approach:**
```yaml
# MariaDB primary + read replicas
primary:
  replicaCount: 1
secondary:
  replicaCount: 2  # Add read replicas
```

**Challenges:**
- Write operations go to primary (single point of write)
- Read replicas help with read-heavy traffic (product browsing)
- Requires more complex storage setup

**Better Alternative for Production:**
- Use managed database (AWS RDS, Google Cloud SQL)
- Remove MariaDB pods entirely
- Connect WordPress to external database

---

## 🌐 Local-to-VPS Production Story

### What Changes Between Local and Production?

| Component | Local (kind) | Production (k3s/VPS) |
|-----------|--------------|----------------------|
| **Container Images** | Built locally, loaded to kind | Pushed to Docker Hub/GCR/ECR |
| **Image Pull** | `imagePullPolicy: Never` | `imagePullPolicy: Always` |
| **Dashboard Service** | NodePort 30000 | LoadBalancer (public IP) |
| **Backend Service** | NodePort 30001 | LoadBalancer OR ClusterIP (internal) |
| **Ingress Access** | Port-forward 8888 | Public IP on port 80/443 |
| **Storage Class** | `local-path` | `gp2` (AWS), `pd-standard` (GCP), `longhorn` (self-hosted) |
| **TLS** | None (HTTP only) | cert-manager + Let's Encrypt |
| **Domains** | `*.localhost:8888` | Real DNS (`alice.myplatform.com`) |
| **Secrets** | In-cluster Secrets | Sealed Secrets OR Vault |
| **Monitoring** | `kubectl logs` | Prometheus + Grafana |
| **Backup** | None | Daily PVC snapshots, etcd backups |
| **Resource Limits** | Minimal (1 CPU, 2GB RAM) | Production-grade (4 CPU, 8GB RAM) |

### Helm Values Differences

**values-local.yaml:**
```yaml
backend:
  image:
    repository: store-platform-backend
    tag: latest
    pullPolicy: Never  # Don't pull from registry
  service:
    type: NodePort
    nodePort: 30001

dashboard:
  service:
    type: NodePort
    nodePort: 30000

ingress:
  enabled: false  # Use port-forward instead
```

**values-prod.yaml:**
```yaml
backend:
  image:
    repository: yourusername/store-platform-backend
    tag: v1.0.0  # Specific version
    pullPolicy: Always  # Pull from Docker Hub
  service:
    type: LoadBalancer  # Get public IP

dashboard:
  service:
    type: LoadBalancer

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: platform.yourdomain.com
      paths: ["/"]
  tls:
    - secretName: platform-tls
      hosts: ["platform.yourdomain.com"]
```

### DNS Configuration

**Local:**
- No DNS needed
- Access via `http://localhost:3000` and port-forwards

**Production:**
```
# Add A records in DNS provider (Cloudflare, Route53, etc.)
platform.yourdomain.com  →  <VPS-Public-IP>
*.stores.yourdomain.com  →  <VPS-Public-IP>

# Example store URLs
http://alice.stores.yourdomain.com
http://bob.stores.yourdomain.com
```

### TLS/SSL Setup

**Production (cert-manager):**
```yaml
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create Let's Encrypt ClusterIssuer
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@yourdomain.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx

# Ingress automatically gets TLS certificate
```

---

## 🚀 Upgrade & Rollback Strategy

### Upgrading Platform (Backend/Dashboard)

**Current Approach:**
```bash
# Build new image version
docker build -t yourusername/store-backend:v1.1.0 .
docker push yourusername/store-backend:v1.1.0

# Upgrade Helm release
helm upgrade platform ./helm-charts/platform \
  -f values-prod.yaml \
  --set backend.image.tag=v1.1.0

# Zero-downtime rolling update
kubectl rollout status deployment/platform-backend
```

**Rollback:**
```bash
# Helm keeps last 10 revisions by default
helm rollback platform 1  # Rollback to revision 1

# OR revert to previous image tag
helm upgrade platform ./helm-charts/platform \
  --set backend.image.tag=v1.0.0
```

### Upgrading Individual Stores (WordPress/WooCommerce)

**Challenge:** 100 stores running WordPress 6.9.1, want to upgrade to 6.10.0

**Approach 1: In-place upgrade (managed by WordPress)**
```bash
# WordPress auto-updates (enabled by default in Bitnami chart)
# OR manually trigger via WP-CLI
kubectl exec -n store-alice <wordpress-pod> -- \
  wp core update --allow-root
```

**Approach 2: Helm upgrade (for major version changes)**
```bash
# Upgrade Helm release with new chart version
helm upgrade alice bitnami/wordpress \
  --version 28.2.0 \  # New chart version
  -n store-alice \
  --reuse-values  # Keep existing passwords, configs
```

**Risk Mitigation:**
- Test on one store first
- Backup database before upgrade (PVC snapshot)
- Implement blue-green deployment for critical stores

---

## 🔄 Concurrency & Provisioning Throughput

### Current Limitations

**Single-threaded provisioning:**
- Backend API handles requests sequentially
- Each `helm install` blocks for 2-3 minutes
- Throughput: ~20-30 stores/hour (1 backend pod)

### Scaling Provisioning Throughput

**Approach 1: Async Task Queue**
```python
# backend/app/main.py
from celery import Celery
from app.store_manager import StoreManager

celery_app = Celery('tasks', broker='redis://localhost:6379')

@celery_app.task
def create_store_async(store_name, owner_email):
    mgr = StoreManager()
    return mgr.create_store(store_name, owner_email)

@app.post("/stores")
async def create_store(request: CreateStoreRequest):
    # Queue task, return immediately
    task = create_store_async.delay(request.store_name, request.owner_email)
    return {"task_id": task.id, "status": "queued"}
```

**Benefits:**
- ✅ Non-blocking API (returns immediately)
- ✅ Horizontal scaling (multiple Celery workers)
- ✅ Retry logic built-in
- ✅ Throughput: 100+ stores/hour

**Approach 2: Kubernetes Jobs**
```python
# Create Job resource for each store creation
job = client.V1Job(
    metadata=client.V1ObjectMeta(name=f"provision-{store_name}"),
    spec=client.V1JobSpec(
        template=client.V1PodTemplateSpec(
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="provisioner",
                        image="store-provisioner:latest",
                        env=[
                            {"name": "STORE_NAME", "value": store_name},
                            {"name": "OWNER_EMAIL", "value": owner_email}
                        ]
                    )
                ]
            )
        )
    )
)
```

**Benefits:**
- ✅ Kubernetes-native (survives backend restarts)
- ✅ Automatic retry on failure
- ✅ Parallel execution (limited by cluster resources)

---

## 🛡️ Abuse Prevention & Rate Limiting

### Current State: No Protection ❌

**Vulnerabilities:**
- Unlimited store creation (could exhaust cluster resources)
- No rate limiting (API can be spammed)
- No user authentication (anyone can create/delete stores)

### Recommended Protections

#### 1. Rate Limiting (API Level)
```python
# backend/app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/stores")
@limiter.limit("5/hour")  # Max 5 stores per hour per IP
async def create_store(request: Request, data: CreateStoreRequest):
    # ...
```

#### 2. ResourceQuota Per Namespace
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: store-quota
  namespace: store-alice
spec:
  hard:
    requests.cpu: "2"      # Max 2 CPU cores
    requests.memory: "4Gi" # Max 4GB RAM
    persistentvolumeclaims: "2"  # Max 2 PVCs
    pods: "10"             # Max 10 pods
```

#### 3. Global Limits (Platform Level)
```python
# backend/app/store_manager.py
MAX_STORES_PER_USER = 5
MAX_TOTAL_STORES = 100

def create_store(self, store_name, user_id):
    # Check per-user limit
    user_stores = self.get_user_stores(user_id)
    if len(user_stores) >= MAX_STORES_PER_USER:
        raise Exception("User store limit reached")
    
    # Check global limit
    total_stores = len(self.list_all_stores())
    if total_stores >= MAX_TOTAL_STORES:
        raise Exception("Platform store limit reached")
```

#### 4. Provisioning Timeout
```python
PROVISION_TIMEOUT = 600  # 10 minutes

def create_store_with_timeout(self, store_name, owner_email):
    start_time = time.time()
    
    # Start provisioning
    self.helm_install(store_name)
    
    # Poll until ready or timeout
    while time.time() - start_time < PROVISION_TIMEOUT:
        if self.is_store_ready(store_name):
            return
        time.sleep(10)
    
    # Timeout: cleanup and fail
    self.delete_store(store_name)
    raise Exception("Provisioning timeout exceeded")
```

---

## 📊 Monitoring & Observability

### Current State: Basic Logging

**What we have:**
```python
# backend/app/main.py
import logging

logger = logging.getLogger(__name__)
logger.info(f"Creating store: {store_name}")
logger.error(f"Failed to create store: {error}")
```

### Production Observability Stack

**Metrics (Prometheus):**
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)

# Custom metrics
store_creation_counter = Counter('stores_created_total', 'Total stores created')
store_creation_duration = Histogram('store_creation_duration_seconds', 'Time to create store')
```

**Logging (ELK Stack):**
```python
import structlog

logger = structlog.get_logger()
logger.info("store.created", store_name=name, owner_email=email, duration_seconds=123)
```

**Dashboards (Grafana):**
- Total stores created
- Active stores count
- Average provisioning time
- Failed provisioning rate
- API request rate and latency

---

## 🎯 Summary of Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **E-commerce Engine** | WooCommerce (WordPress) | Production-ready, mature ecosystem, Bitnami chart |
| **Isolation Model** | Namespace-per-store | Clean separation, easy cleanup, resource quotas |
| **Backend Framework** | FastAPI (Python) | K8s client library, fast development, type safety |
| **Frontend Framework** | React | Simple, widely known, no SSR needed |
| **Deployment Tool** | Helm | Industry standard, templating, values-based config |
| **Local Cluster** | kind | Fast, lightweight, multi-node support |
| **Production Target** | k3s on VPS | Lightweight, production-ready, same as local |
| **Storage** | PersistentVolumeClaims | Kubernetes-native, survives pod restarts |
| **Secrets** | Auto-generated (secrets.token_urlsafe) | Secure, unique per store |
| **Provisioning** | Helm CLI via subprocess | Simple, reliable, debuggable |

---

## 🔮 Future Enhancements

**Not implemented due to time constraints, but recommended for production:**

1. ✅ **User Authentication** - Add login system, tie stores to users
2. ✅ **Billing Integration** - Charge per store or usage
3. ✅ **Backup & Restore** - Automated PVC snapshots, disaster recovery
4. ✅ **Managed Database Option** - Connect to external PostgreSQL/MySQL
5. ✅ **Custom Domains** - Let users bring their own domains
6. ✅ **SSL/TLS Auto-config** - Automatic HTTPS for custom domains
7. ✅ **Store Templates** - Pre-configured themes, plugins, products
8. ✅ **Multi-region Support** - Deploy stores to closest region
9. ✅ **Cost Tracking** - Calculate resource usage per store
10. ✅ **Audit Logs** - Complete trail of who did what when

---

**This platform demonstrates production-ready Kubernetes orchestration, cloud-native architecture, and DevOps best practices suitable for scaling to thousands of stores.**
