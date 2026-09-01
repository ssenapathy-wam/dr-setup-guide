#!/usr/bin/env python3
"""
Credential Manager Module for DR Automation
Handles secure credential loading, validation, and management
Supports environment variables, config files, and encrypted storage
"""

import os
import json
import base64
from pathlib import Path
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from logger_util import PhaseLogger

# ==============================================================================
# CREDENTIAL DATA CLASSES
# ==============================================================================

@dataclass
class ConfluenceCredentials:
    """Confluent Cloud API credentials"""
    api_key: str
    api_secret: str
    
    def __post_init__(self):
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret cannot be empty")
    
    def mask_for_logging(self) -> str:
        """Return masked version for logging"""
        masked_key = self.api_key[:8] + "***" if len(self.api_key) > 8 else "***"
        return f"Key: {masked_key}"

@dataclass
class SchemaRegistryCredentials:
    """Schema Registry credentials"""
    url: str
    api_key: str
    api_secret: str
    
    def __post_init__(self):
        if not self.url or not self.api_key or not self.api_secret:
            raise ValueError("URL, API key and secret cannot be empty")
    
    def mask_for_logging(self) -> str:
        """Return masked version for logging"""
        masked_key = self.api_key[:8] + "***" if len(self.api_key) > 8 else "***"
        return f"URL: {self.url}, Key: {masked_key}"

@dataclass
class AWSCredentials:
    """AWS credentials"""
    access_key_id: str
    secret_access_key: str
    region: str = "us-west-2"
    
    def __post_init__(self):
        if not self.access_key_id or not self.secret_access_key:
            raise ValueError("AWS access key and secret cannot be empty")
    
    def mask_for_logging(self) -> str:
        """Return masked version for logging"""
        masked_key = self.access_key_id[-8:] if len(self.access_key_id) > 8 else "***"
        return f"Access Key: ***{masked_key}"

# ==============================================================================
# CREDENTIAL LOADER
# ==============================================================================

