import logging
import sys
import os
from datetime import datetime

def setup_logging(run_id: int = None):

    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)8s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [Run %(run_id)s] %(name)s - %(message)s'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    

    handlers = [console_handler]
    if run_id:
        log_file = f"logs/run_{run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        os.makedirs("logs", exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=handlers
    )
    
    if run_id:
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.run_id = run_id
            return record
        
        logging.setLogRecordFactory(record_factory)
    
    return logging.getLogger(__name__)