import os
import json
from typing import Any
from utils.logger import logger

def write_file(self, data: Any, filename: str) -> None:
    os.makedirs('data', exist_ok=True)
    output_path = os.path.join('data', filename)
    with open(output_path, 'w') as file:
        json.dump(data, file, indent=2)
    file_logger = logger.getChild("file")
    file_logger.info(f"Results written to {output_path}")
