#!/usr/bin/env python3
"""
Utility functions for the Cache class.
"""

import tempfile
import os
from pathlib import Path
from typing import Optional
from .downloader import download_file_fast, DownloadError


def download_and_store(
    cache,
    url: str,
    file_id: Optional[str] = None,
    use_hf_transfer: bool = True,
    max_files: int = 8,
    chunk_size: int = 1024 * 1024,
    headers: Optional[dict] = None,
    keep_temp_file: bool = False,
    temp_dir: Optional[str] = None
) -> tuple[str, str]:
    """
    Download a file and store it in the cache.
    
    Args:
        cache: Cache instance
        url: URL to download from
        file_id: Optional custom file ID
        use_hf_transfer: Whether to use hf-transfer if available
        max_files: Maximum parallel connections for hf-transfer
        chunk_size: Chunk size for download
        headers: Optional HTTP headers
        keep_temp_file: Whether to keep the temporary downloaded file
        temp_dir: Optional temporary directory to use
        
    Returns:
        Tuple of (file_id, temp_file_path)
        
    Raises:
        DownloadError: If download fails
    """
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, dir=temp_dir, suffix='.tmp') as temp_file:
        temp_path = temp_file.name
    
    try:
        # Download the file
        print(f"Downloading from {url}...")
        download_file_fast(
            url=url,
            output_path=temp_path,
            chunk_size=chunk_size,
            max_files=max_files,
            use_hf_transfer=use_hf_transfer,
            headers=headers
        )
        
        # Store in cache
        print("Storing in cache...")
        stored_file_id = cache.store_file(temp_path, file_id)
        
        # Clean up temp file unless requested to keep it
        if not keep_temp_file:
            try:
                os.unlink(temp_path)
                temp_path = None
            except:
                pass
        
        return stored_file_id, temp_path
        
    except KeyboardInterrupt:
        # Clean up temp file on interruption
        try:
            os.unlink(temp_path)
        except:
            pass
        raise KeyboardInterrupt("Download and store interrupted by user")
        
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except:
            pass
        raise DownloadError(f"Failed to download and store: {e}")


def download_to_cache_cli(
    cache_dir: str,
    block_size: int,
    url: str,
    file_id: Optional[str] = None,
    use_hf_transfer: bool = True,
    max_files: int = 8
) -> str:
    """
    CLI helper function to download and store a file.
    
    Args:
        cache_dir: Cache directory
        block_size: Block size for cache
        url: URL to download
        file_id: Optional file ID
        use_hf_transfer: Whether to use hf-transfer
        max_files: Max parallel connections
        
    Returns:
        File ID of stored file
    """
    from unicache import Cache
    
    cache = Cache(block_size=block_size, cache_dir=cache_dir)
    file_id, _ = download_and_store(
        cache=cache,
        url=url,
        file_id=file_id,
        use_hf_transfer=use_hf_transfer,
        max_files=max_files
    )
    return file_id 