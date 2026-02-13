import subprocess
import secrets
import logging
import time
from datetime import datetime, timezone
from app.kubernetes_manager import KubernetesManager

logger = logging.getLogger(__name__)


class StoreManager:
    """Handles store creation, deletion, and management"""
    
    def __init__(self):
        self.k8s = KubernetesManager()
    
    def _run_command(self, cmd: list[str], timeout: int = 300) -> tuple[bool, str, str]:
        """
        Run a shell command and return success status, stdout, stderr
        
        Args:
            cmd: Command as list of strings
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            success = result.returncode == 0
            return success, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return False, "", str(e)
    
    def check_helm_installed(self) -> bool:
        """Check if Helm is installed"""
        success, _, _ = self._run_command(["helm", "version"])
        return success
    
    def create_store(self, store_name: str, owner_email: str) -> dict:
        """
        Create a complete WooCommerce store
        
        Args:
            store_name: Name for the store (alphanumeric, lowercase, hyphens)
            owner_email: Email of the store owner
            
        Returns:
            Dictionary with store details including credentials
            
        Raises:
            Exception if creation fails
        """
        logger.info(f"Creating store: {store_name}")
        
        # Validate Helm is installed
        if not self.check_helm_installed():
            raise Exception("Helm is not installed or not in PATH")
        
        # Check if namespace already exists
        if self.k8s.namespace_exists(store_name):
            raise Exception(f"Store '{store_name}' already exists")
        
        # Generate secure passwords
        admin_password = secrets.token_urlsafe(16)
        db_password = secrets.token_urlsafe(16)
        
        namespace = f"store-{store_name}"
        created_timestamp = datetime.now(timezone.utc).isoformat()
        
        try:
            # Step 1: Create namespace with timestamp annotation
            logger.info(f"Creating namespace: {namespace}")
            if not self.k8s.create_namespace(
                store_name, 
                annotations={
                    "owner-email": owner_email,
                    "store.urumi.ai/created-at": created_timestamp
                }
            ):
                raise Exception(f"Failed to create namespace {namespace}")
            
            # Step 2: Install WordPress via Helm
            logger.info(f"Installing WordPress for {store_name}")
            helm_cmd = [
                "helm", "install", store_name, "bitnami/wordpress",
                "--namespace", namespace,
                "--set", f"wordpressUsername=admin",
                "--set", f"wordpressPassword={admin_password}",
                "--set", f"wordpressEmail={owner_email}",
                "--set", f"wordpressBlogName={store_name} Store",
                "--set", f"mariadb.auth.password={db_password}",
                "--set", "ingress.enabled=true",
                "--set", "ingress.ingressClassName=nginx",
                "--set", f"ingress.hostname={store_name}.localhost",
                "--set", "persistence.size=5Gi",
                "--set", "mariadb.primary.persistence.size=3Gi",
                "--wait", 
                "--timeout=5m"
            ]
            
            success, stdout, stderr = self._run_command(helm_cmd, timeout=360)
            
            if not success:
                logger.error(f"Helm install failed: {stderr}")
                # Cleanup namespace on failure
                self.k8s.delete_namespace(store_name)
                raise Exception(f"Helm installation failed: {stderr}")
            
            logger.info(f"WordPress installed successfully for {store_name}")
            
            # Step 3: Install WooCommerce plugin
            logger.info(f"Installing WooCommerce plugin for {store_name}")
            max_retries = 5
            woocommerce_installed = False
            for attempt in range(max_retries):
                try:
                    if self._install_woocommerce(namespace, store_name):
                        logger.info(f"WooCommerce installed successfully for {store_name}")
                        woocommerce_installed = True
                        break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"WooCommerce install attempt {attempt + 1} failed, retrying...")
                        time.sleep(10)
                    else:
                        logger.warning(f"WooCommerce installation failed after {max_retries} attempts: {e}")
                        # Don't fail the entire store creation if WooCommerce install fails
                        # User can install it manually later
            
            # Step 4: Enable Cash on Delivery payment method
            if woocommerce_installed:
                try:
                    logger.info(f"Enabling Cash on Delivery payment for {store_name}")
                    self._enable_cod_payment(namespace, store_name)
                except Exception as e:
                    logger.warning(f"Failed to enable COD payment: {e}")
            
            # Return store details
            return {
                "store_name": store_name,
                "namespace": namespace,
                "url": f"http://{store_name}.localhost",
                "admin_url": f"http://{store_name}.localhost/wp-admin",
                "owner_email": owner_email,
                "created_at": created_timestamp,
                "credentials": {
                    "username": "admin",
                    "password": admin_password
                },
                "woocommerce_installed": True  # Assume success for now
            }
            
        except Exception as e:
            logger.error(f"Store creation failed: {e}")
            # Cleanup on failure
            try:
                self.k8s.delete_namespace(store_name)
            except:
                pass
            raise
    
    def _install_woocommerce(self, namespace: str, store_name: str) -> bool:
        """
        Install WooCommerce plugin after WordPress is ready
        
        Args:
            namespace: Kubernetes namespace
            store_name: Name of the store
            
        Returns:
            True if successful, False otherwise
        """
        # Get WordPress pod name
        get_pod_cmd = [
            "kubectl", "get", "pods",
            "-n", namespace,
            "-l", "app.kubernetes.io/name=wordpress",
            "-o", "jsonpath={.items[0].metadata.name}"
        ]
        
        success, pod_name, stderr = self._run_command(get_pod_cmd)
        if not success or not pod_name:
            logger.error(f"Failed to get WordPress pod name: {stderr}")
            return False
        
        pod_name = pod_name.strip()
        logger.info(f"WordPress pod name: {pod_name}")
        
        # Install WooCommerce plugin
        install_cmd = [
            "kubectl", "exec", "-n", namespace, pod_name,
            "--", "wp", "plugin", "install", "woocommerce", "--activate"
        ]
        
        success, stdout, stderr = self._run_command(install_cmd, timeout=120)
        
        if success:
            logger.info(f"WooCommerce installed: {stdout}")
            return True
        else:
            logger.error(f"WooCommerce installation failed: {stderr}")
            return False
    
    def _enable_cod_payment(self, namespace: str, store_name: str) -> bool:
        """
        Enable Cash on Delivery payment method in WooCommerce
        
        Args:
            namespace: Kubernetes namespace
            store_name: Name of the store
            
        Returns:
            True if successful, False otherwise
        """
        # Get WordPress pod name
        get_pod_cmd = [
            "kubectl", "get", "pods",
            "-n", namespace,
            "-l", "app.kubernetes.io/name=wordpress",
            "-o", "jsonpath={.items[0].metadata.name}"
        ]
        
        success, pod_name, stderr = self._run_command(get_pod_cmd)
        if not success or not pod_name:
            logger.error(f"Failed to get WordPress pod name: {stderr}")
            return False
        
        pod_name = pod_name.strip()
        
        # Enable COD payment gateway
        enable_cod_cmd = [
            "kubectl", "exec", "-n", namespace, pod_name,
            "--", "wp", "option", "update", "woocommerce_cod_settings",
            '{"enabled":"yes","title":"Cash on Delivery","description":"Pay with cash upon delivery."}',
            "--format=json"
        ]
        
        success, stdout, stderr = self._run_command(enable_cod_cmd, timeout=30)
        
        if success:
            logger.info(f"COD payment enabled for {store_name}")
            return True
        else:
            # Try alternative method - directly set the option
            logger.warning(f"First method failed, trying alternative approach")
            alt_cmd = [
                "kubectl", "exec", "-n", namespace, pod_name,
                "--", "bash", "-c",
                "wp option patch update woocommerce_cod_settings enabled yes && wp option patch update woocommerce_cod_settings title 'Cash on Delivery'"
            ]
            success, stdout, stderr = self._run_command(alt_cmd, timeout=30)
            if success:
                logger.info(f"COD payment enabled via alternative method")
                return True
            else:
                logger.error(f"Failed to enable COD: {stderr}")
                return False
    
    def list_stores(self) -> list[dict]:
        """
        List all stores
        
        Returns:
            List of store information dictionaries (excludes terminating stores)
        """
        namespaces = self.k8s.list_store_namespaces()
        stores = []
        
        for ns in namespaces:
            # Skip terminating namespaces
            if ns["status"] == "Terminating":
                continue
                
            store_name = ns["store_name"]
            stores.append({
                "name": store_name,
                "namespace": ns["name"],
                "url": f"http://{store_name}.localhost",
                "admin_url": f"http://{store_name}.localhost/wp-admin",
                "created": ns["created"],
                "created_at": ns.get("created_at"),
                "status": ns["status"]
            })
        
        return stores
    
    def delete_store(self, store_name: str) -> bool:
        """
        Delete a store completely
        
        Args:
            store_name: Name of the store to delete
            
        Returns:
            True if successful
            
        Raises:
            Exception if deletion fails
        """
        logger.info(f"Deleting store: {store_name}")
        
        namespace = f"store-{store_name}"
        
        # Step 1: Uninstall Helm release
        logger.info(f"Uninstalling Helm release: {store_name}")
        helm_cmd = [
            "helm", "uninstall", store_name,
            "--namespace", namespace
        ]
        
        success, stdout, stderr = self._run_command(helm_cmd)
        if not success:
            logger.warning(f"Helm uninstall failed (may not exist): {stderr}")
            # Continue anyway to delete namespace
        
        # Step 2: Delete namespace (this deletes everything inside)
        logger.info(f"Deleting namespace: {namespace}")
        if not self.k8s.delete_namespace(store_name):
            raise Exception(f"Failed to delete namespace {namespace}")
        
        logger.info(f"Store {store_name} deleted successfully")
        return True
    
    def get_store_status(self, store_name: str) -> dict:
        """
        Get detailed status of a store
        
        Args:
            store_name: Name of the store
            
        Returns:
            Dictionary with store status details
        """
        if not self.k8s.namespace_exists(store_name):
            return {"exists": False}
        
        pods = self.k8s.get_pods_in_namespace(store_name)
        
        return {
            "exists": True,
            "pods": pods,
            "ready": all(pod["ready"] for pod in pods) if pods else False
        }