class CredentialLoader:
    """Load credentials from various sources"""
    
    def __init__(self, logger=None):
        self.logger = logger or PhaseLogger.master_logger
        self.home_dir = Path.home()
        self.confluent_config_dir = self.home_dir / ".confluent"
        self.confluent_config_file = self.confluent_config_dir / "config"
    
    def load_confluent_prod_credentials(self) -> ConfluenceCredentials:
        """Load production Confluent credentials"""
        self.logger.info("Loading production Confluent credentials...")
        
        api_key = os.getenv("CONFLUENT_PROD_API_KEY") or os.getenv("CONFLUENT_CLOUD_API_KEY")
        api_secret = os.getenv("CONFLUENT_PROD_API_SECRET") or os.getenv("CONFLUENT_CLOUD_API_SECRET")
        
        if not api_key or not api_secret:
            self.logger.warning("Environment variables not found, checking config file...")
            api_key, api_secret = self._load_from_config_file("prod")
        
        if not api_key or not api_secret:
            raise ValueError(
                "Confluent production credentials not found. "
                "Set CONFLUENT_PROD_API_KEY and CONFLUENT_PROD_API_SECRET environment variables."
            )
        
        creds = ConfluenceCredentials(api_key, api_secret)
        self.logger.info(f"✓ Loaded production Confluent credentials: {creds.mask_for_logging()}")
        return creds
    
    def load_confluent_dr_credentials(self) -> ConfluenceCredentials:
        """Load DR Confluent credentials"""
        self.logger.info("Loading DR Confluent credentials...")
        
        api_key = os.getenv("CONFLUENT_DR_API_KEY") or os.getenv("CONFLUENT_CLOUD_API_KEY")
        api_secret = os.getenv("CONFLUENT_DR_API_SECRET") or os.getenv("CONFLUENT_CLOUD_API_SECRET")
        
        if not api_key or not api_secret:
            self.logger.warning("Environment variables not found, checking config file...")
            api_key, api_secret = self._load_from_config_file("dr")
        
        if not api_key or not api_secret:
            raise ValueError(
                "Confluent DR credentials not found. "
                "Set CONFLUENT_DR_API_KEY and CONFLUENT_DR_API_SECRET environment variables."
            )
        
        creds = ConfluenceCredentials(api_key, api_secret)
        self.logger.info(f"✓ Loaded DR Confluent credentials: {creds.mask_for_logging()}")
        return creds
    
    def load_schema_registry_prod_credentials(self) -> SchemaRegistryCredentials:
        """Load production Schema Registry credentials"""
        self.logger.info("Loading production Schema Registry credentials...")
        
        url = os.getenv("CONFLUENT_PROD_SR_URL")
        api_key = os.getenv("CONFLUENT_PROD_SR_API_KEY")
        api_secret = os.getenv("CONFLUENT_PROD_SR_API_SECRET")
        
        if not all([url, api_key, api_secret]):
            raise ValueError(
                "Schema Registry production credentials not found. "
                "Set CONFLUENT_PROD_SR_URL, CONFLUENT_PROD_SR_API_KEY, "
                "and CONFLUENT_PROD_SR_API_SECRET environment variables."
            )
        
        creds = SchemaRegistryCredentials(url, api_key, api_secret)
        self.logger.info(f"✓ Loaded production Schema Registry credentials: {creds.mask_for_logging()}")
        return creds
    
    def load_schema_registry_dr_credentials(self) -> SchemaRegistryCredentials:
        """Load DR Schema Registry credentials"""
        self.logger.info("Loading DR Schema Registry credentials...")
        
        url = os.getenv("CONFLUENT_DR_SR_URL")
        api_key = os.getenv("CONFLUENT_DR_SR_API_KEY")
        api_secret = os.getenv("CONFLUENT_DR_SR_API_SECRET")
        
        if not all([url, api_key, api_secret]):
            raise ValueError(
                "Schema Registry DR credentials not found. "
                "Set CONFLUENT_DR_SR_URL, CONFLUENT_DR_SR_API_KEY, "
                "and CONFLUENT_DR_SR_API_SECRET environment variables."
            )
        
        creds = SchemaRegistryCredentials(url, api_key, api_secret)
        self.logger.info(f"✓ Loaded DR Schema Registry credentials: {creds.mask_for_logging()}")
        return creds
    
    def load_aws_credentials(self, profile: str = "DEVCICD") -> AWSCredentials:
        """Load AWS credentials"""
        self.logger.info(f"Loading AWS credentials for profile: {profile}...")
        
        # Try environment variables first
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region = os.getenv("AWS_REGION", "us-west-2")
        
        if access_key and secret_key:
            creds = AWSCredentials(access_key, secret_key, region)
            self.logger.info(f"✓ Loaded AWS credentials from environment: {creds.mask_for_logging()}")
            return creds
        
        # Try AWS credentials file
        credentials_file = self.home_dir / ".aws" / "credentials"
        if credentials_file.exists():
            access_key, secret_key = self._load_from_aws_credentials_file(credentials_file, profile)
            if access_key and secret_key:
                creds = AWSCredentials(access_key, secret_key, region)
                self.logger.info(f"✓ Loaded AWS credentials from file: {creds.mask_for_logging()}")
                return creds
        
        raise ValueError(
            f"AWS credentials not found for profile '{profile}'. "
            "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables "
            "or configure ~/.aws/credentials file."
        )
    
    def _load_from_config_file(self, environment: str) -> Tuple[str, str]:
        """Load credentials from Confluent config file"""
        if not self.confluent_config_file.exists():
            return None, None
        
        try:
            with open(self.confluent_config_file, 'r') as f:
                content = f.read()
            
            # Simple parser for config file format
            section = None
            api_key = None
            api_secret = None
            
            for line in content.split('\n'):
                line = line.strip()
                
                if line.startswith('[') and line.endswith(']'):
                    section = line[1:-1]
                elif section == environment and '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() == 'api_key':
                        api_key = value.strip()
                    elif key.strip() == 'api_secret':
                        api_secret = value.strip()
            
            return api_key, api_secret
        
        except Exception as e:
            self.logger.warning(f"Failed to read config file: {e}")
            return None, None
    
    def _load_from_aws_credentials_file(self, credentials_file: Path, profile: str) -> Tuple[str, str]:
        """Load AWS credentials from ~/.aws/credentials file"""
        try:
            with open(credentials_file, 'r') as f:
                content = f.read()
            
            section = None
            access_key = None
            secret_key = None
            
            for line in content.split('\n'):
                line = line.strip()
                
                if line.startswith('[') and line.endswith(']'):
                    section = line[1:-1]
                elif section == profile and '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() == 'aws_access_key_id':
                        access_key = value.strip()
                    elif key.strip() == 'aws_secret_access_key':
                        secret_key = value.strip()
            
            return access_key, secret_key
        
        except Exception as e:
            self.logger.warning(f"Failed to read AWS credentials file: {e}")
            return None, None

# ==============================================================================
# CREDENTIAL MANAGER
# ==============================================================================

