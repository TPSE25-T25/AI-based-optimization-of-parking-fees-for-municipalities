"""
Simple File Manager for CRUD operations
Handles basic file operations with focus on JSON files
"""

import json
import shutil
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


class FileManager:
    """
    Simple file manager for CRUD operations.
    Provides methods for creating, reading, updating, and deleting files.
    Supports JSON, text, and binary file operations.
    """
    
    def __init__(self, base_directory: Optional[Union[str, Path]] = None):
        """
        Initialize File Manager.
        
        Args:
            base_directory: Base directory for file operations. Defaults to current directory.
        """
        self.base_directory = Path(base_directory) if base_directory else Path.cwd()
        self.base_directory.mkdir(parents=True, exist_ok=True)
        
    def _resolve_path(self, file_path: Union[str, Path]) -> Path:
        """Resolve a file path relative to base directory."""
        path = Path(file_path)
        if path.is_absolute():
            return path
        return self.base_directory / path
    
    def _ensure_exists(self, path: Path) -> None:
        """Check if file exists, raise error if not."""
        if not path.exists():
            raise FileNotFoundError(f"File {path} does not exist")
    
    def _check_overwrite(self, path: Path, overwrite: bool) -> None:
        """Check if file exists and handle overwrite logic."""
        if path.exists() and not overwrite:
            raise FileExistsError(f"File {path} already exists. Use overwrite=True to replace.")
        
    def create_json(self, file_path: Union[str, Path], data: Any, overwrite: bool = False) -> bool:
        """
        Create a new JSON file.
        
        Args:
            file_path: Path to the JSON file
            data: Data to write (must be JSON serializable)
            overwrite: Whether to overwrite if file exists
            
        Returns:
            True if created successfully
        """
        path = self._resolve_path(file_path)
        self._check_overwrite(path, overwrite)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
    
    def create_text(self, file_path: Union[str, Path], data: str, overwrite: bool = False) -> bool:
        """
        Create a new text file.
        
        Args:
            file_path: Path to the text file
            data: Text data to write
            overwrite: Whether to overwrite if file exists
            
        Returns:
            True if created successfully
        """
        path = self._resolve_path(file_path)
        self._check_overwrite(path, overwrite)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data)
        
        return True
    
    def create_binary(self, file_path: Union[str, Path], data: bytes, overwrite: bool = False) -> bool:
        """
        Create a new binary file.
        
        Args:
            file_path: Path to the binary file
            data: Binary data to write
            overwrite: Whether to overwrite if file exists
            
        Returns:
            True if created successfully
        """
        path = self._resolve_path(file_path)
        self._check_overwrite(path, overwrite)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'wb') as f:
            f.write(data)
        
        return True
        
    def read_json(self, file_path: Union[str, Path]) -> Any:
        """
        Read and parse a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Parsed JSON data
        """
        path = self._resolve_path(file_path)
        self._ensure_exists(path)
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def read_text(self, file_path: Union[str, Path]) -> str:
        """
        Read a text file.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            File contents as string
        """
        path = self._resolve_path(file_path)
        self._ensure_exists(path)
        
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def read_binary(self, file_path: Union[str, Path]) -> bytes:
        """
        Read a binary file.
        
        Args:
            file_path: Path to the binary file
            
        Returns:
            File contents as bytes
        """
        path = self._resolve_path(file_path)
        self._ensure_exists(path)
        
        with open(path, 'rb') as f:
            return f.read()
        
    def update_json(self, file_path: Union[str, Path], data: Any) -> bool:
        """
        Update an existing JSON file.
        
        Args:
            file_path: Path to the JSON file
            data: New data to write
            
        Returns:
            True if updated successfully
        """
        path = self._resolve_path(file_path)
        self._ensure_exists(path)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
    
    def update_text(self, file_path: Union[str, Path], data: str) -> bool:
        """
        Update an existing text file.
        
        Args:
            file_path: Path to the text file
            data: New text data to write
            
        Returns:
            True if updated successfully
        """
        path = self._resolve_path(file_path)
        self._ensure_exists(path)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data)
        
        return True
    
    def update_binary(self, file_path: Union[str, Path], data: bytes) -> bool:
        """
        Update an existing binary file.
        
        Args:
            file_path: Path to the binary file
            data: New binary data to write
            
        Returns:
            True if updated successfully
        """
        path = self._resolve_path(file_path)
        self._ensure_exists(path)
        
        with open(path, 'wb') as f:
            f.write(data)
        
        return True
    
    def append_text(self, file_path: Union[str, Path], data: str) -> bool:
        """
        Append text data to an existing file.
        
        Args:
            file_path: Path to the text file
            data: Text data to append
            
        Returns:
            True if appended successfully
        """
        path = self._resolve_path(file_path)
        self._ensure_exists(path)
        
        with open(path, 'a', encoding='utf-8') as f:
            f.write(data)
        
        return True
    
    def append_binary(self, file_path: Union[str, Path], data: bytes) -> bool:
        """
        Append binary data to an existing file.
        
        Args:
            file_path: Path to the binary file
            data: Binary data to append
            
        Returns:
            True if appended successfully
        """
        path = self._resolve_path(file_path)
        self._ensure_exists(path)
        
        with open(path, 'ab') as f:
            f.write(data)
        
        return True
    
    def delete(self, file_path: Union[str, Path]) -> bool:
        """
        Delete a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if deleted successfully
        """
        path = self._resolve_path(file_path)
        self._ensure_exists(path)
        path.unlink()
        return True
        
    def exists(self, file_path: Union[str, Path]) -> bool:
        """
        Check if a file exists.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file exists
        """
        path = self._resolve_path(file_path)
        return path.exists() and path.is_file()
    
    def list_files(self, directory: Optional[Union[str, Path]] = None, 
                   pattern: str = "*.json", recursive: bool = False) -> List[Path]:
        """
        List files in a directory.
        
        Args:
            directory: Directory to list (defaults to base_directory)
            pattern: Glob pattern to match files
            recursive: Whether to search recursively
            
        Returns:
            List of file paths
        """
        dir_path = self._resolve_path(directory) if directory else self.base_directory
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory {dir_path} does not exist")
        
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))
        
        return [f for f in files if f.is_file()]


# Convenience instance for easy import
file_manager = FileManager()
