import React, { useState } from 'react';

function TodoList() {
  const [todos, setTodos] = useState([]);
  const [input, setInput] = useState('');

  const addTodo = () => {
    if (input.trim() === '') return;
    setTodos([...todos, { text: input, completed: false }]);
    setInput('');
  };

  const removeTodo = (index) => {
    const newTodos = todos.slice();
    newTodos.splice(index, 1);
    setTodos(newTodos);
  };

  const toggleTodo = (index) => {
    const newTodos = todos.slice();
    newTodos[index] = {
      ...newTodos[index],
      completed: !newTodos[index].completed,
    };
    setTodos(newTodos);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      addTodo();
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: '2rem auto', fontFamily: 'sans-serif' }}>
      <h1>Todo List</h1>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Add a new todo"
          style={{ flex: 1, padding: '0.5rem' }}
        />
        <button onClick={addTodo} style={{ padding: '0.5rem 1rem' }}>
          Add
        </button>
      </div>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {todos.map((todo, index) => (
          <li
            key={index}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.5rem',
              borderBottom: '1px solid #eee',
            }}
          >
            <input
              type="checkbox"
              checked={todo.completed}
              onChange={() => toggleTodo(index)}
            />
            <span
              style={{
                flex: 1,
                textDecoration: todo.completed ? 'line-through' : 'none',
                color: todo.completed ? '#888' : '#000',
              }}
            >
              {todo.text}
            </span>
            <button onClick={() => removeTodo(index)}>Remove</button>
          </li>
        ))}
      </ul>
      {todos.length === 0 && (
        <p style={{ textAlign: 'center', color: '#888' }}>No todos yet.</p>
      )}
    </div>
  );
}

export default TodoList;
