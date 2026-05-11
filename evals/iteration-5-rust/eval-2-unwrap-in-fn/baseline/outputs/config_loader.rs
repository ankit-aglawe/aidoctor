use serde::Deserialize;
use std::fs;

#[derive(Debug, Deserialize)]
pub struct Config {
    pub name: String,
    pub version: String,
    pub settings: std::collections::HashMap<String, serde_json::Value>,
}

pub fn load_user_config(path: &str) -> Config {
    let contents = fs::read_to_string(path).unwrap();
    let config: Config = serde_json::from_str(&contents).unwrap();
    config
}
