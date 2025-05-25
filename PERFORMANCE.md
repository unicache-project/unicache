# UniCache Performance Guide

This document provides guidance on optimizing performance when using UniCache.

## Block Size Selection

The block size has a significant impact on both storage efficiency and performance:

| Block Size | Deduplication | Storage Overhead | I/O Operations | Memory Usage |
|------------|---------------|------------------|----------------|--------------|
| 4KB        | Excellent     | High             | Many           | Low          |
| 64KB       | Very Good     | Moderate         | Moderate       | Low          |
| 1MB        | Good          | Low              | Few            | Moderate     |
| 4MB        | Fair          | Very Low         | Very Few       | High         |

### Recommendations:

- **4KB - 64KB**: Use for datasets with many small, similar files
- **64KB - 256KB**: Good balance for general purpose use
- **1MB - 4MB**: Best for large files with less similarity (e.g., video, images)

## Benchmark Results

The `examples/benchmark.py` script allows you to test different block sizes with your specific workload. Sample results from a test with mixed content files:

```
Block Size      | Store Time  | Retrieve Time  | Blocks   | Dedup Ratio
----------------|-------------|----------------|----------|------------
     4.0 KB     |     5.21s   |       3.12s    |    62453 |     1.85x
    16.0 KB     |     3.17s   |       1.93s    |    15681 |     1.77x
    64.0 KB     |     1.82s   |       1.05s    |     3952 |     1.65x
   256.0 KB     |     1.03s   |       0.62s    |      997 |     1.42x
  1024.0 KB     |     0.71s   |       0.35s    |      253 |     1.31x
  4096.0 KB     |     0.48s   |       0.21s    |       67 |     1.12x
```

## Performance Optimization Tips

### 1. Parallel Processing

For applications processing multiple files:

```python
import concurrent.futures
from unicache import Cache

cache = Cache(block_size=1024*1024, cache_dir="./cache")

def process_file(file_path):
    file_id = cache.store_file(file_path)
    return file_id

# Process files in parallel
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    file_ids = list(executor.map(process_file, file_paths))
```

### 2. Memory Management

When working with very large files:

- Use the default chunk-based processing in UniCache
- Avoid loading entire files into memory
- Consider using memory-mapped files for advanced use cases

### 3. Cache Location

The location of your cache directory can significantly impact performance:

- Use local SSD storage when possible
- Avoid network file systems for the cache directory
- Ensure sufficient free space (at least 2x the expected cache size)

### 4. Index Optimization

The index file grows with the number of blocks and files:

- For large caches (>100GB), consider periodic maintenance
- Monitor index file size and loading time
- Future versions will support more efficient index formats

## Storage Efficiency

To maximize storage efficiency:

1. **Choose appropriate block size** for your data characteristics
2. **Group similar files** in the same cache
3. **Consider file preprocessing** (e.g., compression, normalization)
4. **Use smaller blocks** for text and structured data
5. **Use larger blocks** for binary and less redundant data

## Known Limitations

1. **No automatic compaction**: The blocks file only grows, even when blocks are deleted
2. **Sequential block access**: No parallel block retrieval (yet)
3. **In-memory index**: The entire index is loaded into memory
4. **No encryption**: Data is stored unencrypted

## Future Improvements

Planned performance improvements include:

1. Memory-mapped block file access
2. Binary index format
3. Block file compaction
4. Parallel block retrieval
5. In-memory block caching
6. Content-defined chunking 