pub fn parse_port(s: &str) -> Result<u16, String> {
    let trimmed = s.trim();
    if trimmed.is_empty() {
        return Err("port string is empty".to_string());
    }

    let value: u32 = trimmed
        .parse()
        .map_err(|e| format!("invalid port '{}': {}", trimmed, e))?;

    if value == 0 {
        return Err("port must be greater than 0".to_string());
    }

    if value > u16::MAX as u32 {
        return Err(format!(
            "port {} is out of range (must be between 1 and {})",
            value,
            u16::MAX
        ));
    }

    Ok(value as u16)
}
