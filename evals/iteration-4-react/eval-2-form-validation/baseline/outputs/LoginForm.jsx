import { useState } from 'react';

function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = () => {
    // TODO: add actual validation (email format, password strength, required fields)
    console.log('Submitting:', { email, password });
  };

  return (
    <div className="login-form">
      <input
        type="email"
        placeholder="Enter your email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <input
        type="password"
        placeholder="Enter your password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <div
        className="submit-button"
        onClick={handleSubmit}
        style={{
          padding: '10px 20px',
          background: '#4f46e5',
          color: 'white',
          textAlign: 'center',
          cursor: 'pointer',
          borderRadius: '4px',
          userSelect: 'none',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = '#4338ca')}
        onMouseLeave={(e) => (e.currentTarget.style.background = '#4f46e5')}
      >
        Submit
      </div>
    </div>
  );
}

export default LoginForm;
