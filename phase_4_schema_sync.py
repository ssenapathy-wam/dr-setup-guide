#!/usr/bin/env python3
"""
Phase 4: Schema Registry Synchronization
Creates schema registry exporter to sync schemas from prod to DR
"""

from pathlib import Path
from logger_util import PhaseLogger, StructuredLog, PhaseExecutionContext
from command_executor import ConfluenceExecutor
from config import get_full_config, Paths
import time

logger = PhaseLogger.phase_4_logger

class Phase4SchemSync:
    """Phase 4: Schema Registry Synchronization"""
    
    def __init__(self, credentials_manager=None):
        self.credentials_manager = credentials_manager
        self.executor = ConfluenceExecutor(logger, credentials_manager)
        self.config = get_full_config()
    
    def execute(self) -> bool:
        """Execute Phase 4: Schema Sync"""
        with PhaseExecutionContext(logger, "Phase 4: Schema Registry Sync",
                                   "Synchronize schemas from prod to DR"):
            
            # Step 4.1: Create schema config file
            StructuredLog.step_info(logger, 1, "Create schema exporter configuration")
            config_file = self._create_schema_config_file()
            if not config_file:
                raise RuntimeError("Failed to create schema config file")
            
            # Step 4.2: Create schema exporter
            StructuredLog.step_info(logger, 2, "Create schema registry exporter")
            if not self._create_schema_exporter(config_file):
                raise RuntimeError("Failed to create schema exporter")
            
            # Step 4.3: List exporters
            StructuredLog.step_info(logger, 3, "List all exporters")
            if not self._list_exporters():
                logger.warning("Could not list exporters")
            
            # Step 4.4: Check exporter status
            StructuredLog.step_info(logger, 4, "Verify exporter status")
            if not self._verify_exporter_status():
                logger.warning("Could not verify exporter status")
            
            logger.info("✓ Phase 4 completed successfully")
            return True
    
    def _create_schema_config_file(self) -> Path:
        """Create schema exporter configuration file"""
        try:
            config_file = Paths.CONFIG_DIR / "schema_config.txt"
            
            prod_sr = self.credentials_manager.schema_prod_creds
            dr_sr = self.credentials_manager.schema_dr_creds
            
            content = f"""# Source (Production) Schema Registry Configuration
schema.registry.url={prod_sr.url}
schema.registry.basic.auth.user.info={prod_sr.api_key}:{prod_sr.api_secret}

# Destination (DR) Schema Registry Configuration
destination.schema.registry.url={dr_sr.url}
destination.schema.registry.basic.auth.user.info={dr_sr.api_key}:{dr_sr.api_secret}
"""
            
            with open(config_file, 'w') as f:
                f.write(content)
            
            logger.info(f"✓ Schema config file created: {config_file}")
            return config_file
        
        except Exception as e:
            logger.error(f"Failed to create schema config file: {e}")
            return None
    
    def _create_schema_exporter(self, config_file: Path) -> bool:
        """Create schema registry exporter"""
        try:
            exporter_name = self.config['config']['confluence'].exporter_name
            context_type = self.config['config']['confluence'].exporter_context_type
            context_name = self.config['config']['confluence'].exporter_context_name
            subjects = self.config['config']['confluence'].exporter_subjects_pattern
            
            logger.info(f"Creating exporter: {exporter_name}")
            logger.info(f"  Context type: {context_type}")
            logger.info(f"  Context name: {context_name}")
            logger.info(f"  Subjects: {subjects}")
            
            return self.executor.create_schema_exporter(
                exporter_name, context_type, context_name, subjects, config_file, environment="dr"
            )
        except Exception as e:
            logger.error(f"Failed to create schema exporter: {e}")
            return False
    
    def _list_exporters(self) -> bool:
        """List all schema registry exporters"""
        try:
            output = self.executor.list_exporters(environment="dr")
            logger.info(f"Available exporters:\n{output}")
            return True
        except Exception as e:
            logger.error(f"Failed to list exporters: {e}")
            return False
    
    def _verify_exporter_status(self) -> bool:
        """Verify schema exporter status"""
        try:
            exporter_name = self.config['config']['confluence'].exporter_name
            
            # Wait for exporter to initialize
            logger.info("Waiting for exporter to initialize...")
            time.sleep(5)
            
            output = self.executor.describe_exporter(exporter_name, environment="dr")
            logger.info(f"Exporter status:\n{output}")
            
            return True
        except Exception as e:
            logger.warning(f"Could not verify exporter status: {e}")
            return False

if __name__ == "__main__":
    from logger_util import initialize_logging
    from credential_manager import CredentialManager
    
    initialize_logging()
    
    cred_manager = CredentialManager()
    if not cred_manager.load_all_credentials():
        logger.error("Failed to load credentials")
        exit(1)
    
    phase_4 = Phase4SchemSync(cred_manager)
    try:
        if phase_4.execute():
            print("\n✓ Phase 4 completed successfully")
        else:
            print("\n✗ Phase 4 failed")
    except Exception as e:
        logger.error(f"Phase 4 execution failed: {e}")
        print(f"\n✗ Phase 4 failed with error: {e}")
