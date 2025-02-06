"""File operation utilities."""

import json
import os
import threading
import logging

# Global file lock manager
class FileLocker:
    """File lock manager to ensure thread-safe file operations."""
    
    def __init__(self):
        """Initialize the file lock manager."""
        self.locks = {}
        self.lock = threading.Lock()
    
    def get_lock(self, filename):
        """Get a lock for a specific file.
        
        Args:
            filename (str): Path to file
            
        Returns:
            threading.Lock: Lock for the file
        """
        with self.lock:
            if filename not in self.locks:
                self.locks[filename] = threading.Lock()
            return self.locks[filename]

file_locker = FileLocker()

def safe_read_json(file_path):
    """Safely read JSON from a file.
    
    Args:
        file_path (str): Path to JSON file
        
    Returns:
        dict: JSON data or None if error occurs
    """
    with file_locker.get_lock(file_path):
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error reading {file_path}: {str(e)}")
    return None

def safe_save_json(file_path, data):
    """Safely save JSON data to a file.
    
    Args:
        file_path (str): Path to save JSON file
        data (dict): Data to save
    """
    with file_locker.get_lock(file_path):
        try:
            # 创建目录
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving {file_path}: {str(e)}")
