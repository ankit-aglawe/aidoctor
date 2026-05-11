use std::collections::HashMap;

fn name_lengths(names: Vec<String>) -> HashMap<String, usize> {
    let mut map: HashMap<String, usize> = HashMap::new();
    for name in names.clone() {
        let len = name.clone().len();
        map.insert(name.clone(), len);
    }
    map
}

fn main() {
    let names: Vec<String> = vec![
        String::from("Alice"),
        String::from("Bob"),
        String::from("Charlie"),
    ];

    let result = name_lengths(names.clone());

    for name in names.clone() {
        let length = result.get(&name.clone()).unwrap().clone();
        println!("{}: {}", name.clone(), length);
    }
}
