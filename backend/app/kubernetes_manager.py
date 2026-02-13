from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging

logger = logging.getLogger(__name__)


class KubernetesManager:
    """Handles all Kubernetes API operations"""
    
    def __init__(self):
        """Initialize Kubernetes client"""
        try:
            # Load kubeconfig from default location (~/.kube/config)
            config.load_kube_config()
            self.v1 = client.CoreV1Api()
            self.networking_v1 = client.NetworkingV1Api()
            logger.info("Kubernetes configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Kubernetes config: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test if Kubernetes API is accessible"""
        try:
            self.v1.get_api_resources()
            return True
        except Exception as e:
            logger.error(f"Kubernetes connection test failed: {e}")
            return False
    
    def create_namespace(self, name: str, labels: dict = None, annotations: dict = None) -> bool:
        """
        Create a new namespace for a store
        
        Args:
            name: Name of the store (will be prefixed with 'store-')
            labels: Additional labels for the namespace (must be valid K8s label format)
            annotations: Additional annotations for the namespace (can contain any characters)
            
        Returns:
            True if successful, False otherwise
        """
        namespace = f"store-{name}"
        
        default_labels = {
            "app": "store",
            "store-name": name,
            "managed-by": "store-provisioning-platform"
        }
        
        if labels:
            default_labels.update(labels)
        
        default_annotations = {}
        if annotations:
            default_annotations.update(annotations)
        
        try:
            ns_body = client.V1Namespace(
                metadata=client.V1ObjectMeta(
                    name=namespace,
                    labels=default_labels,
                    annotations=default_annotations if default_annotations else None
                )
            )
            self.v1.create_namespace(ns_body)
            logger.info(f"Created namespace: {namespace}")
            return True
        except ApiException as e:
            if e.status == 409:  # Already exists
                logger.warning(f"Namespace {namespace} already exists")
                return False
            logger.error(f"Failed to create namespace {namespace}: {e}")
            raise
    
    def list_store_namespaces(self) -> list[dict]:
        """
        List all store namespaces
        
        Returns:
            List of dictionaries with namespace info
        """
        try:
            namespaces = self.v1.list_namespace(label_selector="app=store")
            result = []
            
            for ns in namespaces.items:
                annotations = ns.metadata.annotations or {}
                result.append({
                    "name": ns.metadata.name,
                    "store_name": ns.metadata.labels.get("store-name", "unknown"),
                    "created": ns.metadata.creation_timestamp.isoformat() if ns.metadata.creation_timestamp else None,
                    "created_at": annotations.get("store.urumi.ai/created-at"),
                    "status": ns.status.phase
                })
            
            return result
        except ApiException as e:
            logger.error(f"Failed to list store namespaces: {e}")
            return []
    
    def namespace_exists(self, name: str) -> bool:
        """Check if a namespace exists"""
        namespace = f"store-{name}"
        try:
            self.v1.read_namespace(namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise
    
    def delete_namespace(self, name: str) -> bool:
        """
        Delete a store namespace
        
        Args:
            name: Name of the store (without 'store-' prefix)
            
        Returns:
            True if successful, False otherwise
        """
        namespace = f"store-{name}"
        try:
            self.v1.delete_namespace(namespace)
            logger.info(f"Deleted namespace: {namespace}")
            return True
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Namespace {namespace} not found")
                return False
            logger.error(f"Failed to delete namespace {namespace}: {e}")
            raise
    
    def get_pods_in_namespace(self, name: str) -> list[dict]:
        """Get all pods in a store namespace"""
        namespace = f"store-{name}"
        try:
            pods = self.v1.list_namespaced_pod(namespace)
            return [
                {
                    "name": pod.metadata.name,
                    "status": pod.status.phase,
                    "ready": all(cs.ready for cs in pod.status.container_statuses) if pod.status.container_statuses else False
                }
                for pod in pods.items
            ]
        except ApiException as e:
            logger.error(f"Failed to get pods in namespace {namespace}: {e}")
            return []
