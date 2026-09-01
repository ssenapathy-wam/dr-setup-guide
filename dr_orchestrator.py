#!/usr/bin/env python3
"""
DR Setup Orchestrator
Coordinates all phases of the disaster recovery setup process
"""

import sys
import time
from pathlib import Path
from logger_util import initialize_logging, PhaseLogger, StructuredLog
from credential_manager import CredentialManager, CredentialValidator
from config import get_full_config, Paths, DryRunConfig

# Import all phase modules
from phase_1_cluster_setup import Phase1ClusterSetup
from phase_2_cluster_link import Phase2ClusterLink
from phase_3_topic_mirroring import Phase3TopicMirroring
from phase_4_schema_sync import Phase4SchemSync
from phase_5_topic_promotion import Phase5TopicPromotion
from phase_6_eks_setup import Phase6EKSSetup
from phase_7_secret_update import Phase7SecretUpdate

logger = PhaseLogger.master_logger

class DRSetupOrchestrator:
    """Main orchestrator for DR setup process"""
    
    def __init__(self, skip_phases=None, only_phases=None):
        self.skip_phases = skip_phases or []
        self.only_phases = only_phases
        self.credentials_manager = None
        self.config = get_full_config()
        self.phase_results = {}
        self.start_time = None
        self.end_time = None
    
    def run(self) -> bool:
        """Execute the complete DR setup process"""
        self.start_time = time.time()
        
        try:
            # Step 1: Initialize logging and configuration
            logger.info("="*80)
            logger.info("CONFLUENT CLOUD DISASTER RECOVERY SETUP")
            logger.info("="*80)
            
            if DryRunConfig.ENABLED:
                logger.warning("\n[DRY RUN MODE ENABLED]")
                logger.warning("Commands will be logged but not executed\n")
            
            # Step 2: Load credentials
            if not self._load_and_validate_credentials():
                raise RuntimeError("Failed to load and validate credentials")
            
            # Step 3: Create required directories
            Paths.create_all_directories()
            
            # Step 4: Execute phases in order
            phases = self._get_phases_to_execute()
            
            for phase_num, phase_instance in phases:
                if not self._execute_phase(phase_num, phase_instance):
                    if not self._should_continue_on_failure():
                        raise RuntimeError(f"Phase {phase_num} failed")
            
            # Step 5: Print summary
            self._print_summary()
            
            logger.info("\n" + "="*80)
            logger.info("✓ DISASTER RECOVERY SETUP COMPLETED SUCCESSFULLY")
            logger.info("="*80)
            
            self.end_time = time.time()
            return True
        
        except KeyboardInterrupt:
            logger.error("\n\n✗ Setup interrupted by user")
            self.end_time = time.time()
            return False
        
        except Exception as e:
            logger.error(f"\n\n✗ Setup failed with error: {e}")
            logger.exception("Full traceback:")
            self.end_time = time.time()
            return False
    
    def _load_and_validate_credentials(self) -> bool:
        """Load and validate all credentials"""
        logger.info("\nStep 1: Loading Credentials")
        logger.info("-" * 80)
        
        self.credentials_manager = CredentialManager()
        
        if not self.credentials_manager.load_all_credentials():
            logger.error("Failed to load credentials")
            return False
        
        # Validate credentials
        logger.info("\nValidating credentials...")
        validator = CredentialValidator(logger)
        
        if not validator.validate_confluent_credentials(
            self.credentials_manager.confluent_prod_creds
        ):
            logger.warning("Could not validate production Confluent credentials")
        
        if not validator.validate_aws_credentials(self.credentials_manager.aws_creds):
            logger.warning("Could not validate AWS credentials")
        
        return True
    
    def _get_phases_to_execute(self) -> list:
        """Get list of phases to execute"""
        all_phases = [
            (1, Phase1ClusterSetup(self.credentials_manager)),
            (2, Phase2ClusterLink(self.credentials_manager)),
            (3, Phase3TopicMirroring(self.credentials_manager)),
            (4, Phase4SchemSync(self.credentials_manager)),
            (5, Phase5TopicPromotion(self.credentials_manager)),
            (6, Phase6EKSSetup(self.credentials_manager)),
            (7, Phase7SecretUpdate(self.credentials_manager)),
        ]
        
        # Filter phases based on configuration
        filtered_phases = []
        for phase_num, phase_instance in all_phases:
            if self.only_phases and phase_num not in self.only_phases:
                continue
            if phase_num in self.skip_phases:
                logger.info(f"Skipping Phase {phase_num}")
                continue
            filtered_phases.append((phase_num, phase_instance))
        
        return filtered_phases
    
    def _execute_phase(self, phase_num: int, phase_instance) -> bool:
        """Execute a single phase"""
        try:
            logger.info(f"\n\nStep {phase_num}: Executing Phase {phase_num}")
            logger.info("-" * 80)
            
            success = phase_instance.execute()
            self.phase_results[phase_num] = "SUCCESS" if success else "FAILED"
            
            return success
        
        except Exception as e:
            logger.error(f"Phase {phase_num} execution failed: {e}")
            self.phase_results[phase_num] = f"FAILED: {str(e)}"
            return False
    
    def _should_continue_on_failure(self) -> bool:
        """Check if we should continue on failure"""
        # For now, fail fast. Can be made configurable
        return False
    
    def _print_summary(self) -> bool:
        """Print execution summary"""
        logger.info("\n\n" + "="*80)
        logger.info("EXECUTION SUMMARY")
        logger.info("="*80)
        
        for phase_num in sorted(self.phase_results.keys()):
            status = self.phase_results[phase_num]
            symbol = "✓" if status == "SUCCESS" else "✗"
            logger.info(f"  Phase {phase_num}: {symbol} {status}")
        
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            logger.info(f"\nTotal execution time: {duration:.2f} seconds")
        
        logger.info("="*80)

def main():
    """Main entry point"""
    initialize_logging()
    
    # Parse command line arguments
    skip_phases = []
    only_phases = None
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.startswith("--skip="):
            skip_phases = [int(x) for x in arg.split("=")[1].split(",")]
        elif arg.startswith("--only="):
            only_phases = [int(x) for x in arg.split("=")[1].split(",")]
    
    orchestrator = DRSetupOrchestrator(skip_phases=skip_phases, only_phases=only_phases)
    
    success = orchestrator.run()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
