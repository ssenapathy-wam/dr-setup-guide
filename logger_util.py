#!/usr/bin/env python3
"""
Logging Utility Module for DR Automation
Provides centralized logging functionality for all phases
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from datetime import datetime
from config import LogConfig, Paths

# ==============================================================================
# LOGGER SETUP
# ==============================================================================

class LoggerSetup:
    """Centralized logger configuration and setup"""
    
    _loggers = {}

    @staticmethod
    def create_logger(
        name: str,
        log_file: Optional[Path] = None,
        level: str = "INFO"
    ) -> logging.Logger:
        """
        Create and configure a logger instance
        
        Args:
            name: Logger name
            log_file: Path to log file (optional)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
        Returns:
            Configured logger instance
        """
        
        if name in LoggerSetup._loggers:
            return LoggerSetup._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level))
        
        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # Console Handler (STDOUT)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level))
        console_formatter = logging.Formatter(
            '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File Handler
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(getattr(logging, level))
            file_formatter = logging.Formatter(
                '%(asctime)s - [%(name)s] - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        LoggerSetup._loggers[name] = logger
        return logger

# ==============================================================================
# PHASE LOGGERS
# ==============================================================================

class PhaseLogger:
    """Factory for phase-specific loggers"""
    
    phase_1_logger = LoggerSetup.create_logger(
        "Phase-1-ClusterSetup",
        log_file=LogConfig.PHASE_1_LOG
    )
    
    phase_2_logger = LoggerSetup.create_logger(
        "Phase-2-ClusterLink",
        log_file=LogConfig.PHASE_2_LOG
    )
    
    phase_3_logger = LoggerSetup.create_logger(
        "Phase-3-TopicMirroring",
        log_file=LogConfig.PHASE_3_LOG
    )
    
    phase_4_logger = LoggerSetup.create_logger(
        "Phase-4-SchemSync",
        log_file=LogConfig.PHASE_4_LOG
    )
    
    phase_5_logger = LoggerSetup.create_logger(
        "Phase-5-TopicPromotion",
        log_file=LogConfig.PHASE_5_LOG
    )
    
    phase_6_logger = LoggerSetup.create_logger(
        "Phase-6-EKSSetup",
        log_file=LogConfig.PHASE_6_LOG
    )
    
    phase_7_logger = LoggerSetup.create_logger(
        "Phase-7-SecretUpdate",
        log_file=LogConfig.PHASE_7_LOG
    )
    
    master_logger = LoggerSetup.create_logger(
        "DR-Automation-Master",
        log_file=LogConfig.MASTER_LOG
    )

# ==============================================================================
# STRUCTURED LOGGING
# ==============================================================================

class StructuredLog:
    """Structured logging helper for consistent log output"""
    
    @staticmethod
    def phase_start(logger: logging.Logger, phase_name: str, description: str):
        """Log phase start"""
        logger.info("="*80)
        logger.info(f"▶ STARTING: {phase_name}")
        logger.info(f"  Description: {description}")
        logger.info(f"  Timestamp: {datetime.now().isoformat()}")
        logger.info("="*80)
    
    @staticmethod
    def phase_complete(logger: logging.Logger, phase_name: str, duration: float = 0):
        """Log phase completion"""
        logger.info("="*80)
        logger.info(f"✓ COMPLETED: {phase_name}")
        if duration > 0:
            logger.info(f"  Duration: {duration:.2f} seconds")
        logger.info(f"  Timestamp: {datetime.now().isoformat()}")
        logger.info("="*80)
    
    @staticmethod
    def phase_error(logger: logging.Logger, phase_name: str, error: str):
        """Log phase error"""
        logger.error("="*80)
        logger.error(f"✗ FAILED: {phase_name}")
        logger.error(f"  Error: {error}")
        logger.error(f"  Timestamp: {datetime.now().isoformat()}")
        logger.error("="*80)
    
    @staticmethod
    def step_info(logger: logging.Logger, step_num: int, description: str, details: dict = None):
        """Log step information"""
        logger.info(f"  Step {step_num}: {description}")
        if details:
            for key, value in details.items():
                logger.info(f"    - {key}: {value}")
    
    @staticmethod
    def command_execution(logger: logging.Logger, command: str):
        """Log command execution"""
        logger.debug(f"  Executing: {command}")
    
    @staticmethod
    def command_output(logger: logging.Logger, output: str):
        """Log command output"""
        logger.debug(f"  Output: {output}")
    
    @staticmethod
    def retry_attempt(logger: logging.Logger, attempt: int, max_attempts: int):
        """Log retry attempt"""
        logger.warning(f"  Retry attempt {attempt}/{max_attempts}")

# ==============================================================================
# LOG FILE UTILITIES
# ==============================================================================

class LogFileUtil:
    """Utilities for managing log files"""
    
    @staticmethod
    def get_latest_phase_log(phase_num: int) -> Path:
        """Get the latest log file for a specific phase"""
        phase_logs = {
            1: LogConfig.PHASE_1_LOG,
            2: LogConfig.PHASE_2_LOG,
            3: LogConfig.PHASE_3_LOG,
            4: LogConfig.PHASE_4_LOG,
            5: LogConfig.PHASE_5_LOG,
            6: LogConfig.PHASE_6_LOG,
            7: LogConfig.PHASE_7_LOG,
        }
        return phase_logs.get(phase_num)
    
    @staticmethod
    def tail_log_file(log_file: Path, lines: int = 50) -> str:
        """Get the last N lines from a log file"""
        if not log_file.exists():
            return f"Log file not found: {log_file}"
        
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return ''.join(tail_lines)
    
    @staticmethod
    def clear_old_logs(days: int = 7):
        """Clear log files older than specified days"""
        import time
        
        now = time.time()
        cutoff = now - (days * 86400)
        
        for log_file in Paths.LOGS_DIR.glob("*.log"):
            if os.path.getmtime(log_file) < cutoff:
                log_file.unlink()
                PhaseLogger.master_logger.info(f"Deleted old log file: {log_file}")

# ==============================================================================
# CONTEXT MANAGER FOR PHASE LOGGING
# ==============================================================================

class PhaseExecutionContext:
    """Context manager for phase execution logging"""
    
    def __init__(self, logger: logging.Logger, phase_name: str, description: str = ""):
        self.logger = logger
        self.phase_name = phase_name
        self.description = description
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        StructuredLog.phase_start(self.logger, self.phase_name, self.description)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            duration = (datetime.now() - self.start_time).total_seconds()
            StructuredLog.phase_complete(self.logger, self.phase_name, duration)
        else:
            StructuredLog.phase_error(self.logger, self.phase_name, str(exc_val))
        return False

# ==============================================================================
# INITIALIZATION
# ==============================================================================

import os

def initialize_logging():
    """Initialize logging for the entire DR automation"""
    master_logger = PhaseLogger.master_logger
    master_logger.info("DR Automation Logging Initialized")
    master_logger.info(f"Log directory: {Paths.LOGS_DIR}")
    master_logger.info(f"Timestamp: {datetime.now().isoformat()}")

if __name__ == "__main__":
    initialize_logging()
    logger = PhaseLogger.phase_1_logger
    
    logger.info("Logger test successful")
    with PhaseExecutionContext(logger, "Test Phase", "Testing phase logging"):
        logger.info("Inside phase context")
        StructuredLog.step_info(logger, 1, "Test step", {"key": "value"})
    
    print(f"\nLogs written to: {Paths.LOGS_DIR}")
