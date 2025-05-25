#!/usr/bin/env python3
"""
Benchmark script for UniCache performance with different block sizes.
"""

import os
import time
import tempfile
from pathlib import Path
import random
import shutil
from unicache import Cache

def create_test_file(path, size_mb, pattern_type="random"):
    """Create a test file with specified size and pattern."""
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
    
    return path

def benchmark_block_size(block_size, test_files, temp_dir):
    """Benchmark cache performance with a specific block size."""
    cache_dir = temp_dir / f"cache_{block_size}"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    
    # Initialize cache with the given block size
    cache = Cache(block_size=block_size, cache_dir=str(cache_dir))
    
    # Measure store performance
    start_time = time.time()
    file_ids = []
    for file_path in test_files:
        file_id = cache.store_file(str(file_path))
        file_ids.append(file_id)
    store_time = time.time() - start_time
    
    # Get cache statistics
    blocks, files_count, stored_size, logical_size = cache.get_stats()
    dedup_ratio = logical_size / stored_size if stored_size > 0 else 1.0
    
    # Measure retrieval performance
    output_dir = temp_dir / f"retrieved_{block_size}"
    output_dir.mkdir(exist_ok=True)
    
    start_time = time.time()
    for i, file_id in enumerate(file_ids):
        output_path = output_dir / f"file_{i}.bin"
        cache.retrieve_file(file_id, str(output_path))
    retrieve_time = time.time() - start_time
    
    return {
        "block_size": block_size,
        "store_time": store_time,
        "retrieve_time": retrieve_time,
        "blocks": blocks,
        "dedup_ratio": dedup_ratio,
        "stored_size_mb": stored_size / (1024**2),
        "logical_size_mb": logical_size / (1024**2),
    }

def main():
    # Create a temporary directory for our test files
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        
        # Create test files with different patterns
        print("Creating test files...")
        test_file_size = 50  # MB per file
        test_files = [
            create_test_file(temp_dir / "random1.bin", test_file_size, "random"),
            create_test_file(temp_dir / "random2.bin", test_file_size, "random"),
            create_test_file(temp_dir / "zeros.bin", test_file_size, "zero"),
            create_test_file(temp_dir / "repeated.bin", test_file_size, "repeating"),
        ]
        
        # Create a file with mixed content from other files
        mixed_file = temp_dir / "mixed.bin"
        with open(mixed_file, "wb") as out_f:
            # Add content from all other files (10MB from each)
            for file_path in test_files:
                with open(file_path, "rb") as in_f:
                    out_f.write(in_f.read(10 * 1024 * 1024))
        test_files.append(mixed_file)
        
        print(f"Created {len(test_files)} test files, total size: {test_file_size * 4 + 40:.2f} MB")
        
        # Test different block sizes
        block_sizes = [
            4 * 1024,       # 4KB
            16 * 1024,      # 16KB
            64 * 1024,      # 64KB
            256 * 1024,     # 256KB
            1024 * 1024,    # 1MB
            4 * 1024 * 1024 # 4MB
        ]
        
        results = []
        for block_size in block_sizes:
            print(f"\nBenchmarking with block size: {block_size / 1024:.1f} KB")
            result = benchmark_block_size(block_size, test_files, temp_dir)
            results.append(result)
            print(f"  Store time: {result['store_time']:.2f}s")
            print(f"  Retrieve time: {result['retrieve_time']:.2f}s")
            print(f"  Blocks: {result['blocks']}")
            print(f"  Dedup ratio: {result['dedup_ratio']:.2f}x")
        
        # Print summary
        print("\nSummary:")
        print(f"{'Block Size':15} | {'Store Time':10} | {'Retrieve Time':13} | {'Blocks':8} | {'Dedup Ratio':11}")
        print("-" * 70)
        for result in results:
            print(f"{result['block_size']/1024:8.1f} KB    | "
                  f"{result['store_time']:8.2f}s  | "
                  f"{result['retrieve_time']:11.2f}s  | "
                  f"{result['blocks']:8d} | "
                  f"{result['dedup_ratio']:9.2f}x")

if __name__ == "__main__":
    main() 