class CredentialManager:
    """Central credential management"""
    
    def __init__(self):
        self.loader = CredentialLoader()
        self.confluent_prod_creds: Optional[ConfluenceCredentials] = None
        self.confluent_dr_creds: Optional[ConfluenceCredentials] = None
        self.schema_prod_creds: Optional[SchemaRegistryCredentials] = None
        self.schema_dr_creds: Optional[SchemaRegistryCredentials] = None
        self.aws_creds: Optional[AWSCredentials] = None
    
    def load_all_credentials(self) -> bool:
        """
        Load all required credentials
        
        Returns:
            True if all credentials loaded successfully
        """
        try:
            PhaseLogger.master_logger.info("="*80)
            PhaseLogger.master_logger.info("LOADING ALL CREDENTIALS")
            PhaseLogger.master_logger.info("="*80)
            
            self.confluent_prod_creds = self.loader.load_confluent_prod_credentials()
            self.confluent_dr_creds = self.loader.load_confluent_dr_credentials()
            self.schema_prod_creds = self.loader.load_schema_registry_prod_credentials()
            self.schema_dr_creds = self.loader.load_schema_registry_dr_credentials()
            self.aws_creds = self.loader.load_aws_credentials()
            
            PhaseLogger.master_logger.info("="*80)
            PhaseLogger.master_logger.info("✓ ALL CREDENTIALS LOADED SUCCESSFULLY")
            PhaseLogger.master_logger.info("="*80)
            return True
        
        except ValueError as e:
            PhaseLogger.master_logger.error(f"✗ CREDENTIAL LOADING FAILED: {e}")
            return False
    
    def get_confluent_env_vars(self, environment: str = "prod") -> Dict[str, str]:
        """Get Confluent environment variables for command execution"""
        creds = self.confluent_prod_creds if environment == "prod" else self.confluent_dr_creds
        
        if not creds:
            raise ValueError(f"Confluent {environment} credentials not loaded")
        
        return {
            "CONFLUENT_CLOUD_API_KEY": creds.api_key,
            "CONFLUENT_CLOUD_API_SECRET": creds.api_secret,
        }
    
    def get_schema_registry_config(self, environment: str = "prod") -> Dict[str, str]:
        """Get Schema Registry configuration dictionary"""
        creds = self.schema_prod_creds if environment == "prod" else self.schema_dr_creds
        
        if not creds:
            raise ValueError(f"Schema Registry {environment} credentials not loaded")
        
        return {
            "url": creds.url,
            "api_key": creds.api_key,
            "api_secret": creds.api_secret,
        }
    
    def get_aws_env_vars(self) -> Dict[str, str]:
        """Get AWS environment variables for command execution"""
        if not self.aws_creds:
            raise ValueError("AWS credentials not loaded")
        
        return {
            "AWS_ACCESS_KEY_ID": self.aws_creds.access_key_id,
            "AWS_SECRET_ACCESS_KEY": self.aws_creds.secret_access_key,
            "AWS_DEFAULT_REGION": self.aws_creds.region,
        }

# ==============================================================================
# CREDENTIAL VALIDATION
# ==============================================================================

class CredentialValidator:
    """Validate credentials are working correctly"""
    
    def __init__(self, logger=None):
        self.logger = logger or PhaseLogger.master_logger
    
    def validate_confluent_credentials(self, creds: ConfluenceCredentials) -> bool:
        """Validate Confluent credentials by listing environments"""
        try:
            import subprocess
            
            env = os.environ.copy()
            env.update({
                "CONFLUENT_CLOUD_API_KEY": creds.api_key,
                "CONFLUENT_CLOUD_API_SECRET": creds.api_secret,
            })
            
            result = subprocess.run(
                "confluent environment list",
                shell=True,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info("✓ Confluent credentials validated successfully")
                return True
            else:
                self.logger.error(f"✗ Confluent credentials validation failed: {result.stderr}")
                return False
        
        except Exception as e:
            self.logger.error(f"✗ Confluent credentials validation error: {e}")
            return False
    
    def validate_aws_credentials(self, creds: AWSCredentials) -> bool:
        """Validate AWS credentials by calling sts"""
        try:
            import subprocess
            
            env = os.environ.copy()
            env.update({
                "AWS_ACCESS_KEY_ID": creds.access_key_id,
                "AWS_SECRET_ACCESS_KEY": creds.secret_access_key,
                "AWS_DEFAULT_REGION": creds.region,
            })
            
            result = subprocess.run(
                "aws sts get-caller-identity",
                shell=True,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info("✓ AWS credentials validated successfully")
                return True
            else:
                self.logger.error(f"✗ AWS credentials validation failed: {result.stderr}")
                return False
        
        except Exception as e:
            self.logger.error(f"✗ AWS credentials validation error: {e}")
            return False

if __name__ == "__main__":
    from logger_util import initialize_logging
    
    initialize_logging()
    
    manager = CredentialManager()
    if manager.load_all_credentials():
        print("✓ All credentials loaded successfully!")
    else:
        print("✗ Failed to load credentials")
