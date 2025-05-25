#!/usr/bin/env python3
"""
Command line interface for UniCache.
"""

import os
import sys
import signal
import click
from pathlib import Path
import time
from tqdm import tqdm
from unicache import Cache, __version__, get_download_info
from unicache.cache_utils import download_to_cache_cli

DEFAULT_CACHE_DIR = Path.home() / ".unicache"
DEFAULT_BLOCK_SIZE = 1024 * 1024  # 1MB

def format_size(size_bytes):
    """Format size in bytes to human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def setup_signal_handlers():
    """Setup signal handlers for graceful interruption."""
    def signal_handler(signum, frame):
        click.echo("\n\nInterrupted by user (Ctrl+C)", err=True)
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)

def get_cache(cache_dir, block_size):
    """Get a cache instance with the specified parameters."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(exist_ok=True, parents=True)
    return Cache(block_size=block_size, cache_dir=str(cache_dir))

@click.group()
@click.version_option(version=__version__)
@click.option('--cache-dir', default=str(DEFAULT_CACHE_DIR), help='Cache directory path')
@click.option('--block-size', default=DEFAULT_BLOCK_SIZE, help='Block size in bytes')
@click.pass_context
def cli(ctx, cache_dir, block_size):
    """UniCache - A block-based deduplicated cache storage backend."""
    setup_signal_handlers()
    ctx.ensure_object(dict)
    ctx.obj['cache_dir'] = cache_dir
    ctx.obj['block_size'] = block_size

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--id', help='Custom ID for the stored file')
@click.pass_context
def store(ctx, file_path, id):
    """Store a file in the cache."""
    cache = get_cache(ctx.obj['cache_dir'], ctx.obj['block_size'])
    file_path = Path(file_path)
    file_size = os.path.getsize(file_path)
    
    click.echo(f"Storing file: {file_path}")
    click.echo(f"File size: {format_size(file_size)}")
    
    start_time = time.time()
    file_id = cache.store_file(str(file_path), id)
    end_time = time.time()
    
    click.echo(f"File stored with ID: {file_id}")
    click.echo(f"Storage time: {end_time - start_time:.2f} seconds")
    
    # Print cache stats
    blocks, files, stored_size, logical_size = cache.get_stats()
    click.echo(f"Cache statistics:")
    click.echo(f"  Total blocks: {blocks}")
    click.echo(f"  Total files: {files}")
    click.echo(f"  Physical storage used: {format_size(stored_size)}")
    click.echo(f"  Logical storage: {format_size(logical_size)}")
    dedup_ratio = logical_size / stored_size if stored_size > 0 else 1.0
    click.echo(f"  Deduplication ratio: {dedup_ratio:.2f}x")

@cli.command()
@click.argument('file_id')
@click.argument('output_path', type=click.Path())
@click.pass_context
def retrieve(ctx, file_id, output_path):
    """Retrieve a file from the cache."""
    cache = get_cache(ctx.obj['cache_dir'], ctx.obj['block_size'])
    
    click.echo(f"Retrieving file with ID: {file_id}")
    start_time = time.time()
    cache.retrieve_file(file_id, output_path)
    end_time = time.time()
    
    file_size = os.path.getsize(output_path)
    click.echo(f"File retrieved to: {output_path}")
    click.echo(f"File size: {format_size(file_size)}")
    click.echo(f"Retrieval time: {end_time - start_time:.2f} seconds")

@cli.command()
@click.argument('file_id')
@click.pass_context
def remove(ctx, file_id):
    """Remove a file from the cache."""
    cache = get_cache(ctx.obj['cache_dir'], ctx.obj['block_size'])
    
    click.echo(f"Removing file with ID: {file_id}")
    cache.remove_file(file_id)
    click.echo("File removed successfully")
    
    # Print cache stats
    blocks, files, stored_size, logical_size = cache.get_stats()
    click.echo(f"Cache statistics:")
    click.echo(f"  Total blocks: {blocks}")
    click.echo(f"  Total files: {files}")
    click.echo(f"  Physical storage used: {format_size(stored_size)}")
    click.echo(f"  Logical storage: {format_size(logical_size)}")

