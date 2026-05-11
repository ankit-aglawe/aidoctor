use std::collections::HashMap;

/// Build a map from each name to its length (in bytes, per `String::len`).
///
/// Takes `&[String]` rather than `Vec<String>` so callers can pass any slice
/// without giving up ownership, and iterates by reference (`&str`) so no
/// per-element clones are needed. Keys are produced via a single
/// `String::from(&str)` per entry — the unavoidable allocation, since the
/// returned map owns its keys.
pub fn name_lengths(names: &[String]) -> HashMap<String, usize> {
    names
        .iter()
        .map(|name| (String::from(name.as_str()), name.len()))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn maps_each_name_to_its_length() {
        let names = vec![
            String::from("ada"),
            String::from("grace"),
            String::from("linus"),
        ];

        let lengths = name_lengths(&names);

        assert_eq!(lengths.len(), 3);
        assert_eq!(lengths.get("ada"), Some(&3));
        assert_eq!(lengths.get("grace"), Some(&5));
        assert_eq!(lengths.get("linus"), Some(&5));
    }

    #[test]
    fn empty_input_produces_empty_map() {
        let names: Vec<String> = Vec::new();
        let lengths = name_lengths(&names);
        assert!(lengths.is_empty());
    }

    #[test]
    fn duplicate_names_collapse_to_one_entry() {
        let names = vec![String::from("dup"), String::from("dup")];
        let lengths = name_lengths(&names);
        assert_eq!(lengths.len(), 1);
        assert_eq!(lengths.get("dup"), Some(&3));
    }

    #[test]
    fn length_is_byte_length_for_multibyte_chars() {
        // "é" is 2 bytes in UTF-8.
        let names = vec![String::from("é")];
        let lengths = name_lengths(&names);
        assert_eq!(lengths.get("é"), Some(&2));
    }
}
