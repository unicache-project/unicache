use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Write, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use std::collections::HashMap;
use blake3::Hasher;
use serde::{Serialize, Deserialize};
use thiserror::Error;

pub type BlockHash = [u8; 32];

#[derive(Error, Debug)]
pub enum BlockError {
    #[error("IO error: {0}")]
    Io(#[from] io::Error),
    
    #[error("Block not found: {0}")]
    BlockNotFound(String),
    
    #[error("Block error: {0}")]
    Other(String),
}

pub type Result<T> = std::result::Result<T, BlockError>;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BlockInfo {
    pub offset: u64,
    pub size: u32,
    pub ref_count: u32,
}

pub struct BlockStore {
    blocks_path: PathBuf,
    blocks_file: File,
    block_index: HashMap<BlockHash, BlockInfo>,
    modified: bool,
}

impl BlockStore {
    pub fn new(blocks_path: &Path) -> Result<Self> {
        let parent_dir = blocks_path.parent().ok_or_else(|| 
            BlockError::Other("Invalid blocks path".to_string()))?;
        fs::create_dir_all(parent_dir)?;
        
        let blocks_file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .open(blocks_path)?;
            
        Ok(BlockStore {
            blocks_path: blocks_path.to_path_buf(),
            blocks_file,
            block_index: HashMap::new(),
            modified: false,
        })
    }
    
    pub fn set_index(&mut self, block_index: HashMap<BlockHash, BlockInfo>) {
        self.block_index = block_index;
    }
    
    pub fn get_index(&self) -> &HashMap<BlockHash, BlockInfo> {
        &self.block_index
    }
    
    pub fn is_modified(&self) -> bool {
        self.modified
    }
    
    pub fn hash_block(data: &[u8]) -> BlockHash {
        let mut hasher = Hasher::new();
        hasher.update(data);
        *hasher.finalize().as_bytes()
    }
    
    pub fn store_block(&mut self, data: &[u8]) -> Result<BlockHash> {
        let hash = Self::hash_block(data);
        
        if let Some(block_info) = self.block_index.get_mut(&hash) {
            // Block already exists, just increment reference count
            block_info.ref_count += 1;
            self.modified = true;
            return Ok(hash);
        }
        
        // New block, append to blocks file
        let offset = self.blocks_file.seek(SeekFrom::End(0))?;
        self.blocks_file.write_all(data)?;
        
        // Store block info
        let block_info = BlockInfo {
            offset,
            size: data.len() as u32,
            ref_count: 1,
        };
        
        self.block_index.insert(hash, block_info);
        self.modified = true;
        
        Ok(hash)
    }
    
    pub fn read_block(&mut self, hash: &BlockHash) -> Result<Vec<u8>> {
        let block_info = self.block_index.get(hash)
            .ok_or_else(|| BlockError::BlockNotFound(hex::encode(hash)))?;
            
        let mut buffer = vec![0u8; block_info.size as usize];
        self.blocks_file.seek(SeekFrom::Start(block_info.offset))?;
        self.blocks_file.read_exact(&mut buffer)?;
        
        Ok(buffer)
    }
    
    pub fn decrement_ref(&mut self, hash: &BlockHash) -> Result<bool> {
        let should_remove = if let Some(block_info) = self.block_index.get_mut(hash) {
            block_info.ref_count -= 1;
            self.modified = true;
            block_info.ref_count == 0
        } else {
            return Err(BlockError::BlockNotFound(hex::encode(hash)));
        };
        
        if should_remove {
            self.block_index.remove(hash);
        }
        
        Ok(should_remove)
    }
    
    pub fn total_size(&self) -> u64 {
        self.block_index.values()
            .map(|info| info.size as u64)
            .sum()
    }
    
    pub fn block_count(&self) -> usize {
        self.block_index.len()
    }
} 