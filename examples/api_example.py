#!/usr/bin/env python3
"""
Example demonstrating the high-level UniCache API - painless file caching.

This example shows how to use the new high-level API for:
- Downloading files from URLs
- Adding local files to cache
- Retrieving cached files
- Managing the cache

The high-level API is designed to be effortless and intuitive.
"""

import os
import tempfile
from pathlib import Path
import time

# Import the high-level API
from unicache.api import UniCache, download, add_file, get_file, cache_stats


def create_sample_file(path: Path, content: str) -> Path:
    """Create a sample file for testing."""
    path.write_text(content)
    return path


def main():
    print("UniCache High-Level API Example")
    print("=" * 50)
    
    # Create a temporary directory for our examples
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        print("\n1. Using the UniCache class (recommended for multiple operations)")
        print("-" * 60)
        
        # Create a cache instance
        with UniCache(cache_dir=temp_dir_path / "cache") as cache:
            
            # Show download capabilities
            download_info = cache.download_info()
            print(f"Fast downloads available: {download_info['hf_transfer_available']}")
            
            # Example 1: Download a file from URL
            print("\n📥 Downloading a file from URL...")
            try:
                url = "https://huggingface.co/microsoft/DialoGPT-small/resolve/main/config.json"
                file_id = cache.download(url)
                print(f"✅ Downloaded and cached with ID: {file_id}")
            except Exception as e:
                print(f"❌ Download failed: {e}")
                # Create a local file instead for the demo
                sample_file = temp_dir_path / "sample.txt"
                create_sample_file(sample_file, "This is a sample file for testing.")
                file_id = cache.add(sample_file)
                print(f"✅ Added local file instead with ID: {file_id}")
            
            # Example 2: Add a local file to cache
            print("\n📁 Adding local files to cache...")
            
            # Create some test files
            test_files = []
            for i in range(3):
                test_file = temp_dir_path / f"test_file_{i}.txt"
                content = f"This is test file {i}\n" + "Sample content " * 100
                create_sample_file(test_file, content)
                test_files.append(test_file)
            
            # Add files to cache
            file_ids = []
            for test_file in test_files:
                file_id = cache.add(test_file)
                file_ids.append(file_id)
                print(f"✅ Added {test_file.name} with ID: {file_id}")
            
            # Example 3: Create a duplicate file to show deduplication
            print("\n🔄 Testing deduplication...")
            duplicate_file = temp_dir_path / "duplicate.txt"
            create_sample_file(duplicate_file, "This is test file 0\n" + "Sample content " * 100)
            
            duplicate_id = cache.add(duplicate_file)
            print(f"✅ Added duplicate file with ID: {duplicate_id}")
            
            # Show cache statistics
            stats = cache.stats()
            print(f"\n📊 Cache Statistics:")
            print(f"   Total files: {stats['total_files']}")
            print(f"   Total blocks: {stats['total_blocks']}")
            print(f"   Physical size: {stats['physical_size_mb']:.2f} MB")
            print(f"   Logical size: {stats['logical_size_mb']:.2f} MB")
            print(f"   Deduplication ratio: {stats['deduplication_ratio']:.2f}x")
            print(f"   Space saved: {stats['space_saved_mb']:.2f} MB")
            
            # Example 4: Retrieve files from cache
            print("\n📤 Retrieving files from cache...")
            
            # Get a file to a temporary location
            retrieved_path = cache.get(file_ids[0])
            print(f"✅ Retrieved file to: {retrieved_path}")
            print(f"   File size: {retrieved_path.stat().st_size} bytes")
            
            # Copy a file to a specific location
            output_path = temp_dir_path / "retrieved_copy.txt"
            cache.copy_to(file_ids[1], output_path)
            print(f"✅ Copied file to: {output_path}")
            
            # Example 5: Check if files exist
            print("\n🔍 Checking file existence...")
            for i, file_id in enumerate(file_ids[:2]):
                exists = cache.exists(file_id)
                print(f"   File {i}: {file_id} - {'✅ exists' if exists else '❌ not found'}")
            
            # Example 6: Remove a file
            print("\n🗑️  Removing a file from cache...")
            removed = cache.remove(file_ids[-1])
            print(f"   {'✅ Removed' if removed else '❌ Failed to remove'} file: {file_ids[-1]}")
            
            # Show updated stats
            stats = cache.stats()
            print(f"\n📊 Updated Cache Statistics:")
            print(f"   Total files: {stats['total_files']}")
            print(f"   Deduplication ratio: {stats['deduplication_ratio']:.2f}x")
        
        print("\n" + "=" * 50)
        print("2. Using convenience functions (for quick operations)")
        print("-" * 60)
        
        cache_dir = temp_dir_path / "quick_cache"
        
        # Quick download
        print("\n📥 Quick download...")
        try:
            url = "https://huggingface.co/microsoft/DialoGPT-small/resolve/main/tokenizer.json"
            file_id = download(url, cache_dir=cache_dir)
            print(f"✅ Quick download completed: {file_id}")
        except Exception as e:
            print(f"❌ Quick download failed: {e}")
            # Use a local file instead
            quick_file = temp_dir_path / "quick_test.txt"
            create_sample_file(quick_file, "Quick test content")
            file_id = add_file(quick_file, cache_dir=cache_dir)
            print(f"✅ Quick add completed: {file_id}")
        
        # Quick retrieval
        print("\n📤 Quick retrieval...")
        output_file = temp_dir_path / "quick_output.txt"
        retrieved_path = get_file(file_id, output_file, cache_dir=cache_dir)
        print(f"✅ Quick retrieval completed: {retrieved_path}")
        
        # Quick stats
        print("\n📊 Quick stats...")
        stats = cache_stats(cache_dir=cache_dir)
        print(f"   Files: {stats['total_files']}, Blocks: {stats['total_blocks']}")
        print(f"   Size: {stats['physical_size_mb']:.2f} MB")
        
        print("\n" + "=" * 50)
        print("3. Advanced usage patterns")
        print("-" * 60)
        
        # Using custom file IDs
        print("\n🏷️  Using custom file IDs...")
        with UniCache(cache_dir=temp_dir_path / "custom_cache") as cache:
            custom_file = temp_dir_path / "custom.txt"
            create_sample_file(custom_file, "Custom content")
            
            custom_id = cache.add(custom_file, file_id="my_custom_file")
            print(f"✅ Added with custom ID: {custom_id}")
            
            # Verify we can retrieve it
            if cache.exists("my_custom_file"):
                print("✅ Custom ID works correctly")
            
        # Using copy_file option
        print("\n📋 Using copy_file option...")
        with UniCache(cache_dir=temp_dir_path / "copy_cache") as cache:
            original_file = temp_dir_path / "original.txt"
            create_sample_file(original_file, "Original content")
            
            # Add without copying (default)
            file_id1 = cache.add(original_file, copy_file=False)
            
            # Add with copying (preserves original)
            file_id2 = cache.add(original_file, copy_file=True)
            
            print(f"✅ Added without copy: {file_id1}")
            print(f"✅ Added with copy: {file_id2}")
        
        print("\n" + "=" * 50)
        print("✨ High-level API demo completed!")
        print("\nKey benefits of the high-level API:")
        print("• 🎯 Simple, intuitive interface")
        print("• 🔄 Automatic deduplication")
        print("• 🚀 Fast downloads with hf-transfer")
        print("• 🧹 Automatic cleanup")
        print("• 📊 Easy statistics")
        print("• 🛡️  Error handling")
        print("• 🔧 Context manager support")


if __name__ == "__main__":
    main() 