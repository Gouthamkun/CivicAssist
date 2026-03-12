import os
import json
import logging
from datetime import datetime

# Create logs directory
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# File handler for structured pipeline logs
_log_file = os.path.join(LOG_DIR, "pipeline.log")

# Configure module logger
logger = logging.getLogger("civicassist")
logger.setLevel(logging.INFO)

# File handler
fh = logging.FileHandler(_log_file, encoding="utf-8")
fh.setLevel(logging.INFO)
fh.setFormatter(logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s"))
logger.addHandler(fh)

# Console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
logger.addHandler(ch)


def log_pipeline_event(query: str, query_type: str, num_docs: int, response_preview: str = ""):
    """Log a structured pipeline event for debugging retrieval quality."""
    event = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "query_type": query_type,
        "num_documents_retrieved": num_docs,
        "response_preview": response_preview[:200],
    }
    logger.info(f"PIPELINE_EVENT: {json.dumps(event, ensure_ascii=False)}")
