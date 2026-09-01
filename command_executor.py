#!/usr/bin/env python3
"""
Command Executor Module for DR Automation
Handles command execution with retry logic, error handling, and credential injection
"""

import subprocess
import time
import os
from typing import Tuple, List, Optional, Dict
from pathlib import Path
from logger_util import PhaseLogger, StructuredLog
from config import RetryConfig, DryRunConfig

# ==============================================================================
# COMMAND EXECUTION BASE CLASS
# ==============================================================================

class CommandExecutor:
    """Execute system commands with retry and error handling"""
    
    def __init__(self, logger=None, credentials_manager=None):
        """
        Initialize command executor
        
        Args:
            logger: Logger instance (defaults to master logger)
            credentials_manager: CredentialManager instance for credential injection
        """
        self.logger = logger or PhaseLogger.master_logger
        self.credentials_manager = credentials_manager
        self.last_output = ""
        self.last_error = ""
    
    def _get_env_vars(self, extra_env: Dict[str, str] = None) -> Dict[str, str]:
        """
        Get environment variables for command execution
        Merges system env with any extra variables
        
        Args:
            extra_env: Additional environment variables to inject
        
        Returns:
            Complete environment dictionary
        """
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        return env
    
    def execute(
        self,
        command: str,
        description: str = "",
        shell: bool = True,
        check: bool = True,
        timeout: int = 300,
        env: dict = None,
        cwd: str = None
    ) -> Tuple[bool, str, str]:
        """
        Execute a shell command with retry logic
        
        Args:
            command: Command to execute
            description: Human-readable description of the command
            shell: Run in shell (default: True)
            check: Raise exception on non-zero exit (default: True)
            timeout: Command timeout in seconds (default: 300)
            env: Environment variables dict
            cwd: Working directory
        
        Returns:
            Tuple of (success, stdout, stderr)
        """
        
        if DryRunConfig.ENABLED:
            self.logger.info(f"[DRY RUN] {description or command}")
            if DryRunConfig.VERBOSE:
                self.logger.info(f"  Command: {command}")
            return (True, "", "")
        
        StructuredLog.command_execution(self.logger, command)
        
        # Prepare environment
        exec_env = self._get_env_vars(env)
        
        for attempt in range(1, RetryConfig.MAX_RETRIES + 1):
            try:
                self.logger.debug(f"Attempt {attempt}/{RetryConfig.MAX_RETRIES}: {description}")
                
                result = subprocess.run(
                    command,
                    shell=shell,
                    capture_output=True,
                    text=True,
                    check=check,
                    timeout=timeout,
                    env=exec_env,
                    cwd=cwd
                )
                
                stdout = result.stdout.strip()
                stderr = result.stderr.strip()
                
                self.last_output = stdout
                self.last_error = stderr
                
                if stdout:
                    StructuredLog.command_output(self.logger, stdout[:200])
                
                if result.returncode == 0:
                    self.logger.info(f"✓ Success: {description}")
                    return (True, stdout, stderr)
                else:
                    if stderr:
                        self.logger.warning(f"  Error: {stderr[:200]}")
                    if attempt < RetryConfig.MAX_RETRIES:
                        StructuredLog.retry_attempt(self.logger, attempt, RetryConfig.MAX_RETRIES)
                        time.sleep(RetryConfig.RETRY_DELAY * (RetryConfig.BACKOFF_MULTIPLIER ** (attempt - 1)))
                        continue
                    return (False, stdout, stderr)
            
            except subprocess.TimeoutExpired:
                self.logger.error(f"  Timeout after {timeout} seconds")
                if attempt < RetryConfig.MAX_RETRIES:
                    StructuredLog.retry_attempt(self.logger, attempt, RetryConfig.MAX_RETRIES)
                    time.sleep(RetryConfig.RETRY_DELAY * (RetryConfig.BACKOFF_MULTIPLIER ** (attempt - 1)))
                else:
                    return (False, "", f"Timeout after {timeout} seconds")
            
            except subprocess.CalledProcessError as e:
                self.logger.error(f"  Command failed with exit code {e.returncode}")
                self.last_error = e.stderr or str(e)
                if attempt < RetryConfig.MAX_RETRIES:
                    StructuredLog.retry_attempt(self.logger, attempt, RetryConfig.MAX_RETRIES)
                    time.sleep(RetryConfig.RETRY_DELAY * (RetryConfig.BACKOFF_MULTIPLIER ** (attempt - 1)))
                else:
                    return (False, e.stdout or "", e.stderr or str(e))
            
            except Exception as e:
                self.logger.error(f"  Unexpected error: {str(e)}")
                if attempt < RetryConfig.MAX_RETRIES:
                    StructuredLog.retry_attempt(self.logger, attempt, RetryConfig.MAX_RETRIES)
                    time.sleep(RetryConfig.RETRY_DELAY * (RetryConfig.BACKOFF_MULTIPLIER ** (attempt - 1)))
                else:
                    return (False, "", str(e))
        
        return (False, "", "Max retries exceeded")
    
    def execute_with_check(
        self,
        command: str,
        description: str = "",
        **kwargs
    ) -> str:
        """
        Execute command and raise exception on failure
        
        Args:
            command: Command to execute
            description: Human-readable description
            **kwargs: Additional arguments for execute()
        
        Returns:
            Command output on success
        
        Raises:
            RuntimeError: If command fails
        """
        success, stdout, stderr = self.execute(command, description, **kwargs)
        if not success:
            raise RuntimeError(f"Command failed: {description}\nError: {stderr}")
        return stdout

