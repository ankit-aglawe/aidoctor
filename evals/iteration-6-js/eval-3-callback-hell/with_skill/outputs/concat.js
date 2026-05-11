import { readFile, writeFile } from "node:fs/promises";

async function concat() {
  const [a, b, c] = await Promise.all([
    readFile("a.txt", "utf8"),
    readFile("b.txt", "utf8"),
    readFile("c.txt", "utf8"),
  ]);
  await writeFile("out.txt", a + b + c);
}

concat().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exitCode = 1;
});
