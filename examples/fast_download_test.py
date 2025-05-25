#!/usr/bin/env python3
"""
Simple test script for fast download functionality.
"""

import os
import sys
import signal
import time
import tempfile
from pathlib import Path
from unicache import Cache, download_file_fast, get_download_info
from unicache.cache_utils import download_and_store

def setup_signal_handlers():
    """Setup signal handlers for graceful interruption."""
    def signal_handler(signum, frame):
        print("\n\nTest interrupted by user (Ctrl+C)")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)

def main():
    setup_signal_handlers()
    
    print("UniCache Fast Download Test")
    print("=" * 40)
    
    # Show download capabilities
    download_info = get_download_info()
    print(f"hf-transfer available: {download_info['hf_transfer_available']}")
    if download_info['hf_transfer_available']:
        print(f"hf-transfer version: {download_info.get('hf_transfer_version', 'unknown')}")
    print()
    
    # Test URL - a small file for quick testing
    test_url = "https://huggingface.co/microsoft/DialoGPT-small/resolve/main/config.json"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        print("Test 1: Direct fast download")
        print("-" * 30)
        
        # Test direct download
        download_path = temp_dir_path / "test_file.json"
        start_time = time.time()
        
        try:
            result_path = download_file_fast(
                url=test_url,
                output_path=str(download_path),
                use_hf_transfer=True,
                max_files=4
            )
            end_time = time.time()
            
            file_size = os.path.getsize(result_path)
            print(f"✅ Download successful!")
            print(f"File size: {file_size / 1024:.2f} KB")
            print(f"Download time: {end_time - start_time:.2f} seconds")
            print(f"Speed: {file_size / (end_time - start_time) / 1024:.2f} KB/s")
            
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return
        
        print("\nTest 2: Download and store in cache")
        print("-" * 30)
        
        # Test integrated download and store
        cache = Cache(block_size=64*1024, cache_dir=str(temp_dir_path / "cache"))
        
        start_time = time.time()
        try:
            file_id, temp_file = download_and_store(
                cache=cache,
                url=test_url,
                file_id="fast_download_test",
                use_hf_transfer=True,
                max_files=4
            )
            end_time = time.time()
            
            print(f"✅ Download and store successful!")
            print(f"File ID: {file_id}")
            print(f"Total time: {end_time - start_time:.2f} seconds")
            
            # Get cache stats
            blocks, files, stored_size, logical_size = cache.get_stats()
            print(f"Cache blocks: {blocks}")
            print(f"Cache files: {files}")
            print(f"Storage used: {stored_size / 1024:.2f} KB")
            
        except Exception as e:
            print(f"❌ Download and store failed: {e}")
            return
        
        print("\nTest 3: Retrieve from cache")
        print("-" * 30)
        
        # Test retrieval
        retrieve_path = temp_dir_path / "retrieved_file.json"
        start_time = time.time()
        
        try:
            cache.retrieve_file(file_id, str(retrieve_path))
            end_time = time.time()
            
            retrieved_size = os.path.getsize(retrieve_path)
            print(f"✅ Retrieval successful!")
            print(f"Retrieved size: {retrieved_size / 1024:.2f} KB")
            print(f"Retrieval time: {end_time - start_time:.2f} seconds")
            
            # Verify integrity
            original_size = os.path.getsize(download_path)
            if original_size == retrieved_size:
                print("✅ File integrity verified!")
            else:
                print("❌ File integrity check failed!")
                
        except Exception as e:
            print(f"❌ Retrieval failed: {e}")
    
    print("\n" + "=" * 40)
    print("Fast download test completed!")

if __name__ == "__main__":
    main() 