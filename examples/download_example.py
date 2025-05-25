#!/usr/bin/env python3
"""
Example script demonstrating how to use UniCache to download and cache a large file.
"""

import os
import sys
import signal
import time
import tempfile
from pathlib import Path
from unicache import Cache, download_file_fast, get_download_info
from unicache.cache_utils import download_and_store

def download_file(url, output_path, use_fast_download=True):
    """Download a file from a URL to a local path with progress bar."""
    if use_fast_download:
        return download_file_fast(url, output_path)
    else:
        # Fallback to requests-only download
        return download_file_fast(url, output_path, use_hf_transfer=False)

def setup_signal_handlers():
    """Setup signal handlers for graceful interruption."""
    def signal_handler(signum, frame):
        print("\n\nDownload interrupted by user (Ctrl+C)")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)

def main():
    setup_signal_handlers()
    
    # Show download capabilities
    download_info = get_download_info()
    print("UniCache Download Example")
    print("=" * 50)
    print(f"Available download methods: {', '.join(download_info['methods'])}")
    print(f"hf-transfer available: {download_info['hf_transfer_available']}")
    if download_info['hf_transfer_available']:
        print(f"hf-transfer version: {download_info.get('hf_transfer_version', 'unknown')}")
    print()
    
    # Create a cache with 1MB block size
    cache_dir = Path.home() / ".unicache"
    block_size = 1024 * 1024  # 1MB blocks
    cache = Cache(block_size=block_size, cache_dir=str(cache_dir))
    
    # URL for a large test file (Hugging Face model file)
    url = "https://huggingface.co/Qwen/Qwen3-0.6B/resolve/main/model.safetensors"
    
    # Create a temporary directory for our downloads
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        print("Method 1: Download then store separately")
        print("-" * 40)
        
        # Download file to temporary location using fast download
        print(f"Downloading file from {url}")
        download_path = temp_dir_path / "downloaded_file.bin"
        start_download = time.time()
        download_file(url, download_path)
        end_download = time.time()
        print(f"Download completed in {end_download - start_download:.2f} seconds")
        
        # Store the file in the cache
        print("\nStoring file in cache...")
        start_time = time.time()
        file_id = cache.store_file(str(download_path))
        end_time = time.time()
        print(f"File stored with ID: {file_id}")
        print(f"Storage time: {end_time - start_time:.2f} seconds")
        
        print(f"\nTotal time (download + store): {end_time - start_download:.2f} seconds")
        
        print("\n" + "=" * 50)
        print("Method 2: Integrated download and store")
        print("-" * 40)
        
        # Demonstrate integrated download and store
        start_integrated = time.time()
        integrated_file_id, temp_file = download_and_store(
            cache=cache,
            url=url,
            file_id="integrated_download_test",
            use_hf_transfer=download_info['hf_transfer_available'],
            max_files=8
        )
        end_integrated = time.time()
        print(f"Integrated download and store completed in {end_integrated - start_integrated:.2f} seconds")
        print(f"File stored with ID: {integrated_file_id}")
        
        # Get cache statistics after both downloads
        blocks, files, stored_size, logical_size = cache.get_stats()
        print(f"\nCache statistics after both downloads:")
        print(f"Total blocks: {blocks}")
        print(f"Total files: {files}")
        print(f"Physical storage used: {stored_size / (1024**2):.2f} MB")
        print(f"Logical storage: {logical_size / (1024**2):.2f} MB")
        dedup_ratio = logical_size / stored_size if stored_size > 0 else 1.0
        print(f"Deduplication ratio: {dedup_ratio:.2f}x")
        
        print("\n" + "=" * 50)
        print("Testing file retrieval and integrity")
        print("-" * 40)
        
        # Retrieve the file from cache
        print("Retrieving file from cache...")
        output_path = temp_dir_path / "retrieved_file.bin"
        start_time = time.time()
        cache.retrieve_file(file_id, str(output_path))
        end_time = time.time()
        print(f"File retrieved to: {output_path}")
        print(f"Retrieval time: {end_time - start_time:.2f} seconds")
        
        # Verify file integrity
        original_size = os.path.getsize(download_path)
        retrieved_size = os.path.getsize(output_path)
        print(f"\nOriginal file size: {original_size / (1024**2):.2f} MB")
        print(f"Retrieved file size: {retrieved_size / (1024**2):.2f} MB")
        
        if original_size == retrieved_size:
            print("✅ File sizes match!")
        else:
            print("❌ File sizes do not match!")
        
        print("\n" + "=" * 50)
        print("Performance comparison summary")
        print("-" * 40)
        
        download_method = "hf-transfer" if download_info['hf_transfer_available'] else "requests"
        print(f"Download method used: {download_method}")
        print(f"Separate download + store: {end_time - start_download:.2f}s")
        print(f"Integrated download + store: {end_integrated - start_integrated:.2f}s")
        print(f"File retrieval: {end_time - start_time:.2f}s")
        print(f"Final deduplication ratio: {dedup_ratio:.2f}x")
        
        # Clean up (optional)
        # cache.remove_file(file_id)
        # cache.remove_file(duplicate_id)

if __name__ == "__main__":
    main() 