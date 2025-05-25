mod block;

use pyo3::prelude::*;
use pyo3::exceptions::{PyIOError, PyValueError};
use pyo3::types::PyBytes;
use std::fs::{self, File};
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};
use std::collections::HashMap;
use blake3::Hasher;
use serde::{Serialize, Deserialize};
use std::sync::{Arc, Mutex};
use rayon::prelude::*;
use thiserror::Error;

use block::{BlockStore, BlockHash, BlockInfo, BlockError};

#[derive(Error, Debug)]
pub enum CacheError {
    #[error("IO error: {0}")]
    Io(#[from] io::Error),
    
    #[error("Block error: {0}")]
    Block(#[from] BlockError),
    
    #[error("File not found: {0}")]
    FileNotFound(String),
    
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    
    #[error("Cache error: {0}")]
    Other(String),
}

type Result<T> = std::result::Result<T, CacheError>;

#[derive(Debug, Serialize, Deserialize)]
struct FileInfo {
    blocks: Vec<BlockHash>,
    size: u64,
    name: String,
}

struct CacheStorage {
    block_size: usize,
    cache_dir: PathBuf,
    block_store: BlockStore,
    file_index: HashMap<String, FileInfo>,
    modified: bool,
}

impl CacheStorage {
    fn new(block_size: usize, cache_dir: &Path) -> Result<Self> {
        fs::create_dir_all(cache_dir)?;
        
        let blocks_path = cache_dir.join("blocks.bin");
        let index_path = cache_dir.join("index.json");
        
        let mut block_store = BlockStore::new(&blocks_path)?;
        
        let (block_index, file_index) = if index_path.exists() {
            let index_data = fs::read_to_string(&index_path)?;
            let index: (HashMap<String, BlockInfo>, HashMap<String, FileInfo>) = serde_json::from_str(&index_data)?;
            
            // Convert string keys back to BlockHash
            let block_index = index.0.into_iter()
                .filter_map(|(k, v)| {
                    let hash = hex::decode(k).ok()?;
                    if hash.len() == 32 {
                        let mut block_hash = [0u8; 32];
                        block_hash.copy_from_slice(&hash);
                        Some((block_hash, v))
                    } else {
                        None
                    }
                })
                .collect();
                
            (block_index, index.1)
        } else {
            (HashMap::new(), HashMap::new())
        };
        
        block_store.set_index(block_index);
        
        Ok(CacheStorage {
            block_size,
            cache_dir: cache_dir.to_path_buf(),
            block_store,
            file_index,
            modified: false,
        })
    }
    
    fn save_index(&self) -> Result<()> {
        if !self.modified && !self.block_store.is_modified() {
            return Ok(());
        }
        
        // Convert BlockHash to hex strings for JSON serialization
        let block_index_hex: HashMap<String, BlockInfo> = self.block_store.get_index()
            .iter()
            .map(|(k, v)| (hex::encode(k), v.clone()))
            .collect();
            
        let index_data = serde_json::to_string(&(block_index_hex, &self.file_index))?;
        fs::write(self.cache_dir.join("index.json"), index_data)?;
        
        Ok(())
    }
    
    fn store_file(&mut self, file_path: &Path, file_id: &str) -> Result<()> {
        let file = File::open(file_path)?;
        let file_size = file.metadata()?.len();
        let file_name = file_path.file_name()
            .ok_or_else(|| CacheError::Other("Invalid file path".to_string()))?
            .to_string_lossy()
            .to_string();
            
        let mut blocks = Vec::new();
        
        // Process file in chunks using memory mapping for efficiency
        let chunk_size = 10 * 1024 * 1024; // 10MB chunks for processing
        let mut file = File::open(file_path)?;
        let mut buffer = vec![0u8; chunk_size];
        
        let mut remaining = file_size;
        while remaining > 0 {
            let to_read = std::cmp::min(remaining, chunk_size as u64) as usize;
            let buffer = &mut buffer[..to_read];
            file.read_exact(buffer)?;
            
            // Split chunk into blocks and store them
            for chunk in buffer.chunks(self.block_size) {
                let hash = self.block_store.store_block(chunk)?;
                blocks.push(hash);
            }
            
            remaining -= to_read as u64;
        }
        
        // Store file info
        let file_info = FileInfo {
            blocks,
            size: file_size,
            name: file_name,
        };
        
        self.file_index.insert(file_id.to_string(), file_info);
        self.modified = true;
        self.save_index()?;
        
        Ok(())
    }
    
    fn retrieve_file(&mut self, file_id: &str, output_path: &Path) -> Result<()> {
        let file_info = self.file_index.get(file_id)
            .ok_or_else(|| CacheError::FileNotFound(file_id.to_string()))?;
            
        let mut output_file = File::create(output_path)?;
        
        for hash in &file_info.blocks {
            let block_data = self.block_store.read_block(hash)?;
            output_file.write_all(&block_data)?;
        }
        
        Ok(())
    }
    
    fn remove_file(&mut self, file_id: &str) -> Result<()> {
        let file_info = self.file_index.remove(file_id)
            .ok_or_else(|| CacheError::FileNotFound(file_id.to_string()))?;
            
        // Decrement reference counts
        for hash in &file_info.blocks {
            self.block_store.decrement_ref(hash)?;
        }
        
        self.modified = true;
        self.save_index()?;
        
        Ok(())
    }
    
    fn get_stats(&self) -> (usize, usize, u64, u64) {
        let total_blocks = self.block_store.block_count();
        let total_files = self.file_index.len();
        
        let stored_size = self.block_store.total_size();
            
        let logical_size: u64 = self.file_index.values()
            .map(|info| info.size)
            .sum();
            
        (total_blocks, total_files, stored_size, logical_size)
    }
}

#[pyclass]
struct Cache {
    storage: Arc<Mutex<CacheStorage>>,
}

#[pymethods]
impl Cache {
    #[new]
    fn new(block_size: usize, cache_dir: &str) -> PyResult<Self> {
        let storage = CacheStorage::new(block_size, Path::new(cache_dir))
            .map_err(|e| PyIOError::new_err(e.to_string()))?;
            
        Ok(Cache {
            storage: Arc::new(Mutex::new(storage)),
        })
    }
    
    fn store_file(&self, file_path: &str, file_id: Option<&str>) -> PyResult<String> {
        let file_id = file_id.map_or_else(
            || {
                // Generate a file ID based on path if not provided
                let mut hasher = Hasher::new();
                hasher.update(file_path.as_bytes());
                hasher.update(&std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
                    .to_le_bytes());
                hex::encode(&hasher.finalize().as_bytes()[0..16])
            },
            |id| id.to_string(),
        );
        
        let mut storage = self.storage.lock().unwrap();
        storage.store_file(Path::new(file_path), &file_id)
            .map_err(|e| PyIOError::new_err(e.to_string()))?;
            
        Ok(file_id)
    }
    
    fn retrieve_file(&self, file_id: &str, output_path: &str) -> PyResult<()> {
        let mut storage = self.storage.lock().unwrap();
        storage.retrieve_file(file_id, Path::new(output_path))
            .map_err(|e| PyIOError::new_err(e.to_string()))?;
            
        Ok(())
    }
    
    fn remove_file(&self, file_id: &str) -> PyResult<()> {
        let mut storage = self.storage.lock().unwrap();
        storage.remove_file(file_id)
            .map_err(|e| PyIOError::new_err(e.to_string()))?;
            
        Ok(())
    }
    
    fn get_stats(&self) -> PyResult<(usize, usize, u64, u64)> {
        let storage = self.storage.lock().unwrap();
        Ok(storage.get_stats())
    }
}

#[pymodule]
fn unicache_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Cache>()?;
    Ok(())
} 