"""
Utility functions for Country Agent
"""

import logging
import sys
from typing import Any


def setup_logging(name: str = "country_agent", level: str = "INFO") -> logging.Logger:
    """Setup application logging."""
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(name)


def truncate_string(value: Any, max_length: int = 100) -> str:
    """Truncate string for display/logging."""
    if value is None:
        return "None"
    
    str_value = str(value)
    if len(str_value) <= max_length:
        return str_value
    
    return str_value[:max_length] + "..."
