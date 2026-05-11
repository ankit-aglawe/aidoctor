fn shorter<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() <= b.len() { a } else { b }
}

#[cfg(test)]
mod tests {
    use super::shorter;

    #[test]
    fn picks_shorter() {
        assert_eq!(shorter("hi", "hello"), "hi");
        assert_eq!(shorter("longer", "no"), "no");
    }

    #[test]
    fn ties_go_to_first() {
        assert_eq!(shorter("abc", "xyz"), "abc");
    }
}
