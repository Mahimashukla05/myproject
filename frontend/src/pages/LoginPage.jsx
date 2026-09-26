import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext.jsx';
import { requestForgotPassword } from '../services/auth.js';

export default function LoginPage({ onNavigateRegister }) {
  const { login } = useAuth();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [forgotOpen, setForgotOpen] = useState(false);
  const [forgotInput, setForgotInput] = useState('');
  const [forgotMessage, setForgotMessage] = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    if (!identifier || !password) {
      setErrorMessage('Please enter both identifier and password.');
      return;
    }
    setLoading(true);
    try {
      await login({ identifier, password });
    } catch (err) {
      setErrorMessage(err.message || 'Login failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotSubmit = async (e) => {
    e.preventDefault();
    if (!forgotInput) return;
    setForgotLoading(true);
    try {
      const res = await requestForgotPassword(forgotInput);
      setForgotMessage(res.message);
    } catch (err) {
      setForgotMessage(err.message);
    } finally {
      setForgotLoading(false);
    }
  };

  return (
    <div className="auth-card">
      <h2>Account Login</h2>
      {errorMessage && <div className="alert alert-error">{errorMessage}</div>}

      <form noValidate onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="identifier">Username, Email, or Mobile</label>
          <input
            id="identifier"
            type="text"
            className={!identifier && errorMessage ? 'input-error' : ''}
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="Enter username, email, or mobile"
          />
        </div>

        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            className={!password && errorMessage ? 'input-error' : ''}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
          />
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>

      <div className="auth-footer">
        <button type="button" className="btn-link" onClick={() => setForgotOpen(!forgotOpen)}>
          Forgot Password?
        </button>
        <button type="button" className="btn-link" onClick={onNavigateRegister}>
          Need an account? Register
        </button>
      </div>

      {forgotOpen && (
        <div className="forgot-panel">
          <h3>Reset Password</h3>
          {forgotMessage && <div className="alert alert-info">{forgotMessage}</div>}
          <form noValidate onSubmit={handleForgotSubmit}>
            <div className="form-group">
              <label htmlFor="forgotInput">Identifier (Username/Email/Mobile)</label>
              <input
                id="forgotInput"
                type="text"
                value={forgotInput}
                onChange={(e) => setForgotInput(e.target.value)}
                placeholder="Enter your identifier"
              />
            </div>
            <button type="submit" className="btn btn-secondary" disabled={forgotLoading}>
              {forgotLoading ? 'Submitting...' : 'Request Reset'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