# ==============================================================================
# CONFLUENT CLI EXECUTOR
# ==============================================================================

class ConfluenceExecutor(CommandExecutor):
    """Execute Confluent CLI commands with credential injection"""
    
    def __init__(self, logger=None, credentials_manager=None):
        super().__init__(logger, credentials_manager)
        self.environment_id = None
        self.cluster_id = None
    
    def _get_confluent_env(self, environment: str = "prod") -> Dict[str, str]:
        """Get Confluent-specific environment variables"""
        if not self.credentials_manager:
            return {}
        
        try:
            return self.credentials_manager.get_confluent_env_vars(environment)
        except Exception as e:
            self.logger.error(f"Failed to get Confluent credentials: {e}")
            return {}
    
    def set_environment(self, env_id: str, environment: str = "prod"):
        """Set the current Confluent environment"""
        command = f"confluent environment use {env_id}"
        extra_env = self._get_confluent_env(environment)
        
        success, _, _ = self.execute(
            command,
            f"Setting Confluent environment: {env_id}",
            env=extra_env
        )
        if success:
            self.environment_id = env_id
        return success
    
    def login(self, no_browser: bool = True, environment: str = "prod") -> bool:
        """Authenticate with Confluent Cloud via API key"""
        # Note: With API keys, explicit login is often not needed
        # as environment variables are set automatically
        self.logger.info("Confluent Cloud credentials are set via environment variables")
        return True
    
    def list_environments(self, environment: str = "prod") -> str:
        """List all Confluent environments"""
        extra_env = self._get_confluent_env(environment)
        return self.execute_with_check(
            "confluent environment list",
            "Listing Confluent environments",
            env=extra_env
        )
    
    def list_clusters(self, environment: str = "prod") -> str:
        """List all Kafka clusters in current environment"""
        extra_env = self._get_confluent_env(environment)
        return self.execute_with_check(
            "confluent kafka cluster list",
            "Listing Kafka clusters",
            env=extra_env
        )
    
    def list_cluster_links(self, cluster_id: str, environment: str = "prod") -> str:
        """List cluster links for a specific cluster"""
        extra_env = self._get_confluent_env(environment)
        return self.execute_with_check(
            f"confluent kafka link list --cluster {cluster_id}",
            f"Listing cluster links for {cluster_id}",
            env=extra_env
        )
    
    def create_cluster_link(
        self,
        link_name: str,
        destination_cluster: str,
        source_cluster: str,
        config_file: Path,
        environment: str = "prod"
    ) -> bool:
        """Create a cluster link"""
        extra_env = self._get_confluent_env(environment)
        command = (
            f"confluent kafka link create {link_name} "
            f"--cluster {destination_cluster} "
            f"--source-cluster-id {source_cluster} "
            f"--config-file {config_file}"
        )
        success, _, _ = self.execute(
            command,
            f"Creating cluster link: {link_name}",
            env=extra_env
        )
        return success
    
    def create_mirror(
        self,
        topic_name: str,
        link_name: str,
        cluster_id: str,
        environment: str = "prod"
    ) -> bool:
        """Create a mirror topic"""
        extra_env = self._get_confluent_env(environment)
        command = (
            f"confluent kafka mirror create {topic_name} "
            f"--link {link_name} "
            f"--cluster {cluster_id}"
        )
        success, _, _ = self.execute(
            command,
            f"Creating mirror for topic: {topic_name}",
            env=extra_env
        )
        return success
    
    def promote_mirror(
        self,
        topic_name: str,
        link_name: str,
        cluster_id: str,
        environment: str = "prod"
    ) -> bool:
        """Promote a mirror topic to writable"""
        extra_env = self._get_confluent_env(environment)
        command = (
            f"confluent kafka mirror promote {topic_name} "
            f"--link {link_name} "
            f"--cluster {cluster_id}"
        )
        success, _, _ = self.execute(
            command,
            f"Promoting mirror topic: {topic_name}",
            env=extra_env
        )
        return success
    
    def describe_topic(self, topic_name: str, cluster_id: str, environment: str = "prod") -> str:
        """Describe a Kafka topic"""
        extra_env = self._get_confluent_env(environment)
        return self.execute_with_check(
            f"confluent kafka topic describe {topic_name} --cluster {cluster_id}",
            f"Describing topic: {topic_name}",
            env=extra_env
        )
    
    def create_schema_exporter(
        self,
        exporter_name: str,
        context_type: str,
        context_name: str,
        subjects: str,
        config_file: Path,
        environment: str = "prod"
    ) -> bool:
        """Create a schema registry exporter"""
        extra_env = self._get_confluent_env(environment)
        command = (
            f"confluent schema-registry exporter create {exporter_name} "
            f"--context-type {context_type} "
            f"--context-name {context_name} "
            f"--subjects '{subjects}' "
            f"--config-file {config_file}"
        )
        success, _, _ = self.execute(
            command,
            f"Creating schema exporter: {exporter_name}",
            env=extra_env
        )
        return success
    
    def list_exporters(self, environment: str = "prod") -> str:
        """List all schema registry exporters"""
        extra_env = self._get_confluent_env(environment)
        return self.execute_with_check(
            "confluent schema-registry exporter list",
            "Listing schema registry exporters",
            env=extra_env
        )
    
    def describe_exporter(self, exporter_name: str, environment: str = "prod") -> str:
        """Describe a schema registry exporter"""
        extra_env = self._get_confluent_env(environment)
        return self.execute_with_check(
            f"confluent schema-registry exporter describe {exporter_name}",
            f"Describing exporter: {exporter_name}",
            env=extra_env
        )

