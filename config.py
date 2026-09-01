#!/usr/bin/env python3
"""
Configuration Management for DR Setup
Centralized configuration and paths management
"""

import os
from pathlib import Path
from dataclasses import dataclass

# ==============================================================================
# PATHS CONFIGURATION
# ==============================================================================

class Paths:
    """Centralized path management"""
    
    BASE_DIR = Path.cwd()
    CONFIG_DIR = BASE_DIR / "config"
    LOGS_DIR = BASE_DIR / "logs"
    BACKUPS_DIR = BASE_DIR / "backups"
    DATA_DIR = BASE_DIR / "data"
    
    @classmethod
    def create_all_directories(cls):
        """Create all required directories"""
        for directory in [cls.CONFIG_DIR, cls.LOGS_DIR, cls.BACKUPS_DIR, cls.DATA_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# DRY RUN CONFIGURATION
# ==============================================================================

class DryRunConfig:
    """Dry run configuration"""
    ENABLED = os.getenv("DRY_RUN", "false").lower() == "true"
    VERBOSE = os.getenv("DRY_RUN_VERBOSE", "true").lower() == "true"

# ==============================================================================
# RETRY CONFIGURATION
# ==============================================================================

class RetryConfig:
    """Retry and backoff configuration"""
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))  # seconds
    BACKOFF_MULTIPLIER = float(os.getenv("BACKOFF_MULTIPLIER", "2.0"))

# ==============================================================================
# CONFLUENT CONFIGURATION
# ==============================================================================

@dataclass
class ConfluenceConfig:
    """Confluent Cloud configuration"""
    # Environments
    prod_environment_id: str = os.getenv("CONFLUENT_PROD_ENV_ID", "env-prod")
    dr_environment_id: str = os.getenv("CONFLUENT_DR_ENV_ID", "env-dr")
    
    # Clusters
    prod_cluster_id: str = os.getenv("CONFLUENT_PROD_CLUSTER_ID", "lkc-prod")
    dr_cluster_id: str = os.getenv("CONFLUENT_DR_CLUSTER_ID", "lkc-dr")
    
    # Cluster Link
    cluster_link_name: str = os.getenv("CLUSTER_LINK_NAME", "prod-to-dr")
    prod_bootstrap_servers: str = os.getenv(
        "CONFLUENT_PROD_BOOTSTRAP",
        "pkc-prod.region.provider.confluent.cloud:9092"
    )
    
    # Schema Registry
    exporter_name: str = os.getenv("EXPORTER_NAME", "prod-to-dr-exporter")
    exporter_context_type: str = os.getenv("EXPORTER_CONTEXT_TYPE", "CUSTOM")
    exporter_context_name: str = os.getenv("EXPORTER_CONTEXT_NAME", "prod")
    exporter_subjects_pattern: str = os.getenv("EXPORTER_SUBJECTS", ":*:")

# ==============================================================================
# TOPICS CONFIGURATION
# ==============================================================================

@dataclass
class TopicsConfig:
    """Topics configuration"""
    topics: list = None
    
    def __post_init__(self):
        if self.topics is None:
            topics_str = os.getenv(
                "MIRROR_TOPICS",
                "dap.portfolio.compact.portfolio-master-for-analytics.avro"
            )
            self.topics = [t.strip() for t in topics_str.split(",")]

# ==============================================================================
# AWS CONFIGURATION
# ==============================================================================

@dataclass
class AWSConfig:
    """AWS configuration"""
    aws_region: str = os.getenv("AWS_REGION", "us-west-2")
    aws_profile: str = os.getenv("AWS_PROFILE", "DEVCICD")
    eks_cluster_name: str = os.getenv("EKS_CLUSTER_NAME", "es-wt-eks-cluster-nonprod")

# ==============================================================================
# KUBERNETES CONFIGURATION
# ==============================================================================

@dataclass
class KubernetesConfig:
    """Kubernetes configuration"""
    namespace: str = os.getenv("K8S_NAMESPACE", "operator-uat")
    secret_name: str = os.getenv("K8S_SECRET_NAME", "secret-kafka")
    connector_label: str = os.getenv("K8S_CONNECTOR_LABEL", "app=connectors")
    additional_secrets: list = None
    
    def __post_init__(self):
        if self.additional_secrets is None:
            secrets_str = os.getenv("K8S_ADDITIONAL_SECRETS", "")
            self.additional_secrets = [s.strip() for s in secrets_str.split(",") if s.strip()]

# ==============================================================================
# FULL CONFIGURATION
# ==============================================================================

@dataclass
class FullConfig:
    """Complete configuration"""
    confluence: ConfluenceConfig
    topics: TopicsConfig
    aws: AWSConfig
    kubernetes: KubernetesConfig

def get_full_config() -> dict:
    """Get complete configuration as dictionary"""
    return {
        "config": FullConfig(
            confluence=ConfluenceConfig(),
            topics=TopicsConfig(),
            aws=AWSConfig(),
            kubernetes=KubernetesConfig()
        )
    }

if __name__ == "__main__":
    config = get_full_config()
    print("Configuration:")
    print(f"  Confluent:")
    print(f"    Prod Environment: {config['config'].confluence.prod_environment_id}")
    print(f"    DR Environment: {config['config'].confluence.dr_environment_id}")
    print(f"    Topics: {config['config'].topics.topics}")
    print(f"  AWS:")
    print(f"    Region: {config['config'].aws.aws_region}")
    print(f"    EKS Cluster: {config['config'].aws.eks_cluster_name}")
    print(f"  Kubernetes:")
    print(f"    Namespace: {config['config'].kubernetes.namespace}")
