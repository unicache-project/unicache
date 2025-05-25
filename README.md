# UniCache

A high-performance block-based deduplicated cache storage system with Python interface. UniCache eliminates duplicate data storage by breaking files into blocks and storing each unique block only once, delivering significant storage savings while maintaining fast access.

## Key Features

- **Block-based deduplication**: Automatically eliminates duplicate data across files
- **High-performance Rust core**: Performance-critical operations implemented in Rust
- **Dual API design**: Simple high-level API for ease of use, low-level API for advanced control
- **Fast downloads**: Integrated `hf-transfer` support for high-speed parallel downloads (>500MB/s)
- **Command-line interface**: Full CLI for scripting and automation
- **Cross-platform**: Works on Linux, macOS, and Windows

## Why UniCache?

### Storage Efficiency
Traditional file storage systems duplicate identical content across different files. UniCache's block-based deduplication can achieve **2-10x storage reduction** depending on your data patterns:

```
Traditional storage:  [File A: 100MB] [File B: 100MB] [File C: 100MB] = 300MB
UniCache:             [Unique blocks: 120MB] + [Metadata: 5MB] = 125MB
Savings:              58% less storage used
```

### Performance Benefits
- **Fixed-size blocks** enable efficient I/O operations
- **Sequential block storage** minimizes disk seeks
- **Memory-efficient design** keeps only metadata in RAM
- **Rust-powered core** delivers native performance

### Robustness
- **Isolation**: Block corruption affects only specific blocks, not entire files
- **Atomic operations**: Cache operations are transactional
- **Reference counting**: Prevents premature deletion of shared blocks

## Installation

### Quick Install
```bash
pip install unicache
```

### Requirements
- Python 3.8+
- Rust toolchain (for building from source)
- Dependencies: `maturin`, `click`, `tqdm`, `requests`

## Quick Start

### Python API (High-Level)

The high-level API provides an effortless interface for common operations:

```python
from unicache.api import UniCache

# Context manager handles setup/cleanup automatically
with UniCache() as cache:
    # Download and cache files from URLs
    file_id = cache.download("https://example.com/dataset.tar.gz")
    
    # Add local files to cache
    local_id = cache.add("./large_model.bin")
    
    # Retrieve cached files
    cached_path = cache.get(file_id)
    cache.copy_to(local_id, "./output/model.bin")
    
    # View deduplication benefits
    stats = cache.stats()
    print(f"Storage saved: {stats['space_saved_mb']:.2f} MB")
    print(f"Deduplication ratio: {stats['deduplication_ratio']:.2f}x")
```

### Command Line Interface

```bash
# Download and cache large files with parallel transfers
unicache download "https://example.com/large-dataset.tar.gz" --max-files 8

# Store local files
unicache store ./my-large-file.bin

# Retrieve files by ID
unicache retrieve abc123def456 ./output-file.bin

# View cache statistics
unicache stats

# Clean up cache
unicache remove abc123def456
```

## API Reference

### High-Level API

Perfect for straightforward caching needs:

```python
from unicache.api import UniCache, download, add_file, get_file

# Class-based interface for multiple operations
with UniCache(cache_dir="./my_cache") as cache:
    # Download with progress tracking
    file_id = cache.download(
        "https://huggingface.co/microsoft/DialoGPT-medium/resolve/main/pytorch_model.bin"
    )
    
    # Add files with custom IDs
    cache.add("./data.json", file_id="my_data")
    
    # Check existence before operations
    if cache.exists("my_data"):
        cache.copy_to("my_data", "./backup/data.json")
    
    # Monitor storage efficiency
    stats = cache.stats()
    efficiency = stats['deduplication_ratio']

# Convenience functions for one-off operations
file_id = download("https://example.com/file.zip")
local_id = add_file("./document.pdf")
get_file(file_id, "./downloads/file.zip")
```

### Low-Level API

For advanced use cases requiring fine-grained control:

```python
from unicache import Cache
from unicache.cache_utils import download_and_store

# Create cache with custom block size
cache = Cache(
    block_size=4*1024*1024,  # 4MB blocks for large files
    cache_dir="./cache"
)

# Download with custom settings
file_id, temp_path = download_and_store(
    cache=cache,
    url="https://example.com/huge-dataset.tar.gz",
    use_hf_transfer=True,
    max_files=16  # High parallelism for fast connections
)

# Manual file operations
file_id = cache.store_file("./input.bin")
cache.retrieve_file(file_id, "./output.bin")

# Detailed statistics
blocks, files, physical_size, logical_size = cache.get_stats()
dedup_ratio = logical_size / physical_size if physical_size > 0 else 1.0
```

## Command Line Reference