# ==============================================================================
# AWS CLI EXECUTOR
# ==============================================================================

class AWSExecutor(CommandExecutor):
    """Execute AWS CLI commands with credential injection"""
    
    def __init__(self, logger=None, credentials_manager=None, profile: str = None):
        super().__init__(logger, credentials_manager)
        self.profile = profile
    
    def _get_aws_env(self) -> Dict[str, str]:
        """Get AWS-specific environment variables"""
        if not self.credentials_manager:
            return {}
        
        try:
            return self.credentials_manager.get_aws_env_vars()
        except Exception as e:
            self.logger.error(f"Failed to get AWS credentials: {e}")
            return {}
    
    def _get_profile_option(self) -> str:
        """Get AWS profile option for commands"""
        if self.profile:
            return f"--profile {self.profile}"
        return ""
    
    def update_kubeconfig(self, region: str, cluster_name: str) -> bool:
        """Update kubeconfig for EKS cluster"""
        profile_opt = self._get_profile_option()
        extra_env = self._get_aws_env()
        
        command = (
            f"aws eks update-kubeconfig {profile_opt} "
            f"--region {region} --name {cluster_name}"
        )
        success, _, _ = self.execute(
            command,
            f"Updating kubeconfig for EKS cluster: {cluster_name}",
            env=extra_env
        )
        return success

