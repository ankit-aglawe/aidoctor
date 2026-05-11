//! Port parsing for a library crate.
//!
//! Exposes [`parse_port`], which converts a string into a valid TCP/UDP port
//! number (`u16`, excluding 0). Errors are typed so callers can match on
//! the specific failure mode rather than parsing strings.

use std::num::ParseIntError;

/// Errors that can occur while parsing a port string.
///
/// This is a typed enum (not `Result<u16, String>`) so that downstream
/// callers can pattern-match on the failure reason — surfacing
/// `InvalidNumber` differently from `OutOfRange`, for example in error
/// messages, metrics, or retry decisions.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PortParseError {
    /// The input was empty or whitespace-only.
    Empty,
    /// The input was not a valid unsigned integer in the `u16` range.
    ///
    /// Wraps the underlying [`ParseIntError`] so callers retain the
    /// original parser diagnostic if they want it.
    InvalidNumber(ParseIntError),
    /// The input parsed as `0`, which is not a valid TCP/UDP port for
    /// most practical purposes (it means "any port" at the OS level
    /// and is not assignable as a destination).
    OutOfRange { value: u16 },
}

impl std::fmt::Display for PortParseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Empty => f.write_str("port string is empty"),
            Self::InvalidNumber(e) => write!(f, "invalid port number: {e}"),
            Self::OutOfRange { value } => {
                write!(f, "port {value} is out of the valid range 1..=65535")
            }
        }
    }
}

impl std::error::Error for PortParseError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::InvalidNumber(e) => Some(e),
            Self::Empty | Self::OutOfRange { .. } => None,
        }
    }
}

impl From<ParseIntError> for PortParseError {
    fn from(e: ParseIntError) -> Self {
        Self::InvalidNumber(e)
    }
}

/// Parse a string into a valid TCP/UDP port number.
///
/// Accepts a trimmed decimal integer in the range `1..=65535`.
/// Rejects empty strings, non-numeric input, values outside the `u16`
/// range, and port `0`.
///
/// # Errors
///
/// Returns a [`PortParseError`] variant describing exactly which
/// validation step failed. See the enum docs for details.
///
/// # Examples
///
/// ```
/// # use port_parser::{parse_port, PortParseError};
/// assert_eq!(parse_port("8080").unwrap(), 8080);
/// assert!(matches!(parse_port(""), Err(PortParseError::Empty)));
/// assert!(matches!(parse_port("0"), Err(PortParseError::OutOfRange { value: 0 })));
/// assert!(matches!(parse_port("70000"), Err(PortParseError::InvalidNumber(_))));
/// ```
pub fn parse_port(s: &str) -> Result<u16, PortParseError> {
    let trimmed = s.trim();
    if trimmed.is_empty() {
        return Err(PortParseError::Empty);
    }
    let value: u16 = trimmed.parse()?;
    if value == 0 {
        return Err(PortParseError::OutOfRange { value });
    }
    Ok(value)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_valid_port() {
        assert_eq!(parse_port("8080").unwrap(), 8080);
        assert_eq!(parse_port("1").unwrap(), 1);
        assert_eq!(parse_port("65535").unwrap(), 65535);
    }

    #[test]
    fn trims_whitespace() {
        assert_eq!(parse_port("  443  ").unwrap(), 443);
    }

    #[test]
    fn rejects_empty() {
        assert_eq!(parse_port(""), Err(PortParseError::Empty));
        assert_eq!(parse_port("   "), Err(PortParseError::Empty));
    }

    #[test]
    fn rejects_zero() {
        assert_eq!(
            parse_port("0"),
            Err(PortParseError::OutOfRange { value: 0 })
        );
    }

    #[test]
    fn rejects_overflow() {
        assert!(matches!(
            parse_port("65536"),
            Err(PortParseError::InvalidNumber(_))
        ));
        assert!(matches!(
            parse_port("99999999"),
            Err(PortParseError::InvalidNumber(_))
        ));
    }

    #[test]
    fn rejects_non_numeric() {
        assert!(matches!(
            parse_port("abc"),
            Err(PortParseError::InvalidNumber(_))
        ));
        assert!(matches!(
            parse_port("-1"),
            Err(PortParseError::InvalidNumber(_))
        ));
    }

    #[test]
    fn error_display_is_useful() {
        let err = parse_port("0").unwrap_err();
        let msg = format!("{err}");
        assert!(msg.contains("0"));
        assert!(msg.contains("range"));
    }

    #[test]
    fn error_source_chain_preserves_parse_int_error() {
        let err = parse_port("abc").unwrap_err();
        assert!(std::error::Error::source(&err).is_some());
    }
}
