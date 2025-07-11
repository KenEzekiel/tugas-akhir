import os
import json
from typing import Any
from src.utils.logger import logger

def write_file(data: Any, filename: str) -> None:
  os.makedirs('data', exist_ok=True)
  output_path = os.path.join('data', filename)
  with open(output_path, 'w') as file:
      json.dump(data, file, indent=2)
  file_logger = logger.getChild("file")
  file_logger.info(f"Results written to {output_path}")

def load_file(filename: str) -> Any:
  input_path = os.path.join('data', filename)
  if not os.path.exists(input_path):
      raise FileNotFoundError(f"File {input_path} does not exist")
  with open(input_path, 'r') as file:
      data = json.load(file)
  file_logger = logger.getChild("file")
  file_logger.info(f"Loaded data from {input_path}")
  return data