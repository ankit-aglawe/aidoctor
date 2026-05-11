import { useState } from "react";

function TodoList() {
  const [todos, setTodos] = useState([]);
  const [draft, setDraft] = useState("");

  function addTodo() {
    const text = draft.trim();
    if (!text) return;
    const newTodo = {
      id:
        typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      text,
      completed: false,
    };
    setTodos((prev) => [...prev, newTodo]);
    setDraft("");
  }

  function removeTodo(id) {
    setTodos((prev) => prev.filter((todo) => todo.id !== id));
  }

  function toggleTodo(id) {
    setTodos((prev) =>
      prev.map((todo) =>
        todo.id === id ? { ...todo, completed: !todo.completed } : todo
      )
    );
  }

  function handleSubmit(event) {
    event.preventDefault();
    addTodo();
  }

  return (
    <section>
      <h1>Todo List</h1>

      <form onSubmit={handleSubmit}>
        <label>
          New todo
          <input
            type="text"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="What needs doing?"
          />
        </label>
        <button type="submit">Add</button>
      </form>

      {todos.length === 0 ? (
        <p>No todos yet.</p>
      ) : (
        <ul>
          {todos.map((todo) => (
            <li key={todo.id}>
              <label>
                <input
                  type="checkbox"
                  checked={todo.completed}
                  onChange={() => toggleTodo(todo.id)}
                  aria-label={`Mark "${todo.text}" as ${
                    todo.completed ? "incomplete" : "complete"
                  }`}
                />
                <span
                  style={{
                    textDecoration: todo.completed ? "line-through" : "none",
                  }}
                >
                  {todo.text}
                </span>
              </label>
              <button
                type="button"
                onClick={() => removeTodo(todo.id)}
                aria-label={`Remove "${todo.text}"`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default TodoList;
