#!/usr/bin/env python3
"""
Phase 6: AWS EKS Setup and Configuration
Configures kubectl access to EKS cluster and verifies connectivity
"""

from logger_util import PhaseLogger, StructuredLog, PhaseExecutionContext
from command_executor import AWSExecutor, KubectlExecutor
from config import get_full_config

logger = PhaseLogger.phase_6_logger

class Phase6EKSSetup:
    """Phase 6: EKS Setup and Configuration"""
    
    def __init__(self, credentials_manager=None):
        self.credentials_manager = credentials_manager
        self.aws_executor = AWSExecutor(logger, credentials_manager)
        self.config = get_full_config()
    
    def execute(self) -> bool:
        """Execute Phase 6: EKS Setup"""
        with PhaseExecutionContext(logger, "Phase 6: EKS Setup",
                                   "Configure AWS EKS access and verify cluster connectivity"):
            
            # Step 6.1: Update kubeconfig
            StructuredLog.step_info(logger, 1, "Update kubeconfig for EKS cluster", {
                "region": self.config['config']['aws'].aws_region,
                "cluster_name": self.config['config']['aws'].eks_cluster_name
            })
            if not self._update_kubeconfig():
                raise RuntimeError("Failed to update kubeconfig")
            
            # Step 6.2: Verify cluster access
            StructuredLog.step_info(logger, 2, "Verify cluster access")
            if not self._verify_cluster_access():
                raise RuntimeError("Failed to verify cluster access")
            
            # Step 6.3: Get cluster nodes
            StructuredLog.step_info(logger, 3, "List cluster nodes")
            if not self._list_nodes():
                logger.warning("Could not list cluster nodes")
            
            # Step 6.4: Get pods
            StructuredLog.step_info(logger, 4, "List pods in operator-uat namespace")
            if not self._list_pods():
                logger.warning("Could not list pods")
            
            # Step 6.5: Get connector pods
            StructuredLog.step_info(logger, 5, "Identify Kafka Connect connector pods")
            if not self._list_connector_pods():
                logger.warning("Could not list connector pods")
            
            logger.info("✓ Phase 6 completed successfully")
            return True
    
    def _update_kubeconfig(self) -> bool:
        """Update kubeconfig for EKS cluster"""
        try:
            region = self.config['config']['aws'].aws_region
            cluster_name = self.config['config']['aws'].eks_cluster_name
            
            return self.aws_executor.update_kubeconfig(region, cluster_name)
        except Exception as e:
            logger.error(f"Failed to update kubeconfig: {e}")
            return False
    
    def _verify_cluster_access(self) -> bool:
        """Verify we can access the cluster"""
        try:
            kubectl = KubectlExecutor(logger, self.credentials_manager)
            output = kubectl.get_nodes()
            logger.info(f"Cluster nodes:\n{output}")
            return True
        except Exception as e:
            logger.error(f"Failed to verify cluster access: {e}")
            return False
    
    def _list_nodes(self) -> bool:
        """List cluster nodes"""
        try:
            kubectl = KubectlExecutor(logger, self.credentials_manager)
            output = kubectl.get_nodes()
            logger.info(f"Nodes:\n{output}")
            return True
        except Exception as e:
            logger.error(f"Failed to list nodes: {e}")
            return False
    
    def _list_pods(self) -> bool:
        """List pods in operator-uat namespace"""
        try:
            kubectl = KubectlExecutor(logger, self.credentials_manager, 
                                     namespace=self.config['config']['kubernetes'].namespace)
            output = kubectl.get_pods()
            logger.info(f"Pods in namespace {self.config['config']['kubernetes'].namespace}:\n{output}")
            return True
        except Exception as e:
            logger.error(f"Failed to list pods: {e}")
            return False
    
    def _list_connector_pods(self) -> bool:
        """List Kafka Connect connector pods"""
        try:
            kubectl = KubectlExecutor(logger, self.credentials_manager,
                                     namespace=self.config['config']['kubernetes'].namespace)
            output = kubectl.get_pods_by_label(self.config['config']['kubernetes'].connector_label)
            logger.info(f"Connector pods:\n{output}")
            return True
        except Exception as e:
            logger.error(f"Failed to list connector pods: {e}")
            return False

if __name__ == "__main__":
    from logger_util import initialize_logging
    from credential_manager import CredentialManager
    
    initialize_logging()
    
    cred_manager = CredentialManager()
    if not cred_manager.load_all_credentials():
        logger.error("Failed to load credentials")
        exit(1)
    
    phase_6 = Phase6EKSSetup(cred_manager)
    try:
        if phase_6.execute():
            print("\n✓ Phase 6 completed successfully")
        else:
            print("\n✗ Phase 6 failed")
    except Exception as e:
        logger.error(f"Phase 6 execution failed: {e}")
        print(f"\n✗ Phase 6 failed with error: {e}")
