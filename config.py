#!/usr/bin/env python3
"""
Disaster Recovery (DR) Setup Configuration
Central configuration file for all DR automation scripts
"""

import os
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass
import json

# ==============================================================================
# ENVIRONMENT CONFIGURATION
# ==============================================================================

@dataclass
class ConfluenceConfig:
    """Confluent Cloud configuration"""
    # Production Environment
    prod_environment_id: str = "env-prod"
    prod_cluster_id: str = "lkc-m2qgx"
    prod_bootstrap_servers: str = "pkc-prod.region.provider.confluent.cloud:9092"
    prod_api_key: str = ""  # Set via environment variable
    prod_api_secret: str = ""  # Set via environment variable
    prod_sr_url: str = "https://psrc-prod.region.provider.confluent.cloud"
    prod_sr_api_key: str = ""  # Set via environment variable
    prod_sr_api_secret: str = ""  # Set via environment variable

    # DR Environment
    dr_environment_id: str = "env-xrwzz"
    dr_cluster_id: str = "lkc-xqrk0kz"
    dr_bootstrap_servers: str = "pkc-dr.region.provider.confluent.cloud:9092"
    dr_api_key: str = ""  # Set via environment variable
    dr_api_secret: str = ""  # Set via environment variable
    dr_sr_url: str = "https://psrc-dr.region.provider.confluent.cloud"
    dr_sr_api_key: str = ""  # Set via environment variable
    dr_sr_api_secret: str = ""  # Set via environment variable

    # Cluster Link Configuration
    cluster_link_name: str = "cl-prod-to-dr"

    # Schema Registry Exporter Configuration
    exporter_name: str = "prod-to-dr-schema-exporter"
    exporter_context_type: str = "CUSTOM"
    exporter_context_name: str = "prod"
    exporter_subjects_pattern: str = ":*:"

@dataclass
class AWSConfig:
    """AWS EKS configuration"""
    aws_profile: str = "DEVCICD"
    aws_region: str = "us-west-2"
    eks_cluster_name: str = "es-wt-eks-cluster-nonprod"
    
@dataclass
class KubernetesConfig:
    """Kubernetes configuration"""
    namespace: str = "operator-uat"
    connector_label: str = "app=connectors"
    secret_name: str = "secret-kafka"
    additional_secrets: list = None

    def __post_init__(self):
        if self.additional_secrets is None:
            self.additional_secrets = ["es-conf-platform-uat-secret"]

@dataclass
class TopicConfig:
    """Topics to be mirrored"""
    topics: list = None

    def __post_init__(self):
        if self.topics is None:
            self.topics = [
                "dap.portfolio.compact.portfolio-master-for-analytics.avro",
                "dev.gdr.analytics.compact.bmk-analytic.avro"
            ]

# ==============================================================================
# PATHS AND LOGGING
# ==============================================================================

class Paths:
    """Directory and file paths"""
    BASE_DIR = Path(__file__).parent.absolute()
    CONFIG_DIR = BASE_DIR / "config"
    LOGS_DIR = BASE_DIR / "logs"
    BACKUPS_DIR = BASE_DIR / "backups"
    TEMP_DIR = BASE_DIR / "temp"
    
    # Ensure directories exist
    CONFIG_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)

    # Configuration files
    CONFLUENT_CONFIG = CONFIG_DIR / "confluent_config.txt"
    SCHEMA_CONFIG = CONFIG_DIR / "schema_config.txt"
    AWS_CREDENTIALS = Path.home() / ".aws" / "credentials"
    KUBECONFIG = Path.home() / ".kube" / "config"

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================

class LogConfig:
    """Logging configuration"""
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_LEVEL = "INFO"
    LOG_DIR = Paths.LOGS_DIR
    
    # Phase-specific logs
    PHASE_1_LOG = LOG_DIR / "phase_1_cluster_setup.log"
    PHASE_2_LOG = LOG_DIR / "phase_2_cluster_link.log"
    PHASE_3_LOG = LOG_DIR / "phase_3_topic_mirroring.log"
    PHASE_4_LOG = LOG_DIR / "phase_4_schema_sync.log"
    PHASE_5_LOG = LOG_DIR / "phase_5_topic_promotion.log"
    PHASE_6_LOG = LOG_DIR / "phase_6_eks_setup.log"
    PHASE_7_LOG = LOG_DIR / "phase_7_secret_update.log"
    MASTER_LOG = LOG_DIR / "dr_automation_master.log"

