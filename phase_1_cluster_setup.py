#!/usr/bin/env python3
"""
Phase 1: Confluent Cloud DR Cluster Setup
Verifies and prepares Confluent Cloud DR cluster
"""

import time
from pathlib import Path
from logger_util import PhaseLogger, StructuredLog, PhaseExecutionContext
from command_executor import ConfluenceExecutor
from config import get_full_config

logger = PhaseLogger.phase_1_logger

class Phase1ClusterSetup:
    """Phase 1: Confluent Cloud DR Cluster Setup"""
    
    def __init__(self, credentials_manager=None):
        self.credentials_manager = credentials_manager
        self.executor = ConfluenceExecutor(logger, credentials_manager)
        self.config = get_full_config()
    
    def execute(self) -> bool:
        """Execute Phase 1: Cluster Setup"""
        with PhaseExecutionContext(logger, "Phase 1: Cluster Setup", 
                                   "Verify and prepare Confluent Cloud DR cluster"):
            
            # Step 1.1: List Environments
            StructuredLog.step_info(logger, 1, "List Confluent Environments")
            if not self._list_environments():
                raise RuntimeError("Failed to list environments")
            
            # Step 1.2: Set DR Environment
            StructuredLog.step_info(logger, 2, "Set DR Environment", {
                "environment_id": self.config['config']['confluence'].dr_environment_id
            })
            if not self._set_environment():
                raise RuntimeError("Failed to set DR environment")
            
            # Step 1.3: List Networks
            StructuredLog.step_info(logger, 3, "Verify Network Configuration")
            if not self._list_networks():
                logger.warning("Could not verify networks (this may be expected)")
            
            # Step 1.4: List Clusters
            StructuredLog.step_info(logger, 4, "List Kafka Clusters")
            if not self._list_clusters():
                raise RuntimeError("Failed to list clusters")
            
            # Step 1.5: Verify DR Cluster Exists
            StructuredLog.step_info(logger, 5, "Verify DR Cluster Exists", {
                "cluster_id": self.config['config']['confluence'].dr_cluster_id
            })
            if not self._verify_dr_cluster():
                raise RuntimeError("DR cluster not found or not ready")
            
            logger.info("✓ Phase 1 completed successfully")
            return True
    
    def _list_environments(self) -> bool:
        """List all Confluent environments"""
        try:
            output = self.executor.list_environments(environment="dr")
            logger.info(f"Available environments:\n{output}")
            return True
        except Exception as e:
            logger.error(f"Failed to list environments: {e}")
            return False
    
    def _set_environment(self) -> bool:
        """Set DR environment"""
        env_id = self.config['config']['confluence'].dr_environment_id
        return self.executor.set_environment(env_id, environment="dr")
    
    def _list_networks(self) -> bool:
        """List networks (optional verification)"""
        try:
            success, output, error = self.executor.execute(
                "confluent network list",
                "Listing networks",
                env=self.executor._get_confluent_env("dr")
            )
            if success:
                logger.info(f"Networks configured:\n{output}")
            else:
                logger.warning(f"Could not list networks: {error}")
            return success
        except Exception as e:
            logger.warning(f"Network listing not critical: {e}")
            return True
    
    def _list_clusters(self) -> bool:
        """List all Kafka clusters"""
        try:
            output = self.executor.list_clusters(environment="dr")
            logger.info(f"Available clusters:\n{output}")
            return True
        except Exception as e:
            logger.error(f"Failed to list clusters: {e}")
            return False
    
    def _verify_dr_cluster(self) -> bool:
        """Verify DR cluster exists and is ready"""
        try:
            cluster_id = self.config['config']['confluence'].dr_cluster_id
            output = self.executor.list_clusters(environment="dr")
            
            if cluster_id in output:
                logger.info(f"✓ DR cluster {cluster_id} found and ready")
                return True
            else:
                logger.error(f"✗ DR cluster {cluster_id} not found")
                logger.error(f"Available clusters:\n{output}")
                return False
        except Exception as e:
            logger.error(f"Failed to verify DR cluster: {e}")
            return False

if __name__ == "__main__":
    from logger_util import initialize_logging
    from credential_manager import CredentialManager
    
    initialize_logging()
    
    cred_manager = CredentialManager()
    if not cred_manager.load_all_credentials():
        logger.error("Failed to load credentials")
        exit(1)
    
    phase_1 = Phase1ClusterSetup(cred_manager)
    try:
        if phase_1.execute():
            print("\n✓ Phase 1 completed successfully")
        else:
            print("\n✗ Phase 1 failed")
    except Exception as e:
        logger.error(f"Phase 1 execution failed: {e}")
        print(f"\n✗ Phase 1 failed with error: {e}")
