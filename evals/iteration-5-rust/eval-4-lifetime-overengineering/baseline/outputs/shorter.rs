fn shorter<'a, 'b: 'a, 'c: 'a>(s1: &'b str, s2: &'c str) -> &'a str {
    if s1.len() <= s2.len() {
        s1
    } else {
        s2
    }
}

fn main() {
    let a = String::from("hello");
    let b = String::from("hi");
    let result = shorter(&a, &b);
    println!("Shorter: {}", result);
}
