import os
import hashlib
import glob
from pathlib import Path
from typing import List, Dict, Optional, Set
import mimetypes
from datetime import datetime

class Scanner:
    def __init__(self, config: Dict):
        self.config = config
        self.supported_extensions = set()
        for extensions in config['scanner']['extensions'].values():
            self.supported_extensions.update(extensions)
    
    def scan(self, directory: str) -> List[Dict]:
        """Scan directory for code files."""
        directory = Path(directory).expanduser()
        files = self._find_files(directory)
        results = []
        
        for file_path in files:
            try:
                file_info = self._process_file(file_path)
                if file_info:
                    results.append(file_info)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        return results
    
    def _find_files(self, directory: Path) -> List[Path]:
        """Find all supported files in directory."""
        files = []
        exclude_patterns = self.config['scanner']['exclude']
        
        for pattern in ['**/*']:
            for file_path in directory.glob(pattern):
                if file_path.is_file() and self._is_supported(file_path):
                    # Check if file should be excluded
                    if not any(exc in str(file_path) for exc in exclude_patterns):
                        files.append(file_path)
        
        return files
    
    def _is_supported(self, file_path: Path) -> bool:
        """Check if file extension is supported."""
        return file_path.suffix.lower() in self.supported_extensions
    
    def _process_file(self, file_path: Path) -> Optional[Dict]:
        """Process a single file."""
        stats = file_path.stat()
        
        # Skip large files
        if stats.st_size > self.config['scanner']['max_file_size']:
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Skip binary files
            return None
        
        file_hash = hashlib.md5(content.encode()).hexdigest()
        
        return {
            'path': str(file_path),
            'name': file_path.name,
            'type': self._detect_type(file_path),
            'language': self._detect_language(file_path),
            'content': content,
            'hash': file_hash,
            'size': stats.st_size,
            'last_modified': int(stats.st_mtime * 1000)
        }
    
    def _detect_type(self, file_path: Path) -> str:
        """Detect file type."""
        name = file_path.name
        suffix = file_path.suffix.lower()
        
        if suffix in ['.sh', '.bash', '.zsh']:
            return 'script'
        elif suffix in ['.py', '.js', '.ts']:
            return 'module'
        elif name == 'Dockerfile':
            return 'config'
        elif name == 'Makefile':
            return 'build'
        elif name in ['package.json', 'pyproject.toml']:
            return 'manifest'
        
        return 'file'
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language."""
        suffix = file_path.suffix.lower()
        
        language_map = {
            '.py': 'python',
            '.pyw': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.sh': 'shell',
            '.bash': 'bash',
            '.zsh': 'zsh'
        }
        
        return language_map.get(suffix, 'unknown')
