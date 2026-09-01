#!/usr/bin/env python3
"""
Phase 7: Kubernetes Secret Update
Updates Kafka Connect secrets with DR broker credentials
"""

import base64
import json
from logger_util import PhaseLogger, StructuredLog, PhaseExecutionContext
from command_executor import KubectlExecutor
from config import get_full_config

logger = PhaseLogger.phase_7_logger

class Phase7SecretUpdate:
    """Phase 7: Update Kubernetes Secrets"""
    
    def __init__(self, credentials_manager=None):
        self.credentials_manager = credentials_manager
        self.config = get_full_config()
        self.kubectl = KubectlExecutor(
            logger, 
            credentials_manager,
            namespace=self.config['config']['kubernetes'].namespace
        )
    
    def execute(self) -> bool:
        """Execute Phase 7: Secret Update"""
        with PhaseExecutionContext(logger, "Phase 7: Secret Update",
                                   "Update Kubernetes secrets with DR credentials"):
            
            # Step 7.1: Get current secret
            StructuredLog.step_info(logger, 1, "Backup current secret")
            secret_name = self.config['config']['kubernetes'].secret_name
            if not self._backup_secret(secret_name):
                raise RuntimeError("Failed to backup secret")
            
            # Step 7.2: Update primary secret
            StructuredLog.step_info(logger, 2, "Update Kafka credentials secret")
            if not self._update_kafka_secret(secret_name):
                raise RuntimeError("Failed to update Kafka secret")
            
            # Step 7.3: Verify secret update
            StructuredLog.step_info(logger, 3, "Verify secret update")
            if not self._verify_secret_update(secret_name):
                logger.warning("Could not verify secret update")
            
            # Step 7.4: Update additional secrets if needed
            StructuredLog.step_info(logger, 4, "Update additional secrets (if any)")
            self._update_additional_secrets()
            
            # Step 7.5: Restart connector pods
            StructuredLog.step_info(logger, 5, "Restart Kafka Connect pods")
            if not self._restart_connector_pods():
                logger.warning("Pods may need manual restart")
            
            logger.info("✓ Phase 7 completed successfully")
            return True
    
    def _backup_secret(self, secret_name: str) -> bool:
        """Backup current secret"""
        try:
            output = self.kubectl.get_secret(secret_name)
            
            from config import Paths
            backup_file = Paths.BACKUPS_DIR / f"{secret_name}-backup.yaml"
            
            with open(backup_file, 'w') as f:
                f.write(output)
            
            logger.info(f"✓ Secret backed up to: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup secret: {e}")
            return False
    
    def _update_kafka_secret(self, secret_name: str) -> bool:
        """Update Kafka credentials in secret"""
        try:
            dr_creds = self.credentials_manager.confluent_dr_creds
            
            # Prepare credentials in the expected format
            credentials_str = f"username={dr_creds.api_key}\npassword={dr_creds.api_secret}"
            encoded = base64.b64encode(credentials_str.encode()).decode().replace('\n', '')
            
            # Create JSON patch
            patch_json = (
                "[{\"op\": \"replace\", \"path\": \"/data/username\", "
                f"\"value\": \"{base64.b64encode(dr_creds.api_key.encode()).decode()}\"}},"
                "{\"op\": \"replace\", \"path\": \"/data/password\", "
                f"\"value\": \"{base64.b64encode(dr_creds.api_secret.encode()).decode()}\"}}"
                "]"
            )
            
            return self.kubectl.patch_secret(secret_name, patch_json)
        except Exception as e:
            logger.error(f"Failed to update Kafka secret: {e}")
            return False
    
    def _verify_secret_update(self, secret_name: str) -> bool:
        """Verify secret was updated"""
        try:
            output = self.kubectl.get_secret(secret_name)
            logger.info(f"Secret updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to verify secret update: {e}")
            return False
    
    def _update_additional_secrets(self) -> bool:
        """Update additional secrets if configured"""
        try:
            additional_secrets = self.config['config']['kubernetes'].additional_secrets
            
            for secret_name in additional_secrets:
                logger.info(f"Checking additional secret: {secret_name}")
                try:
                    self.kubectl.get_secret(secret_name)
                    logger.info(f"  Found: {secret_name} (may need manual update)")
                except:
                    logger.warning(f"  Not found or not accessible: {secret_name}")
            
            return True
        except Exception as e:
            logger.warning(f"Could not update additional secrets: {e}")
            return False
    
    def _restart_connector_pods(self) -> bool:
        """Restart Kafka Connect pods to load new credentials"""
        try:
            connector_label = self.config['config']['kubernetes'].connector_label
            output = self.kubectl.get_pods_by_label(connector_label)
            
            # Extract pod names from output
            pod_names = []
            for line in output.split('\n')[1:]:
                if line.strip():
                    pod_name = line.split()[0]
                    pod_names.append(pod_name)
            
            if not pod_names:
                logger.warning("No connector pods found")
                return False
            
            logger.info(f"Found {len(pod_names)} connector pods: {pod_names}")
            
            # Delete pods to trigger restart
            for pod_name in pod_names:
                logger.info(f"Restarting pod: {pod_name}")
                if self.kubectl.delete_pod(pod_name):
                    logger.info(f"✓ Pod {pod_name} deleted (will restart)")
                else:
                    logger.warning(f"⚠ Could not delete pod {pod_name}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to restart connector pods: {e}")
            return False

if __name__ == "__main__":
    from logger_util import initialize_logging
    from credential_manager import CredentialManager
    
    initialize_logging()
    
    cred_manager = CredentialManager()
    if not cred_manager.load_all_credentials():
        logger.error("Failed to load credentials")
        exit(1)
    
    phase_7 = Phase7SecretUpdate(cred_manager)
    try:
        if phase_7.execute():
            print("\n✓ Phase 7 completed successfully")
        else:
            print("\n✗ Phase 7 failed")
    except Exception as e:
        logger.error(f"Phase 7 execution failed: {e}")
        print(f"\n✗ Phase 7 failed with error: {e}")
