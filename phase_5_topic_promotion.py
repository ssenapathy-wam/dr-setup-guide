#!/usr/bin/env python3
"""
Phase 5: Topic Promotion
Promotes read-only mirror topics to writable topics
"""

from logger_util import PhaseLogger, StructuredLog, PhaseExecutionContext
from command_executor import ConfluenceExecutor
from config import get_full_config
import time

logger = PhaseLogger.phase_5_logger

class Phase5TopicPromotion:
    """Phase 5: Promote Mirror Topics"""
    
    def __init__(self, credentials_manager=None, topics=None):
        self.credentials_manager = credentials_manager
        self.executor = ConfluenceExecutor(logger, credentials_manager)
        self.config = get_full_config()
        self.topics = topics or self.config['config']['topics'].topics
        self.promoted_topics = []
        self.failed_topics = []
    
    def execute(self) -> bool:
        """Execute Phase 5: Topic Promotion"""
        with PhaseExecutionContext(logger, "Phase 5: Topic Promotion",
                                   "Promote read-only mirror topics to writable"):
            
            logger.warning("\n" + "="*80)
            logger.warning("⚠ WARNING: Topic promotion is IRREVERSIBLE")
            logger.warning("Once promoted, topics cannot revert to mirror mode")
            logger.warning("Only promote during actual failover to DR")
            logger.warning("="*80 + "\n")
            
            link_name = self.config['config']['confluence'].cluster_link_name
            dr_cluster = self.config['config']['confluence'].dr_cluster_id
            
            logger.info(f"Promoting {len(self.topics)} topics to writable...")
            
            # Promote each topic
            for idx, topic in enumerate(self.topics, 1):
                StructuredLog.step_info(logger, idx, f"Promote topic: {topic}")
                
                if self._promote_topic(topic, link_name, dr_cluster):
                    self.promoted_topics.append(topic)
                    logger.info(f"✓ Successfully promoted topic: {topic}")
                else:
                    self.failed_topics.append(topic)
                    logger.error(f"✗ Failed to promote topic: {topic}")
                
                # Wait between operations
                if idx < len(self.topics):
                    time.sleep(2)
            
            # Summary
            logger.info(f"\nPromotion Summary:")
            logger.info(f"  ✓ Promoted: {len(self.promoted_topics)}/{len(self.topics)}")
            if self.failed_topics:
                logger.error(f"  ✗ Failed: {len(self.failed_topics)}")
                for topic in self.failed_topics:
                    logger.error(f"    - {topic}")
            
            success = len(self.failed_topics) == 0
            if success:
                logger.info("✓ Phase 5 completed successfully")
            else:
                logger.error(f"Phase 5 completed with {len(self.failed_topics)} failures")
            
            return success
    
    def _promote_topic(self, topic_name: str, link_name: str, cluster_id: str) -> bool:
        """Promote a single mirror topic"""
        try:
            return self.executor.promote_mirror(topic_name, link_name, cluster_id, environment="dr")
        except Exception as e:
            logger.error(f"Failed to promote {topic_name}: {e}")
            return False

if __name__ == "__main__":
    from logger_util import initialize_logging
    from credential_manager import CredentialManager
    
    initialize_logging()
    
    cred_manager = CredentialManager()
    if not cred_manager.load_all_credentials():
        logger.error("Failed to load credentials")
        exit(1)
    
    phase_5 = Phase5TopicPromotion(cred_manager)
    try:
        if phase_5.execute():
            print("\n✓ Phase 5 completed successfully")
        else:
            print("\n✗ Phase 5 completed with errors")
    except Exception as e:
        logger.error(f"Phase 5 execution failed: {e}")
        print(f"\n✗ Phase 5 failed with error: {e}")
