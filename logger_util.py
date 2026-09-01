#!/usr/bin/env python3
"""
Logging Utilities for DR Setup
Provides structured logging for all phases
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from config import Paths

# ==============================================================================
# LOG FORMATTING
# ==============================================================================

class ColoredFormatter(logging.Formatter):
    """Formatter with color support"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

# ==============================================================================
# PHASE LOGGERS
# ==============================================================================

class PhaseLogger:
    """Centralized logger management"""
    
    master_logger = None
    phase_1_logger = None
    phase_2_logger = None
    phase_3_logger = None
    phase_4_logger = None
    phase_5_logger = None
    phase_6_logger = None
    phase_7_logger = None

# ==============================================================================
# STRUCTURED LOGGING
# ==============================================================================

class StructuredLog:
    """Structured logging helpers"""
    
    @staticmethod
    def step_info(logger, step_num: int, description: str, details: dict = None):
        """Log step information"""
        logger.info(f"\n[Step {step_num}] {description}")
        if details:
            for key, value in details.items():
                logger.info(f"  {key}: {value}")
    
    @staticmethod
    def command_execution(logger, command: str):
        """Log command execution"""
        logger.debug(f"Executing: {command}")
    
    @staticmethod
    def command_output(logger, output: str, max_length: int = 200):
        """Log command output"""
        if len(output) > max_length:
            output = output[:max_length] + "..."
        logger.debug(f"Output: {output}")
    
    @staticmethod
    def retry_attempt(logger, attempt: int, max_attempts: int):
        """Log retry attempt"""
        logger.warning(f"Retry {attempt}/{max_attempts}...")
    
    @staticmethod
    def phase_start(logger, phase_num: int, description: str):
        """Log phase start"""
        logger.info(f"\n{'='*80}")
        logger.info(f"PHASE {phase_num}: {description}")
        logger.info(f"{'='*80}")
    
    @staticmethod
    def phase_complete(logger, phase_num: int, success: bool):
        """Log phase completion"""
        status = "SUCCESS" if success else "FAILED"
        symbol = "✓" if success else "✗"
        logger.info(f"\nPhase {phase_num}: {symbol} {status}")

# ==============================================================================
# CONTEXT MANAGERS
# ==============================================================================

@contextmanager
class PhaseExecutionContext:
    """Context manager for phase execution"""
    
    def __init__(self, logger, phase_name: str, description: str):
        self.logger = logger
        self.phase_name = phase_name
        self.description = description
    
    def __enter__(self):
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"{self.phase_name}")
        self.logger.info(f"{self.description}")
        self.logger.info(f"{'='*80}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.logger.error(f"\n✗ {self.phase_name} failed with exception")
            return False
        return True

# ==============================================================================
# INITIALIZATION
# ==============================================================================

def initialize_logging(log_level: str = "INFO"):
    """Initialize logging system"""
    
    # Create logs directory
    log_dir = Paths.LOGS_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Log file path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"dr_setup_{timestamp}.log"
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = ColoredFormatter(
        '%(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(console_formatter)
    
    # Configure master logger
    master_logger = logging.getLogger('dr_setup')
    master_logger.setLevel(logging.DEBUG)
    master_logger.addHandler(file_handler)
    master_logger.addHandler(console_handler)
    master_logger.propagate = False
    
    PhaseLogger.master_logger = master_logger
    
    # Create phase-specific loggers
    for phase_num in range(1, 8):
        phase_logger = logging.getLogger(f'dr_setup.phase_{phase_num}')
        phase_logger.setLevel(logging.DEBUG)
        phase_logger.addHandler(file_handler)
        phase_logger.addHandler(console_handler)
        phase_logger.propagate = False
        
        setattr(PhaseLogger, f'phase_{phase_num}_logger', phase_logger)
    
    master_logger.info(f"Logging initialized. Log file: {log_file}")

if __name__ == "__main__":
    initialize_logging()
    logger = PhaseLogger.master_logger
    logger.info("Testing master logger")
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
