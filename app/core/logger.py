# core/logger.py
import logging

# Create logger
logger = logging.getLogger("tripmate")
logger.setLevel(logging.INFO)  # Change to DEBUG for development

# Console Handler
console_handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
console_handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(console_handler)
