#!/usr/bin/env python3
"""
Phase 3: Mirror Critical Topics to DR Cluster
Creates and monitors topic mirrors from production to DR
"""

from logger_util import PhaseLogger, StructuredLog, PhaseExecutionContext
from command_executor import ConfluenceExecutor
from config import get_full_config
import time

logger = PhaseLogger.phase_3_logger

class Phase3TopicMirroring:
    """Phase 3: Mirror Topics to DR"""
    
    def __init__(self, credentials_manager=None, topics=None):
        self.credentials_manager = credentials_manager
        self.executor = ConfluenceExecutor(logger, credentials_manager)
        self.config = get_full_config()
        self.topics = topics or self.config['config']['topics'].topics
        self.mirrored_topics = []
        self.failed_topics = []
    
    def execute(self) -> bool:
        """Execute Phase 3: Topic Mirroring"""
        with PhaseExecutionContext(logger, "Phase 3: Topic Mirroring",
                                   "Mirror critical topics from prod to DR"):
            
            link_name = self.config['config']['confluence'].cluster_link_name
            dr_cluster = self.config['config']['confluence'].dr_cluster_id
            
            logger.info(f"Mirroring {len(self.topics)} topics...")
            
            # Mirror each topic
            for idx, topic in enumerate(self.topics, 1):
                StructuredLog.step_info(logger, idx, f"Mirror topic: {topic}")
                
                if self._mirror_topic(topic, link_name, dr_cluster):
                    self.mirrored_topics.append(topic)
                    logger.info(f"✓ Successfully mirrored topic: {topic}")
                else:
                    self.failed_topics.append(topic)
                    logger.error(f"✗ Failed to mirror topic: {topic}")
                
                # Wait between operations
                if idx < len(self.topics):
                    time.sleep(2)
            
            # Verify mirrored topics
            StructuredLog.step_info(logger, len(self.topics) + 1, "Verify mirrored topics")
            if not self._verify_mirrors():
                logger.warning("Some topics could not be verified")
            
            # Summary
            logger.info(f"\nMirroring Summary:")
            logger.info(f"  ✓ Successful: {len(self.mirrored_topics)}/{len(self.topics)}")
            if self.failed_topics:
                logger.warning(f"  ✗ Failed: {len(self.failed_topics)}")
                for topic in self.failed_topics:
                    logger.warning(f"    - {topic}")
            
            success = len(self.failed_topics) == 0
            if success:
                logger.info("✓ Phase 3 completed successfully")
            else:
                logger.warning(f"Phase 3 completed with {len(self.failed_topics)} failures")
            
            return success
    
    def _mirror_topic(self, topic_name: str, link_name: str, cluster_id: str) -> bool:
        """Create mirror for a single topic"""
        try:
            return self.executor.create_mirror(topic_name, link_name, cluster_id, environment="dr")
        except Exception as e:
            logger.error(f"Failed to mirror {topic_name}: {e}")
            return False
    
    def _verify_mirrors(self) -> bool:
        """Verify mirrored topics exist on DR cluster"""
        dr_cluster = self.config['config']['confluence'].dr_cluster_id
        verified_count = 0
        
        for topic in self.mirrored_topics:
            try:
                output = self.executor.describe_topic(topic, dr_cluster, environment="dr")
                if topic in output:
                    logger.info(f"✓ Verified: {topic}")
                    verified_count += 1
                else:
                    logger.warning(f"⚠ Could not verify: {topic}")
            except Exception as e:
                logger.warning(f"⚠ Verification error for {topic}: {e}")
        
        logger.info(f"Verified {verified_count}/{len(self.mirrored_topics)} topics")
        return verified_count == len(self.mirrored_topics)

if __name__ == "__main__":
    from logger_util import initialize_logging
    from credential_manager import CredentialManager
    
    initialize_logging()
    
    cred_manager = CredentialManager()
    if not cred_manager.load_all_credentials():
        logger.error("Failed to load credentials")
        exit(1)
    
    phase_3 = Phase3TopicMirroring(cred_manager)
    try:
        if phase_3.execute():
            print("\n✓ Phase 3 completed successfully")
        else:
            print("\n✗ Phase 3 completed with errors")
    except Exception as e:
        logger.error(f"Phase 3 execution failed: {e}")
        print(f"\n✗ Phase 3 failed with error: {e}")