# ==============================================================================
# KUBECTL EXECUTOR
# ==============================================================================

class KubectlExecutor(CommandExecutor):
    """Execute kubectl commands"""
    
    def __init__(self, logger=None, credentials_manager=None, namespace: str = "default"):
        super().__init__(logger, credentials_manager)
        self.namespace = namespace
    
    def _get_namespace_option(self) -> str:
        """Get namespace option for commands"""
        if self.namespace:
            return f"-n {self.namespace}"
        return ""
    
    def get_nodes(self) -> str:
        """Get cluster nodes"""
        return self.execute_with_check(
            "kubectl get nodes",
            "Getting cluster nodes"
        )
    
    def get_pods(self) -> str:
        """Get pods in namespace"""
        ns_opt = self._get_namespace_option()
        return self.execute_with_check(
            f"kubectl get pods {ns_opt}",
            f"Getting pods in namespace: {self.namespace}"
        )
    
    def get_secret(self, secret_name: str) -> str:
        """Get secret in YAML format"""
        ns_opt = self._get_namespace_option()
        return self.execute_with_check(
            f"kubectl get secret {secret_name} {ns_opt} -o yaml",
            f"Getting secret: {secret_name}"
        )
    
    def edit_secret(self, secret_name: str) -> bool:
        """Edit secret interactively"""
        ns_opt = self._get_namespace_option()
        command = f"kubectl edit secret {secret_name} {ns_opt}"
        success, _, _ = self.execute(
            command,
            f"Editing secret: {secret_name}",
            check=False
        )
        return success
    
    def patch_secret(self, secret_name: str, patch_json: str) -> bool:
        """Patch secret with JSON patch"""
        ns_opt = self._get_namespace_option()
        command = (
            f"kubectl patch secret {secret_name} {ns_opt} "
            f"--type='json' -p='{patch_json}'"
        )
        success, _, _ = self.execute(
            command,
            f"Patching secret: {secret_name}"
        )
        return success
    
    def get_pod_logs(self, pod_name: str, lines: int = 50) -> str:
        """Get pod logs"""
        ns_opt = self._get_namespace_option()
        return self.execute_with_check(
            f"kubectl logs {pod_name} {ns_opt} --tail={lines}",
            f"Getting logs for pod: {pod_name}"
        )
    
    def get_pods_by_label(self, label: str) -> str:
        """Get pods by label"""
        ns_opt = self._get_namespace_option()
        return self.execute_with_check(
            f"kubectl get pods -l {label} {ns_opt}",
            f"Getting pods with label: {label}"
        )
    
    def delete_pod(self, pod_name: str, force: bool = False) -> bool:
        """Delete a pod"""
        ns_opt = self._get_namespace_option()
        command = f"kubectl delete pod {pod_name} {ns_opt}"
        if force:
            command += " --force --grace-period=0"
        
        success, _, _ = self.execute(
            command,
            f"Deleting pod: {pod_name}"
        )
        return success

if __name__ == "__main__":
    # Test command execution
    executor = CommandExecutor()
    success, stdout, stderr = executor.execute(
        "echo 'Command executor test'",
        "Testing command executor"
    )
    print(f"Success: {success}")
    print(f"Output: {stdout}")
