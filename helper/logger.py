import logging
from datetime import datetime

LOG_FILE = f"./logs/{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.log"
LOG_FORMAT = '[%(asctime)s] - %(name)s - %(levelname)s - %(message)s'
LOGGING_LEVEL = logging.INFO

logging.basicConfig(
    filename=LOG_FILE,
    format=LOG_FORMAT,
    level=logging.INFO,
    datefmt='%Y/%m/%d %H:%M:%S'
)
