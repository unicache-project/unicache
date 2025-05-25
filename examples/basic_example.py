#!/usr/bin/env python3
"""
Basic example demonstrating UniCache functionality with local files.
"""

import os
import sys
from pathlib import Path
import tempfile
import random
from unicache import Cache

def create_test_file(path, size_mb, pattern_type="random"):
    """Create a test file with specified size and pattern."""
    print(f"Creating test file: {path} ({size_mb} MB)")
    
    chunk_size = 1024 * 1024  # 1MB chunks
    with open(path, "wb") as f:
        for _ in range(size_mb):
            if pattern_type == "random":
                # Random data
                data = random.randbytes(chunk_size)
            elif pattern_type == "zero":
                # All zeros
                data = b"\x00" * chunk_size
            elif pattern_type == "repeating":
                # Repeating pattern
                data = b"abcdefghijklmnopqrstuvwxyz" * (chunk_size // 26)
            else:
                raise ValueError(f"Unknown pattern type: {pattern_type}")
                
            f.write(data)
    
    print(f"Created {path} ({os.path.getsize(path) / 1024 / 1024:.2f} MB)")
    return path

def main():
    # Create a temporary directory for our test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        # Create a cache with 64KB block size
        cache_dir = temp_dir_path / "cache"
        block_size = 64 * 1024  # 64KB blocks
        cache = Cache(block_size=block_size, cache_dir=str(cache_dir))
        
        # Create a few test files with different patterns
        files = [
            create_test_file(temp_dir_path / "random1.bin", 5, "random"),
            create_test_file(temp_dir_path / "random2.bin", 5, "random"),
            create_test_file(temp_dir_path / "zeros.bin", 10, "zero"),
            create_test_file(temp_dir_path / "repeated.bin", 10, "repeating"),
        ]
        
        # Store all files in the cache
        print("\nStoring files in cache...")
        file_ids = []
        for file_path in files:
            file_id = cache.store_file(str(file_path))
            file_ids.append(file_id)
            print(f"Stored {file_path.name} with ID: {file_id}")
        
        # Print cache statistics
        blocks, files_count, stored_size, logical_size = cache.get_stats()
        print(f"\nCache statistics:")
        print(f"Total blocks: {blocks}")
        print(f"Total files: {files_count}")
        print(f"Physical storage used: {stored_size / (1024**2):.2f} MB")
        print(f"Logical storage: {logical_size / (1024**2):.2f} MB")
        dedup_ratio = logical_size / stored_size if stored_size > 0 else 1.0
        print(f"Deduplication ratio: {dedup_ratio:.2f}x")
        
        # Retrieve a file from the cache
        file_id_to_retrieve = file_ids[0]
        output_path = temp_dir_path / "retrieved_file.bin"
        print(f"\nRetrieving file with ID {file_id_to_retrieve}...")
        cache.retrieve_file(file_id_to_retrieve, str(output_path))
        print(f"Retrieved to: {output_path} ({os.path.getsize(output_path) / 1024 / 1024:.2f} MB)")
        
        # Create duplicate content to demonstrate deduplication
        print("\nCreating a file with duplicate content...")
        duplicate_file = temp_dir_path / "duplicate_content.bin"
        
        # Create a file that has some duplicate content from previous files
        with open(duplicate_file, "wb") as out_f:
            # Add content from zeros.bin (first 5MB)
            with open(temp_dir_path / "zeros.bin", "rb") as in_f:
                out_f.write(in_f.read(5 * 1024 * 1024))
                
            # Add content from repeated.bin (first 5MB) 
            with open(temp_dir_path / "repeated.bin", "rb") as in_f:
                out_f.write(in_f.read(5 * 1024 * 1024))
        
        print(f"Created duplicate file: {duplicate_file} ({os.path.getsize(duplicate_file) / 1024 / 1024:.2f} MB)")
        
        # Store the duplicate file
        duplicate_id = cache.store_file(str(duplicate_file))
        print(f"Stored duplicate file with ID: {duplicate_id}")
        
        # Check statistics again to see deduplication in action
        blocks, files_count, stored_size, logical_size = cache.get_stats()
        print(f"\nCache statistics after storing duplicate content:")
        print(f"Total blocks: {blocks}")
        print(f"Total files: {files_count}")
        print(f"Physical storage used: {stored_size / (1024**2):.2f} MB")
        print(f"Logical storage: {logical_size / (1024**2):.2f} MB")
        dedup_ratio = logical_size / stored_size if stored_size > 0 else 1.0
        print(f"Deduplication ratio: {dedup_ratio:.2f}x")
        
        # Remove a file and check stats again
        print("\nRemoving a file from the cache...")
        cache.remove_file(file_ids[0])
        
        blocks, files_count, stored_size, logical_size = cache.get_stats()
        print(f"Cache statistics after removal:")
        print(f"Total blocks: {blocks}")
        print(f"Total files: {files_count}")
        print(f"Physical storage used: {stored_size / (1024**2):.2f} MB")
        print(f"Logical storage: {logical_size / (1024**2):.2f} MB")

if __name__ == "__main__":
    main() 