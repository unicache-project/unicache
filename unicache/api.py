#!/usr/bin/env python3
"""
High-level Python API for UniCache - painless, effortless file caching.

This module provides a simple, intuitive interface for:
- Downloading files from URLs and caching them
- Adding local files to the cache
- Retrieving cached files
- Managing the cache

Example usage:
    from unicache.api import UniCache
    
    # Create a cache instance
    cache = UniCache()
    
    # Download and cache a file
    file_id = cache.download("https://example.com/large_file.bin")
    
    # Add a local file to cache
    file_id = cache.add("./my_file.txt")
    
    # Get a file from cache (returns path to cached file)
    file_path = cache.get(file_id)
    
    # Copy a file from cache to a specific location
    cache.copy_to(file_id, "./output_file.txt")
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Union, Dict, Any, List, Tuple
from urllib.parse import urlparse
import hashlib
import time

from unicache import Cache as LowLevelCache, download_file_fast, get_download_info, DownloadError
from unicache.cache_utils import download_and_store


class UniCacheError(Exception):
    """Base exception for UniCache API errors."""
    pass


class FileNotFoundError(UniCacheError):
    """Raised when a requested file is not found in the cache."""
    pass


class DownloadFailedError(UniCacheError):
    """Raised when a download operation fails."""
    pass


class UniCache:
    """
    High-level interface for UniCache - effortless file caching.
    
    This class provides a simple, intuitive API for downloading files,
    adding local files to cache, and retrieving cached files.
    
    Args:
        cache_dir: Directory to store cache files (default: ~/.unicache)
        block_size: Block size for deduplication (default: 1MB)
        auto_cleanup: Whether to automatically clean up temporary files (default: True)
    """
    
    def __init__(
        self,
        cache_dir: Optional[Union[str, Path]] = None,
        block_size: int = 1024 * 1024,  # 1MB
        auto_cleanup: bool = True
    ):
        if cache_dir is None:
            cache_dir = Path.home() / ".unicache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.block_size = block_size
        self.auto_cleanup = auto_cleanup
        
        # Initialize the low-level cache
        self._cache = LowLevelCache(block_size=block_size, cache_dir=str(self.cache_dir))
        
        # Track temporary files for cleanup
        self._temp_files = set()
    
    def download(
        self,
        url: str,
        file_id: Optional[str] = None,
        use_fast_download: bool = True,
        max_connections: int = 8,
        progress: bool = True
    ) -> str:
        """
        Download a file from a URL and store it in the cache.
        
        Args:
            url: URL to download from
            file_id: Custom ID for the file (auto-generated if None)
            use_fast_download: Whether to use hf-transfer for fast downloads
            max_connections: Number of parallel connections for fast downloads
            progress: Whether to show download progress
            
        Returns:
            File ID that can be used to retrieve the file
            
        Raises:
            DownloadFailedError: If the download fails
        """
        try:
            # Generate file ID if not provided
            if file_id is None:
                file_id = self._generate_file_id(url)
            
            # Check if file already exists in cache
            if self._file_exists(file_id):
                return file_id
            
            # Download and store the file
            actual_file_id, temp_path = download_and_store(
                cache=self._cache,
                url=url,
                file_id=file_id,
                use_hf_transfer=use_fast_download,
                max_files=max_connections
            )
            
            # Clean up temporary file if auto_cleanup is enabled
            if self.auto_cleanup and temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            return actual_file_id
            
        except Exception as e:
            raise DownloadFailedError(f"Failed to download {url}: {e}")
    
    def add(
        self,
        file_path: Union[str, Path],
        file_id: Optional[str] = None,
        copy_file: bool = False
    ) -> str:
        """
        Add a local file to the cache.
        
        Args:
            file_path: Path to the local file
            file_id: Custom ID for the file (auto-generated if None)
            copy_file: Whether to copy the file before adding (preserves original)
            
        Returns:
            File ID that can be used to retrieve the file
            
        Raises:
            FileNotFoundError: If the local file doesn't exist
            UniCacheError: If storing the file fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Local file not found: {file_path}")
        
        try:
            # Generate file ID if not provided
            if file_id is None:
                file_id = self._generate_file_id_from_path(file_path)
            
            # Check if file already exists in cache
            if self._file_exists(file_id):
                return file_id
            
            # Copy file to temporary location if requested
            if copy_file:
                temp_dir = self.cache_dir / "temp"
                temp_dir.mkdir(exist_ok=True)
                temp_path = temp_dir / f"temp_{int(time.time())}_{file_path.name}"
                shutil.copy2(file_path, temp_path)
                file_to_store = temp_path
                if self.auto_cleanup:
                    self._temp_files.add(temp_path)
            else:
                file_to_store = file_path
            
            # Store the file in cache
            actual_file_id = self._cache.store_file(str(file_to_store), file_id)
            
            # Clean up temporary file if created
            if copy_file and self.auto_cleanup and temp_path.exists():
                try:
                    temp_path.unlink()
                    self._temp_files.discard(temp_path)
                except:
                    pass
            
            return actual_file_id
            
        except Exception as e:
            raise UniCacheError(f"Failed to add file {file_path}: {e}")
    
    def get(self, file_id: str, output_dir: Optional[Union[str, Path]] = None) -> Path:
        """
        Get a file from the cache and return its path.
        
        The file is extracted to a temporary location or specified directory.
        
        Args:
            file_id: ID of the file to retrieve
            output_dir: Directory to extract the file to (uses temp dir if None)
            
        Returns:
            Path to the retrieved file
            
        Raises:
            FileNotFoundError: If the file is not found in cache
        """
        if not self._file_exists(file_id):
            raise FileNotFoundError(f"File not found in cache: {file_id}")
        
        try:
            # Determine output location
            if output_dir is None:
                output_dir = self.cache_dir / "retrieved"
                output_dir.mkdir(exist_ok=True)
            else:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate a unique filename
            output_path = output_dir / f"{file_id}_{int(time.time())}"
            
            # Retrieve the file
            self._cache.retrieve_file(file_id, str(output_path))
            
            # Track for cleanup if needed
            if self.auto_cleanup:
                self._temp_files.add(output_path)
            
            return output_path
            
        except Exception as e:
            raise UniCacheError(f"Failed to retrieve file {file_id}: {e}")
    
    def copy_to(self, file_id: str, output_path: Union[str, Path]) -> Path:
        """
        Copy a file from the cache to a specific location.
        
        Args:
            file_id: ID of the file to retrieve
            output_path: Where to copy the file
            
        Returns:
            Path to the copied file
            
        Raises:
            FileNotFoundError: If the file is not found in cache
        """
        if not self._file_exists(file_id):
            raise FileNotFoundError(f"File not found in cache: {file_id}")
        
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Retrieve the file directly to the specified location
            self._cache.retrieve_file(file_id, str(output_path))
            
            return output_path
            
        except Exception as e:
            raise UniCacheError(f"Failed to copy file {file_id} to {output_path}: {e}")
    
    def remove(self, file_id: str) -> bool:
        """
        Remove a file from the cache.
        
        Args:
            file_id: ID of the file to remove
            
        Returns:
            True if the file was removed, False if it wasn't found
        """
        try:
            self._cache.remove_file(file_id)
            return True
        except:
            return False
    
    def exists(self, file_id: str) -> bool:
        """
        Check if a file exists in the cache.
        
        Args:
            file_id: ID of the file to check
            
        Returns:
            True if the file exists, False otherwise
        """
        return self._file_exists(file_id)
    
    def list_files(self) -> List[str]:
        """
        List all file IDs in the cache.
        
        Returns:
            List of file IDs
        """
        # This is a limitation of the current low-level API
        # We can't easily list files without accessing internal state
        # For now, return an empty list and suggest using stats()
        return []
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        blocks, files, stored_size, logical_size = self._cache.get_stats()
        
        dedup_ratio = logical_size / stored_size if stored_size > 0 else 1.0
        space_saved = logical_size - stored_size
        
        return {
            "total_blocks": blocks,
            "total_files": files,
            "physical_size_bytes": stored_size,
            "logical_size_bytes": logical_size,
            "physical_size_mb": stored_size / (1024 * 1024),
            "logical_size_mb": logical_size / (1024 * 1024),
            "deduplication_ratio": dedup_ratio,
            "space_saved_bytes": space_saved,
            "space_saved_mb": space_saved / (1024 * 1024),
            "cache_directory": str(self.cache_dir),
            "block_size": self.block_size
        }
    
    def cleanup(self):
        """
        Clean up temporary files created by this instance.
        """
        for temp_file in list(self._temp_files):
            try:
                if temp_file.exists():
                    temp_file.unlink()
                self._temp_files.discard(temp_file)
            except:
                pass
    
    def download_info(self) -> Dict[str, Any]:
        """
        Get information about available download methods.
        
        Returns:
            Dictionary with download capability information
        """
        return get_download_info()
    
    def _file_exists(self, file_id: str) -> bool:
        """Check if a file exists in the cache by trying to get its stats."""
        try:
            # Try to retrieve to a temporary location to test existence
            with tempfile.NamedTemporaryFile() as temp_file:
                self._cache.retrieve_file(file_id, temp_file.name)
                return True
        except:
            return False
    
    def _generate_file_id(self, url: str) -> str:
        """Generate a file ID from a URL."""
        # Use URL and timestamp to create a unique ID
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        timestamp = int(time.time())
        
        # Try to extract filename from URL
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if filename:
            # Clean filename for use in ID
            clean_filename = "".join(c for c in filename if c.isalnum() or c in "._-")[:20]
            return f"{clean_filename}_{url_hash}_{timestamp}"
        else:
            return f"download_{url_hash}_{timestamp}"
    
    def _generate_file_id_from_path(self, file_path: Path) -> str:
        """Generate a file ID from a file path."""
        # Use file path, size, and modification time to create a unique ID
        try:
            stat = file_path.stat()
            path_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:16]
            size = stat.st_size
            mtime = int(stat.st_mtime)
            
            # Clean filename for use in ID
            clean_filename = "".join(c for c in file_path.name if c.isalnum() or c in "._-")[:20]
            return f"{clean_filename}_{path_hash}_{size}_{mtime}"
        except:
            # Fallback to simple hash
            path_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:16]
            timestamp = int(time.time())
            return f"file_{path_hash}_{timestamp}"
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temporary files."""
        if self.auto_cleanup:
            self.cleanup()


# Convenience functions for quick operations
def download(url: str, cache_dir: Optional[Union[str, Path]] = None, **kwargs) -> str:
    """
    Quick function to download a file and return its cache ID.
    
    Args:
        url: URL to download
        cache_dir: Cache directory (default: ~/.unicache)
        **kwargs: Additional arguments passed to UniCache.download()
        
    Returns:
        File ID for the downloaded file
    """
    with UniCache(cache_dir=cache_dir) as cache:
        return cache.download(url, **kwargs)


def add_file(file_path: Union[str, Path], cache_dir: Optional[Union[str, Path]] = None, **kwargs) -> str:
    """
    Quick function to add a local file to cache and return its ID.
    
    Args:
        file_path: Path to the local file
        cache_dir: Cache directory (default: ~/.unicache)
        **kwargs: Additional arguments passed to UniCache.add()
        
    Returns:
        File ID for the added file
    """
    with UniCache(cache_dir=cache_dir) as cache:
        return cache.add(file_path, **kwargs)


def get_file(file_id: str, output_path: Union[str, Path], cache_dir: Optional[Union[str, Path]] = None) -> Path:
    """
    Quick function to retrieve a file from cache to a specific location.
    
    Args:
        file_id: ID of the file to retrieve
        output_path: Where to copy the file
        cache_dir: Cache directory (default: ~/.unicache)
        
    Returns:
        Path to the retrieved file
    """
    with UniCache(cache_dir=cache_dir) as cache:
        return cache.copy_to(file_id, output_path)


def cache_stats(cache_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Quick function to get cache statistics.
    
    Args:
        cache_dir: Cache directory (default: ~/.unicache)
        
    Returns:
        Dictionary with cache statistics
    """
    with UniCache(cache_dir=cache_dir) as cache:
        return cache.stats() 