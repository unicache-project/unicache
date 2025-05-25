from unicache.unicache_rs import Cache
from unicache.downloader import download_file_fast, download, get_download_info, DownloadError
from unicache.api import UniCache, download as api_download, add_file, get_file, cache_stats

__version__ = "0.1.0"
__all__ = [
    "Cache", "download_file_fast", "download", "get_download_info", "DownloadError",
    "UniCache", "api_download", "add_file", "get_file", "cache_stats"
] 