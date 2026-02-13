from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.models import (
    CreateStoreRequest,
    CreateStoreResponse,
    StoreListResponse,
    DeleteStoreResponse,
    HealthResponse,
    StoreResponse
)
from app.store_manager import StoreManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Store Provisioning API",
    description="API for provisioning WooCommerce stores on Kubernetes",
    version="1.0.0"
)

# Add CORS middleware (for React frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize store manager
try:
    store_mgr = StoreManager()
    logger.info("Store Manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Store Manager: {e}")
    store_mgr = None


@app.get("/", tags=["Status"])
def read_root():
    """API root endpoint"""
    return {
        "status": "running",
        "service": "store-provisioning-api",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "stores": "/stores"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Status"])
def health_check():
    """
    Health check endpoint
    
    Checks:
    - API is running
    - Kubernetes connection
    - Helm installation
    """
    if not store_mgr:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Store Manager not initialized"
        )
    
    k8s_connected = store_mgr.k8s.test_connection()
    helm_installed = store_mgr.check_helm_installed()
    
    healthy = k8s_connected and helm_installed
    
    return HealthResponse(
        healthy=healthy,
        kubernetes_connected=k8s_connected,
        helm_installed=helm_installed
    )


@app.post("/stores", response_model=CreateStoreResponse, status_code=status.HTTP_201_CREATED, tags=["Stores"])
def create_store(request: CreateStoreRequest):
    """
    Create a new WooCommerce store
    
    This will:
    1. Create a Kubernetes namespace
    2. Deploy WordPress + MariaDB via Helm
    3. Install and activate WooCommerce plugin
    4. Configure ingress for domain access
    
    **Note:** Store creation takes 2-3 minutes
    """
    if not store_mgr:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Store Manager not initialized"
        )
    
    logger.info(f"Received request to create store: {request.store_name}")
    
    try:
        result = store_mgr.create_store(
            store_name=request.store_name,
            owner_email=request.owner_email
        )
        
        return CreateStoreResponse(
            status="success",
            message=f"Store '{request.store_name}' created successfully",
            data=result
        )
    
    except Exception as e:
        logger.error(f"Failed to create store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Store creation failed: {str(e)}"
        )


@app.get("/stores", response_model=StoreListResponse, tags=["Stores"])
def list_stores():
    """
    List all WooCommerce stores
    
    Returns list of all stores with their details
    """
    if not store_mgr:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Store Manager not initialized"
        )
    
    try:
        stores = store_mgr.list_stores()
        
        store_responses = [
            StoreResponse(
                store_name=store["name"],
                namespace=store["namespace"],
                url=store["url"],
                admin_url=store["admin_url"],
                status=store.get("status", "active"),
                created_at=store.get("created_at")
            )
            for store in stores
        ]
        
        return StoreListResponse(
            count=len(store_responses),
            stores=store_responses
        )
    
    except Exception as e:
        logger.error(f"Failed to list stores: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list stores: {str(e)}"
        )


@app.get("/stores/{store_name}", response_model=dict, tags=["Stores"])
def get_store_status(store_name: str):
    """
    Get detailed status of a specific store
    
    Includes pod status and readiness information
    """
    if not store_mgr:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Store Manager not initialized"
        )
    
    try:
        status_info = store_mgr.get_store_status(store_name)
        
        if not status_info.get("exists"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store '{store_name}' not found"
            )
        
        return {
            "store_name": store_name,
            "namespace": f"store-{store_name}",
            "status": status_info
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get store status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get store status: {str(e)}"
        )


@app.delete("/stores/{store_name}", response_model=DeleteStoreResponse, tags=["Stores"])
def delete_store(store_name: str):
    """
    Delete a WooCommerce store
    
    This will:
    1. Uninstall the Helm release
    2. Delete the Kubernetes namespace (removes all resources)
    
    **Warning:** This action is irreversible!
    """
    if not store_mgr:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Store Manager not initialized"
        )
    
    logger.info(f"Received request to delete store: {store_name}")
    
    # Check if store exists
    if not store_mgr.k8s.namespace_exists(store_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store '{store_name}' not found"
        )
    
    try:
        store_mgr.delete_store(store_name)
        
        return DeleteStoreResponse(
            status="success",
            message=f"Store '{store_name}' deleted successfully",
            store_name=store_name
        )
    
    except Exception as e:
        logger.error(f"Failed to delete store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Store deletion failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