@cli.command()
@click.pass_context
def stats(ctx):
    """Show cache statistics."""
    cache = get_cache(ctx.obj['cache_dir'], ctx.obj['block_size'])
    
    blocks, files, stored_size, logical_size = cache.get_stats()
    click.echo(f"Cache directory: {ctx.obj['cache_dir']}")
    click.echo(f"Block size: {format_size(ctx.obj['block_size'])}")
    click.echo(f"Total blocks: {blocks}")
    click.echo(f"Total files: {files}")
    click.echo(f"Physical storage used: {format_size(stored_size)}")
    click.echo(f"Logical storage: {format_size(logical_size)}")
    
    if stored_size > 0:
        dedup_ratio = logical_size / stored_size
        click.echo(f"Deduplication ratio: {dedup_ratio:.2f}x")
        click.echo(f"Space saved: {format_size(logical_size - stored_size)}")

@cli.command()
@click.argument('url')
@click.option('--id', help='Custom ID for the downloaded file')
@click.option('--max-files', default=8, help='Maximum parallel connections for fast download')
@click.option('--no-hf-transfer', is_flag=True, help='Disable hf-transfer and use requests only')
@click.pass_context
def download(ctx, url, id, max_files, no_hf_transfer):
    """Download a file from URL and store it in the cache."""
    
    # Show download method info
    download_info = get_download_info()
    if download_info['hf_transfer_available'] and not no_hf_transfer:
        click.echo(f"Using fast download with hf-transfer (v{download_info.get('hf_transfer_version', 'unknown')})")
    else:
        if no_hf_transfer:
            click.echo("Using requests (hf-transfer disabled)")
        else:
            click.echo("Using requests (hf-transfer not available)")
    
    click.echo(f"Downloading from: {url}")
    if max_files > 1:
        click.echo(f"Max parallel connections: {max_files}")
    
    start_time = time.time()
    try:
        file_id = download_to_cache_cli(
            cache_dir=ctx.obj['cache_dir'],
            block_size=ctx.obj['block_size'],
            url=url,
            file_id=id,
            use_hf_transfer=not no_hf_transfer,
            max_files=max_files
        )
        end_time = time.time()
        
        click.echo(f"File downloaded and stored with ID: {file_id}")
        click.echo(f"Total time: {end_time - start_time:.2f} seconds")
        
        # Print cache stats
        cache = get_cache(ctx.obj['cache_dir'], ctx.obj['block_size'])
        blocks, files, stored_size, logical_size = cache.get_stats()
        click.echo(f"Cache statistics:")
        click.echo(f"  Total blocks: {blocks}")
        click.echo(f"  Total files: {files}")
        click.echo(f"  Physical storage used: {format_size(stored_size)}")
        click.echo(f"  Logical storage: {format_size(logical_size)}")
        dedup_ratio = logical_size / stored_size if stored_size > 0 else 1.0
        click.echo(f"  Deduplication ratio: {dedup_ratio:.2f}x")
        
    except KeyboardInterrupt:
        click.echo(f"\nDownload interrupted by user", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()

@cli.command()
@click.pass_context
def info(ctx):
    """Show information about available download methods."""
    download_info = get_download_info()
    
    click.echo("UniCache Download Information:")
    click.echo(f"Available methods: {', '.join(download_info['methods'])}")
    click.echo(f"hf-transfer available: {download_info['hf_transfer_available']}")
    
    if download_info['hf_transfer_available']:
        click.echo(f"hf-transfer version: {download_info.get('hf_transfer_version', 'unknown')}")
        click.echo("\nhf-transfer provides:")
        click.echo("  - Parallel chunk downloading")
        click.echo("  - Automatic retry with exponential backoff")
        click.echo("  - Optimized for high-bandwidth networks")
        click.echo("  - Can exceed 500MB/s on fast connections")
    else:
        click.echo("\nTo enable fast downloads, install hf-transfer:")
        click.echo("  pip install hf-transfer")

def main():
    cli(obj={})

if __name__ == "__main__":
    main() 