use std::fs;
use std::io;

use serde::Deserialize;

#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct Config {
    pub name: String,
    pub version: u32,
}

#[derive(thiserror::Error, Debug)]
pub enum ConfigError {
    #[error("failed to read config file: {0}")]
    Io(#[from] io::Error),

    #[error("failed to parse config JSON: {0}")]
    Parse(#[from] serde_json::Error),
}

pub fn load_user_config(path: &str) -> Result<Config, ConfigError> {
    let raw = fs::read_to_string(path)?;
    let config = serde_json::from_str(&raw)?;
    Ok(config)
}
