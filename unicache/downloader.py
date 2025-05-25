#!/usr/bin/env python3
"""
Fast downloader module using hf-transfer for high-speed downloads.
"""

import os
import tempfile
import requests
from pathlib import Path
from typing import Optional, Callable
from tqdm import tqdm

try:
    import hf_transfer
    HF_TRANSFER_AVAILABLE = True
except ImportError:
    HF_TRANSFER_AVAILABLE = False


class DownloadError(Exception):
    """Exception raised when download fails."""
    pass


def download_file_fast(
    url: str,
    output_path: str,
    chunk_size: int = 8192,
    max_files: int = 8,
    progress_callback: Optional[Callable[[int], None]] = None,
    use_hf_transfer: bool = True,
    headers: Optional[dict] = None
) -> str:
    """
    Download a file using the fastest available method.
    
    Args:
        url: URL to download from
        output_path: Local path to save the file
        chunk_size: Chunk size for hf-transfer (default 8KB, but hf-transfer uses larger chunks internally)
        max_files: Maximum number of parallel connections for hf-transfer
        progress_callback: Optional callback function called with bytes downloaded
        use_hf_transfer: Whether to use hf-transfer if available (default True)
        headers: Optional HTTP headers
        
    Returns:
        Path to the downloaded file
        
    Raises:
        DownloadError: If download fails
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Try hf-transfer first if available and requested
    if use_hf_transfer and HF_TRANSFER_AVAILABLE:
        try:
            return _download_with_hf_transfer(
                url, str(output_path), chunk_size, max_files, progress_callback, headers
            )
        except Exception as e:
            print(f"hf-transfer failed ({e}), falling back to requests...")
    
    # Fallback to requests
    return _download_with_requests(url, str(output_path), progress_callback, headers)


def _download_with_hf_transfer(
    url: str,
    output_path: str,
    chunk_size: int,
    max_files: int,
    progress_callback: Optional[Callable[[int], None]],
    headers: Optional[dict]
) -> str:
    """Download using hf-transfer for maximum speed."""
    
    # Convert headers to the format expected by hf-transfer
    hf_headers = {}
    if headers:
        hf_headers = {k: v for k, v in headers.items()}
    
    # Get file size for progress bar
    try:
        import requests
        head_response = requests.head(url, headers=headers, allow_redirects=True)
        total_size = int(head_response.headers.get('content-length', 0))
    except:
        total_size = 0
    
    # Create progress bar and callback wrapper
    total_downloaded = [0]
    pbar = None
    
    if total_size > 0:
        pbar = tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading (hf-transfer)", dynamic_ncols=True)
    
    def hf_progress_callback(chunk_size_downloaded: int):
        total_downloaded[0] += chunk_size_downloaded
        if pbar:
            pbar.update(chunk_size_downloaded)
        if progress_callback:
            progress_callback(chunk_size_downloaded)
    
    try:
        # Use hf-transfer's download function
        hf_transfer.download(
            url=url,
            filename=output_path,
            max_files=max_files,
            chunk_size=max(chunk_size, 1024 * 1024),  # At least 1MB chunks for efficiency
            parallel_failures=2,  # Allow some parallel failures
            max_retries=3,  # Retry failed chunks
            headers=hf_headers if hf_headers else None,
            callback=hf_progress_callback
        )
        
        if pbar:
            pbar.close()
        
        if not os.path.exists(output_path):
            raise DownloadError(f"hf-transfer completed but file not found: {output_path}")
            
        return output_path
        
    except KeyboardInterrupt:
        if pbar:
            pbar.close()
        # Clean up partial file
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        raise KeyboardInterrupt("Download interrupted by user")
        
    except Exception as e:
        if pbar:
            pbar.close()
        # Clean up partial file if it exists
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        raise DownloadError(f"hf-transfer download failed: {e}")


def _download_with_requests(
    url: str,
    output_path: str,
    progress_callback: Optional[Callable[[int], None]],
    headers: Optional[dict]
) -> str:
    """Fallback download using requests with progress bar."""
    
    try:
        with requests.get(url, stream=True, headers=headers) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            with open(output_path, 'wb') as f:
                if total_size > 0:
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading (requests)", dynamic_ncols=True) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                chunk_size = len(chunk)
                                pbar.update(chunk_size)
                                if progress_callback:
                                    progress_callback(chunk_size)
                else:
                    # No content-length header, download without progress bar
                    print("Downloading (size unknown)...")
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            if progress_callback:
                                progress_callback(len(chunk))
        
        return output_path
        
    except KeyboardInterrupt:
        # Clean up partial file
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        raise KeyboardInterrupt("Download interrupted by user")
        
    except Exception as e:
        # Clean up partial file if it exists
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        raise DownloadError(f"requests download failed: {e}")


def get_download_info():
    """Get information about available download methods."""
    info = {
        "hf_transfer_available": HF_TRANSFER_AVAILABLE,
        "methods": ["requests"]
    }
    
    if HF_TRANSFER_AVAILABLE:
        info["methods"].insert(0, "hf-transfer")
        try:
            info["hf_transfer_version"] = hf_transfer.__version__
        except:
            info["hf_transfer_version"] = "unknown"
    
    return info


# Convenience function for simple downloads
def download(url: str, output_path: str, **kwargs) -> str:
    """
    Simple download function with sensible defaults.
    
    Args:
        url: URL to download
        output_path: Where to save the file
        **kwargs: Additional arguments passed to download_file_fast
        
    Returns:
        Path to downloaded file
    """
    return download_file_fast(url, output_path, **kwargs) 