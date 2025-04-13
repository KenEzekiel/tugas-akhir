import logging
from logging.handlers import RotatingFileHandler
import sys

def setup_logger(name: str = "SmartContractDiscovery"):
    logger = logging.getLogger(name)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)  # Set root logging level
    
    # Prevent duplicate handlers if called multiple times
    if logger.handlers: 
        return logger

    # Format for both handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Terminal handler (existing functionality)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # File handler
    file_handler = RotatingFileHandler(
        'logs/contract_processing.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    # Add both handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Ensure propagation to parent loggers
    logger.propagate = True  
    return logger

# Root logger
logger = setup_logger()