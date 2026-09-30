import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext.jsx';
import { requestForgotPassword } from '../services/auth.js';

const EyeIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const EyeOffIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
    <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
    <path d="M6.61 6.61A13.52 13.52 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
    <line x1="2" x2="22" y1="2" y2="22" />
  </svg>
);

export default function LoginPage({ onNavigateRegister }) {
  const { login } = useAuth();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
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
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              className={!password && errorMessage ? 'input-error' : ''}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              style={{ paddingRight: '2.5rem', width: '100%' }}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              title={showPassword ? 'Hide password' : 'Show password'}
              style={{
                position: 'absolute',
                right: '0.6rem',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '0.2rem',
                color: '#64748b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {showPassword ? <EyeOffIcon /> : <EyeIcon />}
            </button>
          </div>
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
