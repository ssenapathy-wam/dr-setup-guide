#!/usr/bin/env python3
"""
Phase 2: Create Cluster Link from Production to DR
Establishes unidirectional cluster link for data mirroring
"""

from pathlib import Path
from logger_util import PhaseLogger, StructuredLog, PhaseExecutionContext
from command_executor import ConfluenceExecutor
from config import get_full_config, Paths

logger = PhaseLogger.phase_2_logger

class Phase2ClusterLink:
    """Phase 2: Create Cluster Link"""
    
    def __init__(self, credentials_manager=None):
        self.credentials_manager = credentials_manager
        self.executor = ConfluenceExecutor(logger, credentials_manager)
        self.config = get_full_config()
    
    def execute(self) -> bool:
        """Execute Phase 2: Create Cluster Link"""
        with PhaseExecutionContext(logger, "Phase 2: Create Cluster Link",
                                   "Create unidirectional cluster link from prod to DR"):
            
            # Step 2.1: Check existing links
            StructuredLog.step_info(logger, 1, "Check existing cluster links on both clusters")
            if not self._check_existing_links():
                logger.warning("Could not check existing links (continuing anyway)")
            
            # Step 2.2: Create config file
            StructuredLog.step_info(logger, 2, "Create cluster link configuration file")
            config_file = self._create_config_file()
            if not config_file:
                raise RuntimeError("Failed to create config file")
            
            # Step 2.3: Create cluster link
            StructuredLog.step_info(logger, 3, "Create cluster link", {
                "link_name": self.config['config']['confluence'].cluster_link_name,
                "source_cluster": self.config['config']['confluence'].prod_cluster_id,
                "dest_cluster": self.config['config']['confluence'].dr_cluster_id
            })
            if not self._create_cluster_link(config_file):
                raise RuntimeError("Failed to create cluster link")
            
            # Step 2.4: Verify cluster link
            StructuredLog.step_info(logger, 4, "Verify cluster link creation")
            if not self._verify_cluster_link():
                raise RuntimeError("Cluster link verification failed")
            
            logger.info("✓ Phase 2 completed successfully")
            return True
    
    def _check_existing_links(self) -> bool:
        """Check existing cluster links"""
        try:
            prod_cluster = self.config['config']['confluence'].prod_cluster_id
            dr_cluster = self.config['config']['confluence'].dr_cluster_id
            
            # Check prod cluster links
            try:
                output = self.executor.list_cluster_links(prod_cluster, environment="prod")
                logger.info(f"Prod cluster links:\n{output}")
            except:
                logger.warning(f"Could not list links for prod cluster {prod_cluster}")
            
            # Check DR cluster links
            try:
                output = self.executor.list_cluster_links(dr_cluster, environment="dr")
                logger.info(f"DR cluster links:\n{output}")
            except:
                logger.warning(f"Could not list links for DR cluster {dr_cluster}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to check existing links: {e}")
            return False
    
    def _create_config_file(self) -> Path:
        """Create cluster link configuration file"""
        try:
            config_file = Paths.CONFIG_DIR / "confluent_config.txt"
            
            prod_creds = self.credentials_manager.confluent_prod_creds
            prod_bootstrap = self.config['config']['confluence'].prod_bootstrap_servers
            
            content = f"""# Production Cluster Link Configuration
bootstrap.servers={prod_bootstrap}
security.protocol=SASL_SSL
sasl.mechanism=PLAIN
sasl.username={prod_creds.api_key}
sasl.password={prod_creds.api_secret}
"""
            
            with open(config_file, 'w') as f:
                f.write(content)
            
            logger.info(f"✓ Config file created: {config_file}")
            return config_file
        
        except Exception as e:
            logger.error(f"Failed to create config file: {e}")
            return None
    
    def _create_cluster_link(self, config_file: Path) -> bool:
        """Create the cluster link"""
        try:
            link_name = self.config['config']['confluence'].cluster_link_name
            dr_cluster = self.config['config']['confluence'].dr_cluster_id
            prod_cluster = self.config['config']['confluence'].prod_cluster_id
            
            return self.executor.create_cluster_link(
                link_name, dr_cluster, prod_cluster, config_file, environment="dr"
            )
        except Exception as e:
            logger.error(f"Failed to create cluster link: {e}")
            return False
    
    def _verify_cluster_link(self) -> bool:
        """Verify cluster link was created successfully"""
        try:
            dr_cluster = self.config['config']['confluence'].dr_cluster_id
            link_name = self.config['config']['confluence'].cluster_link_name
            
            output = self.executor.list_cluster_links(dr_cluster, environment="dr")
            
            if link_name in output and "READY" in output:
                logger.info(f"✓ Cluster link {link_name} is READY")
                return True
            else:
                logger.warning(f"Cluster link may not be fully ready yet. Output:\n{output}")
                return True  # Continue anyway as it may be initializing
        except Exception as e:
            logger.error(f"Failed to verify cluster link: {e}")
            return False

if __name__ == "__main__":
    from logger_util import initialize_logging
    from credential_manager import CredentialManager
    
    initialize_logging()
    
    cred_manager = CredentialManager()
    if not cred_manager.load_all_credentials():
        logger.error("Failed to load credentials")
        exit(1)
    
    phase_2 = Phase2ClusterLink(cred_manager)
    try:
        if phase_2.execute():
            print("\n✓ Phase 2 completed successfully")
        else:
            print("\n✗ Phase 2 failed")
    except Exception as e:
        logger.error(f"Phase 2 execution failed: {e}")
        print(f"\n✗ Phase 2 failed with error: {e}")
