# UniCache Architecture

UniCache is a high-performance block-based deduplicated cache storage backend with a Python interface. This document explains the design and implementation details.

## Overview

UniCache provides an efficient way to store files while avoiding storing duplicate content. The key concept is to break files into fixed-size blocks, and store each unique block only once. This approach provides several benefits:

1. **Storage efficiency**: Identical data is never stored more than once
2. **Performance**: Fixed-size blocks enable efficient I/O operations
3. **Memory efficiency**: Only metadata needs to be kept in memory
4. **Robustness**: Corruption in one block doesn't affect other files

## Core Components

### 1. Block-Based Deduplication

The core of UniCache is its block-based deduplication system:

- Files are split into fixed-size blocks (configurable, default 1MB)
- Each block is hashed using BLAKE3 (a fast cryptographic hash function)
- Blocks with identical hashes are stored only once
- Reference counting is used to track when blocks can be deleted

### 2. Storage Structure

The cache maintains two main components on disk:

1. **Blocks file**: A single file containing all stored blocks, appended sequentially
2. **Index file**: A JSON file storing metadata about blocks and files

The index contains:
- Block information (offset in blocks file, size, reference count)
- File information (list of block hashes, original file size, file name)

### 3. Rust Core

The performance-critical parts of UniCache are implemented in Rust:

- Block hashing and storage
- File chunking and reconstruction
- Index management
- Reference counting

Rust was chosen for its performance, memory safety, and ability to integrate with Python through PyO3.

### 4. Python Interface

The Python interface provides a simple API for interacting with the cache:

```python
from unicache import Cache

# Create a cache with a specified block size (in bytes)
cache = Cache(block_size=4096, cache_dir="./cache")

# Store a file in the cache
file_id = cache.store_file("large_file.bin")

# Retrieve the file from the cache
cache.retrieve_file(file_id, "retrieved_file.bin")

# Remove a file from the cache
cache.remove_file(file_id)

# Get cache statistics
blocks, files, stored_size, logical_size = cache.get_stats()
```

### 5. Command Line Interface

UniCache also provides a command-line interface for basic operations:

```bash
# Store a file
unicache store large_file.bin

# Retrieve a file
unicache retrieve FILE_ID output_file.bin

# Remove a file
unicache remove FILE_ID

# Show cache statistics
unicache stats
```

## Implementation Details

### Block Storage

Blocks are stored in a single file to minimize filesystem overhead. When a new block is added, it's appended to the end of the file. The offset of each block in the file is recorded in the index.

### Index Management

The index is serialized as a JSON file for simplicity and human readability. While this approach has some performance overhead compared to a binary format, it enables easy debugging and manual recovery if needed.

### Reference Counting

Each block has a reference count that tracks how many files are using it. When a file is removed, the reference counts of its blocks are decremented. Blocks with a reference count of zero are candidates for removal.

### File Handling

When storing a file:
1. The file is read in chunks
2. Each chunk is split into blocks of the configured size
3. Each block is hashed and checked against the index
4. New blocks are appended to the blocks file
5. Block references are updated
6. File metadata is stored in the index

When retrieving a file:
1. The file's metadata is retrieved from the index
2. Each block is read from the blocks file
3. The blocks are written in sequence to the output file

## Performance Considerations

### Block Size

The block size significantly impacts performance and deduplication efficiency:

- **Smaller blocks** (e.g., 4KB-64KB): Better deduplication but more overhead
- **Larger blocks** (e.g., 1MB-4MB): Less overhead but potentially less deduplication

The default block size (1MB) provides a good balance for most use cases.

### Caching

UniCache currently doesn't implement in-memory caching of frequently accessed blocks, which could be a future enhancement.

### Garbage Collection

The current implementation doesn't compact the blocks file when blocks are deleted. A future enhancement could include a garbage collection process to reclaim space.

## Future Improvements

1. **Compaction**: Implement a process to compact the blocks file by removing unreferenced blocks
2. **In-memory caching**: Cache frequently accessed blocks in memory
3. **Binary index format**: Replace JSON with a more efficient binary format
4. **Variable-sized chunks**: Implement content-defined chunking for better deduplication
5. **Encryption**: Add support for encrypting stored data
6. **Compression**: Implement block-level compression
7. **Remote storage**: Add support for storing blocks in cloud storage

## Conclusion

UniCache provides an efficient and reliable solution for caching large files with built-in deduplication. Its hybrid Rust/Python implementation delivers high performance while maintaining a user-friendly interface. 