### Download Operations
```bash
# Basic download
unicache download "https://example.com/file.bin"

# High-speed parallel download
unicache download "https://example.com/file.bin" --max-files 8

# Custom file ID
unicache download "https://example.com/file.bin" --id "my_file"

# Disable fast downloads (use standard requests)
unicache download "https://example.com/file.bin" --no-hf-transfer
```

### Storage Operations
```bash
# Store local file
unicache store ./large_file.bin

# Retrieve file
unicache retrieve <file_id> ./output.bin

# Remove file
unicache remove <file_id>
```

### Information Commands
```bash
# Cache statistics
unicache stats

# Download capabilities
unicache info
```

## Advanced Features

### Fast Downloads with `hf-transfer`

UniCache integrates with `hf-transfer` for high-performance downloads:

- **Parallel chunk downloading**: Multiple simultaneous connections
- **Real-time progress**: Speed, ETA, and completion percentage
- **Automatic retry**: Failed chunks retry with exponential backoff
- **Bandwidth optimization**: Can exceed 500MB/s on fast connections (unlike a pure-Python implementation)

```python
# Automatic fast downloads
with UniCache() as cache:
    # Uses hf-transfer automatically if available
    file_id = cache.download("https://example.com/large-file.tar.gz")

# Check download capabilities
info = cache.download_info()
print(f"Fast downloads available: {info['hf_transfer_available']}")
```

### Custom Block Sizes

Optimize for your use case:

```python
# Small blocks for better deduplication
cache = Cache(block_size=64*1024)  # 64KB blocks

# Large blocks for fewer seeks
cache = Cache(block_size=4*1024*1024)  # 4MB blocks
```

### Error Handling and Recovery

```python
from unicache.api import UniCache, CacheError

try:
    with UniCache() as cache:
        file_id = cache.download("https://example.com/file.bin")
        path = cache.get(file_id)
except CacheError as e:
    print(f"Cache operation failed: {e}")
except KeyboardInterrupt:
    print("Operation cancelled by user")
    # Cache remains in consistent state
```

## Architecture Overview

### Block-Based Storage

UniCache uses fixed-size blocks (default 1MB) with BLAKE3 hashing:

```
File: [Block A][Block B][Block C][Block A][Block D]
                    ↓
Storage: [Block A: offset=0][Block B: offset=1MB][Block C: offset=2MB][Block D: offset=3MB]
Index:   {A: count=2, B: count=1, C: count=1, D: count=1}
```

### Storage Components

- **Blocks file**: Sequential storage of unique blocks
- **Index file**: JSON metadata with block locations and reference counts
- **Rust core**: Performance-critical operations (hashing, I/O, chunking)
- **Python interface**: High-level API and CLI

### Deduplication Process

1. File split into fixed-size blocks
2. Each block hashed with BLAKE3
3. Duplicate blocks detected by hash comparison
4. Only unique blocks stored physically
5. Reference counting tracks block usage

## Performance Considerations

### Block Size Impact

- **Smaller blocks** (64KB-256KB): Better deduplication, more overhead
- **Larger blocks** (1MB-4MB): Less overhead, potentially less deduplication
- **Default 1MB**: Balanced for most use cases

### Memory Usage

UniCache keeps only metadata in memory:

- **Index data**: ~100 bytes per unique block
- **File metadata**: ~50 bytes per cached file
- **Runtime overhead**: Minimal heap allocation

### I/O Patterns

- **Sequential writes**: New blocks appended to storage file
- **Random reads**: Direct block access by offset
- **Batch operations**: Multiple blocks read/written together

## Use Cases

### Machine Learning
```python
# Cache large model files and datasets
with UniCache(cache_dir="./ml_cache") as cache:
    model_id = cache.download("https://huggingface.co/bert-base-uncased/resolve/main/pytorch_model.bin")
    dataset_id = cache.add("./preprocessed_dataset.pkl")
    
    # Models with similar architectures share blocks
    stats = cache.stats()
    print(f"Storage efficiency: {stats['deduplication_ratio']:.2f}x")
```

### Content Distribution
```bash
# Cache frequently accessed files
unicache download "https://cdn.example.com/assets.tar.gz"
unicache download "https://cdn.example.com/updates.tar.gz"

# View deduplication benefits
unicache stats
```

### Development Workflows
```python
# Cache build artifacts and dependencies
with UniCache(cache_dir="./build_cache") as cache:
    # Large binary dependencies
    cache.add("./node_modules.tar.gz")
    cache.add("./target/release/app")
    
    # Docker layer equivalents
    cache.add("./base_layer.tar")
    cache.add("./app_layer.tar")
```

## Acknowledgments

UniCache is inspired by the following projects:

- [hf-transfer](https://github.com/huggingface/hf-transfer)
- [Xet](https://github.com/huggingface/xet-core)

## License

This software is licensed under the MIT License.

---

**UniCache**: Because every byte should only be stored once.