# ==============================================================================
# TIMEOUT CONFIGURATIONS
# ==============================================================================

class TimeoutConfig:
    """Timeout configurations (in seconds)"""
    CLUSTER_LINK_CREATION = 300  # 5 minutes
    TOPIC_REPLICATION = 3600  # 1 hour
    SCHEMA_EXPORT = 600  # 10 minutes
    EKS_OPERATION = 300  # 5 minutes
    POD_RESTART = 600  # 10 minutes
    SECRET_UPDATE = 120  # 2 minutes
    KUBERNETES_OPERATION = 300  # 5 minutes

# ==============================================================================
# RETRY CONFIGURATIONS
# ==============================================================================

class RetryConfig:
    """Retry configurations"""
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    BACKOFF_MULTIPLIER = 2

# ==============================================================================
# NOTIFICATION CONFIGURATION
# ==============================================================================

@dataclass
class NotificationConfig:
    """Notification settings"""
    enable_notifications: bool = False
    email_on_failure: bool = True
    email_recipients: list = None
    slack_webhook_url: str = ""
    
    def __post_init__(self):
        if self.email_recipients is None:
            self.email_recipients = ["ops-team@example.com"]

# ==============================================================================
# INITIALIZATION FUNCTION
# ==============================================================================

def load_config_from_env() -> Dict[str, Any]:
    """
    Load configuration from environment variables
    Supports overriding defaults via environment
    """
    config = {
        "confluence": ConfluenceConfig(
            prod_api_key=os.getenv("CONFLUENT_PROD_API_KEY", ""),
            prod_api_secret=os.getenv("CONFLUENT_PROD_API_SECRET", ""),
            prod_sr_api_key=os.getenv("CONFLUENT_PROD_SR_API_KEY", ""),
            prod_sr_api_secret=os.getenv("CONFLUENT_PROD_SR_API_SECRET", ""),
            dr_api_key=os.getenv("CONFLUENT_DR_API_KEY", ""),
            dr_api_secret=os.getenv("CONFLUENT_DR_API_SECRET", ""),
            dr_sr_api_key=os.getenv("CONFLUENT_DR_SR_API_KEY", ""),
            dr_sr_api_secret=os.getenv("CONFLUENT_DR_SR_API_SECRET", ""),
        ),
        "aws": AWSConfig(
            aws_profile=os.getenv("AWS_PROFILE", "DEVCICD"),
            aws_region=os.getenv("AWS_REGION", "us-west-2"),
            eks_cluster_name=os.getenv("EKS_CLUSTER_NAME", "es-wt-eks-cluster-nonprod"),
        ),
        "kubernetes": KubernetesConfig(
            namespace=os.getenv("K8S_NAMESPACE", "operator-uat"),
        ),
        "topics": TopicConfig(),
        "notifications": NotificationConfig(),
    }
    return config

# ==============================================================================
# DRY RUN CONFIGURATION
# ==============================================================================

class DryRunConfig:
    """Dry run mode - prints commands without executing"""
    ENABLED = os.getenv("DRY_RUN", "false").lower() == "true"
    VERBOSE = True

# ==============================================================================
# EXPORT CONFIGURATION
# ==============================================================================

def get_full_config() -> Dict[str, Any]:
    """Get complete configuration object"""
    return {
        "paths": Paths,
        "logging": LogConfig,
        "timeouts": TimeoutConfig,
        "retries": RetryConfig,
        "dry_run": DryRunConfig,
        "config": load_config_from_env(),
    }

if __name__ == "__main__":
    # Test configuration loading
    config = get_full_config()
    print("Configuration loaded successfully!")
    print(f"Base directory: {Paths.BASE_DIR}")
    print(f"Logs directory: {Paths.LOGS_DIR}")
    print(f"DR Environment: {config['config']['confluence'].dr_environment_id}")
    print(f"EKS Cluster: {config['config']['aws'].eks_cluster_name}")
