import pytest
import tempfile
import shutil
from pathlib import Path
from backend.services.io.file_manager import FileManager


class TestFileManager:
    """Unit tests for FileManager class"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures before each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.file_manager = FileManager(base_directory=self.temp_dir)
        
        yield
        
        # Teardown
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_create_json_success(self):
        """Test creating a new JSON file"""
        test_data = {"name": "test", "value": 123}
        result = self.file_manager.create_json("test.json", test_data)
        
        assert result is True
        assert self.file_manager.exists("test.json") is True
        
        read_data = self.file_manager.read_json("test.json")
        assert read_data == test_data
    
    def test_create_json_with_nested_directory(self):
        """Test creating JSON file in nested directory"""
        test_data = {"nested": True}
        result = self.file_manager.create_json("subdir/nested/test.json", test_data)
        
        assert result is True
        assert self.file_manager.exists("subdir/nested/test.json") is True
    
    def test_create_json_overwrite_false(self):
        """Test that creating existing JSON file without overwrite raises error"""
        test_data = {"test": "data"}
        self.file_manager.create_json("test.json", test_data)
        
        with pytest.raises(FileExistsError):
            self.file_manager.create_json("test.json", test_data, overwrite=False)
    
    def test_create_json_overwrite_true(self):
        """Test overwriting existing JSON file"""
        original_data = {"original": "data"}
        new_data = {"new": "data"}
        
        self.file_manager.create_json("test.json", original_data)
        result = self.file_manager.create_json("test.json", new_data, overwrite=True)
        
        assert result is True
        read_data = self.file_manager.read_json("test.json")
        assert read_data == new_data
    
    def test_read_json_success(self):
        """Test reading JSON file"""
        test_data = {"key": "value", "number": 42}
        self.file_manager.create_json("test.json", test_data)
        
        result = self.file_manager.read_json("test.json")
        assert result == test_data
    
    def test_read_json_file_not_found(self):
        """Test reading non-existent JSON file raises error"""
        with pytest.raises(FileNotFoundError):
            self.file_manager.read_json("nonexistent.json")
    
    def test_update_json_success(self):
        """Test updating existing JSON file"""
        original_data = {"old": "data"}
        new_data = {"new": "data", "updated": True}
        
        self.file_manager.create_json("test.json", original_data)
        result = self.file_manager.update_json("test.json", new_data)
        
        assert result is True
        read_data = self.file_manager.read_json("test.json")
        assert read_data == new_data
    
    def test_update_json_file_not_found(self):
        """Test updating non-existent JSON file raises error"""
        with pytest.raises(FileNotFoundError):
            self.file_manager.update_json("nonexistent.json", {"data": "test"})
    
    def test_create_text_success(self):
        """Test creating a new text file"""
        test_content = "Hello, World!\nThis is a test."
        result = self.file_manager.create_text("test.txt", test_content)
        
        assert result is True
        assert self.file_manager.exists("test.txt") is True
        
        read_content = self.file_manager.read_text("test.txt")
        assert read_content == test_content
    
    def test_create_text_overwrite(self):
        """Test overwriting text file"""
        original = "Original content"
        new = "New content"
        
        self.file_manager.create_text("test.txt", original)
        self.file_manager.create_text("test.txt", new, overwrite=True)
        
        result = self.file_manager.read_text("test.txt")
        assert result == new
    
    def test_read_text_success(self):
        """Test reading text file"""
        test_content = "Test content\nWith multiple lines"
        self.file_manager.create_text("test.txt", test_content)
        
        result = self.file_manager.read_text("test.txt")
        assert result == test_content
    
    def test_read_text_file_not_found(self):
        """Test reading non-existent text file raises error"""
        with pytest.raises(FileNotFoundError):
            self.file_manager.read_text("nonexistent.txt")
    
    def test_update_text_success(self):
        """Test updating text file"""
        original = "Original"
        updated = "Updated content"
        
        self.file_manager.create_text("test.txt", original)
        result = self.file_manager.update_text("test.txt", updated)
        
        assert result is True
        assert self.file_manager.read_text("test.txt") == updated
    
    def test_append_text_success(self):
        """Test appending to text file"""
        initial = "Initial content"
        appended = "\nAppended content"
        
        self.file_manager.create_text("test.txt", initial)
        result = self.file_manager.append_text("test.txt", appended)
        
        assert result is True
        final_content = self.file_manager.read_text("test.txt")
        assert final_content == initial + appended
    
    def test_append_text_file_not_found(self):
        """Test appending to non-existent text file raises error"""
        with pytest.raises(FileNotFoundError):
            self.file_manager.append_text("nonexistent.txt", "content")
    
    def test_create_binary_success(self):
        """Test creating a new binary file"""
        test_data = b'\x00\x01\x02\x03\xFF\xFE'
        result = self.file_manager.create_binary("test.bin", test_data)
        
        assert result is True
        assert self.file_manager.exists("test.bin") is True
        
        read_data = self.file_manager.read_binary("test.bin")
        assert read_data == test_data
    
    def test_create_binary_overwrite(self):
        """Test overwriting binary file"""
        original = b'\x00\x01'
        new = b'\xFF\xFE'
        
        self.file_manager.create_binary("test.bin", original)
        self.file_manager.create_binary("test.bin", new, overwrite=True)
        
        result = self.file_manager.read_binary("test.bin")
        assert result == new
    
    def test_read_binary_success(self):
        """Test reading binary file"""
        test_data = b'\x48\x65\x6C\x6C\x6F'  # "Hello" in bytes
        self.file_manager.create_binary("test.bin", test_data)
        
        result = self.file_manager.read_binary("test.bin")
        assert result == test_data
    
    def test_read_binary_file_not_found(self):
        """Test reading non-existent binary file raises error"""
        with pytest.raises(FileNotFoundError):
            self.file_manager.read_binary("nonexistent.bin")
    
    def test_update_binary_success(self):
        """Test updating binary file"""
        original = b'\x00\x01'
        updated = b'\xFF\xFE\xFD'
        
        self.file_manager.create_binary("test.bin", original)
        result = self.file_manager.update_binary("test.bin", updated)
        
        assert result is True
        assert self.file_manager.read_binary("test.bin") == updated
    
    def test_append_binary_success(self):
        """Test appending to binary file"""
        initial = b'\x00\x01'
        appended = b'\x02\x03'
        
        self.file_manager.create_binary("test.bin", initial)
        result = self.file_manager.append_binary("test.bin", appended)
        
        assert result is True
        final_data = self.file_manager.read_binary("test.bin")
        assert final_data == initial + appended
    
    def test_append_binary_file_not_found(self):
        """Test appending to non-existent binary file raises error"""
        with pytest.raises(FileNotFoundError):
            self.file_manager.append_binary("nonexistent.bin", b'\x00')
    
    def test_delete_success(self):
        """Test deleting a file"""
        self.file_manager.create_text("test.txt", "content")
        assert self.file_manager.exists("test.txt") is True
        
        result = self.file_manager.delete("test.txt")
        
        assert result is True
        assert self.file_manager.exists("test.txt") is False
    
    def test_delete_file_not_found(self):
        """Test deleting non-existent file raises error"""
        with pytest.raises(FileNotFoundError):
            self.file_manager.delete("nonexistent.txt")
    
    def test_exists_true(self):
        """Test exists returns True for existing file"""
        self.file_manager.create_text("test.txt", "content")
        assert self.file_manager.exists("test.txt") is True
    
    def test_exists_false(self):
        """Test exists returns False for non-existent file"""
        assert self.file_manager.exists("nonexistent.txt") is False
    
    def test_exists_directory_returns_false(self):
        """Test exists returns False for directories"""
        dir_path = Path(self.temp_dir) / "subdir"
        dir_path.mkdir()
        assert self.file_manager.exists("subdir") is False
    
    def test_list_files_default_pattern(self):
        """Test listing JSON files with default pattern"""
        self.file_manager.create_json("file1.json", {})
        self.file_manager.create_json("file2.json", {})
        self.file_manager.create_text("file3.txt", "")
        
        files = self.file_manager.list_files()
        file_names = [f.name for f in files]
        
        assert len(files) == 2
        assert "file1.json" in file_names
        assert "file2.json" in file_names
        assert "file3.txt" not in file_names
    
    def test_list_files_custom_pattern(self):
        """Test listing files with custom pattern"""
        self.file_manager.create_text("file1.txt", "")
        self.file_manager.create_text("file2.txt", "")
        self.file_manager.create_json("file3.json", {})
        
        files = self.file_manager.list_files(pattern="*.txt")
        file_names = [f.name for f in files]
        
        assert len(files) == 2
        assert "file1.txt" in file_names
        assert "file2.txt" in file_names
    
    def test_list_files_recursive(self):
        """Test listing files recursively"""
        self.file_manager.create_json("root.json", {})
        self.file_manager.create_json("subdir/nested.json", {})
        self.file_manager.create_json("subdir/deeper/deep.json", {})
        
        files = self.file_manager.list_files(recursive=True)
        file_names = [f.name for f in files]
        
        assert len(files) == 3
        assert "root.json" in file_names
        assert "nested.json" in file_names
        assert "deep.json" in file_names
    
    def test_list_files_non_recursive(self):
        """Test listing files non-recursively"""
        self.file_manager.create_json("root.json", {})
        self.file_manager.create_json("subdir/nested.json", {})
        
        files = self.file_manager.list_files(recursive=False)
        file_names = [f.name for f in files]
        
        assert len(files) == 1
        assert "root.json" in file_names
        assert "nested.json" not in file_names
    
    def test_list_files_directory_not_found(self):
        """Test listing files in non-existent directory raises error"""
        with pytest.raises(FileNotFoundError):
            self.file_manager.list_files(directory="nonexistent_dir")
    
    def test_absolute_path_handling(self):
        """Test handling of absolute paths"""
        temp_file = Path(self.temp_dir) / "absolute.json"
        test_data = {"absolute": True}
        
        result = self.file_manager.create_json(str(temp_file), test_data)
        
        assert result is True
        assert temp_file.exists() is True
    
    def test_relative_path_handling(self):
        """Test handling of relative paths"""
        test_data = {"relative": True}
        result = self.file_manager.create_json("relative.json", test_data)
        
        assert result is True
        expected_path = Path(self.temp_dir) / "relative.json"
        assert expected_path.exists() is True