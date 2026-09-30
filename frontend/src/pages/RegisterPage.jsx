import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext.jsx';

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

export default function RegisterPage({ onNavigateLogin }) {
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    fullName: '',
    username: '',
    email: '',
    mobile: '',
    password: '',
    confirmPassword: '',
    role: 'operator',
    adminKey: '',
  });

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [validationErrors, setValidationErrors] = useState({});
  const [focusedField, setFocusedField] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const getRequirementsStatus = (value) => {
    const val = value || '';
    return {
      length: val.length >= 8,
      uppercase: /[A-Z]/.test(val),
      lowercase: /[a-z]/.test(val),
      number: /[0-9]/.test(val),
      special: /[^A-Za-z0-9]/.test(val),
    };
  };

  const isAllValid = (status) => {
    return status.length && status.uppercase && status.lowercase && status.number && status.special;
  };

  const usernameReqs = getRequirementsStatus(formData.username);
  const passwordReqs = getRequirementsStatus(formData.password);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setValidationErrors({ ...validationErrors, [e.target.name]: '' });
  };

  const validate = () => {
    const errors = {};
    if (!formData.fullName.trim()) errors.fullName = 'Full Name is required';
    if (!formData.username.trim()) {
      errors.username = 'Username is required';
    } else if (!isAllValid(usernameReqs)) {
      errors.username = 'Username must contain at least 8 characters, 1 uppercase, 1 lowercase, 1 number, and 1 special character';
    }

    if (!formData.email.trim()) errors.email = 'Email is required';
    if (!formData.mobile.trim()) errors.mobile = 'Mobile Number is required';

    if (!formData.password) {
      errors.password = 'Password is required';
    } else if (!isAllValid(passwordReqs)) {
      errors.password = 'Password must contain at least 8 characters, 1 uppercase, 1 lowercase, 1 number, and 1 special character';
    }

    if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }
    if (formData.role === 'admin' && !formData.adminKey.trim()) {
      errors.adminKey = 'Admin Key is required for Admin registration';
    }
    return errors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    
    const errors = validate();
    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      setErrorMessage('Please fix highlighted form errors before submitting.');
      return;
    }

    setLoading(true);
    try {
      await register(formData);
      setSuccessMessage('Account registered successfully! You can now log in.');
      setTimeout(() => {
        onNavigateLogin();
      }, 1500);
    } catch (err) {
      setErrorMessage(err.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const renderRequirementsBox = (label, status) => {
    const allPassed = isAllValid(status);
    return (
      <div style={{
        marginTop: '0.4rem',
        padding: '0.6rem 0.75rem',
        backgroundColor: allPassed ? '#f0fdf4' : '#f8fafc',
        border: `1px solid ${allPassed ? '#86efac' : '#cbd5e1'}`,
        borderRadius: '4px',
        fontSize: '0.8rem',
        transition: 'all 0.2s ease'
      }}>
        <div style={{ fontWeight: 600, marginBottom: '0.3rem', color: '#334155' }}>
          {label} must contain:
        </div>
        <ul style={{ listStyle: 'none', paddingLeft: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
          <li style={{ color: status.length ? '#166534' : '#991b1b', fontWeight: status.length ? 600 : 400 }}>
            {status.length ? '✓' : '✗'} At least 8 characters
          </li>
          <li style={{ color: status.uppercase ? '#166534' : '#991b1b', fontWeight: status.uppercase ? 600 : 400 }}>
            {status.uppercase ? '✓' : '✗'} At least 1 uppercase letter
          </li>
          <li style={{ color: status.lowercase ? '#166534' : '#991b1b', fontWeight: status.lowercase ? 600 : 400 }}>
            {status.lowercase ? '✓' : '✗'} At least 1 lowercase letter
          </li>
          <li style={{ color: status.number ? '#166534' : '#991b1b', fontWeight: status.number ? 600 : 400 }}>
            {status.number ? '✓' : '✗'} At least 1 number
          </li>
          <li style={{ color: status.special ? '#166534' : '#991b1b', fontWeight: status.special ? 600 : 400 }}>
            {status.special ? '✓' : '✗'} At least 1 special character
          </li>
        </ul>
        {allPassed && (
          <div style={{ marginTop: '0.4rem', color: '#166534', fontWeight: 700 }}>
            ✓ All {label.toLowerCase()} criteria met!
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="auth-card">
      <h2>Create Account</h2>
      {errorMessage && <div className="alert alert-error">{errorMessage}</div>}
      {successMessage && <div className="alert alert-success">{successMessage}</div>}

      <form noValidate onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="fullName">Full Name *</label>
          <input
            id="fullName"
            name="fullName"
            type="text"
            className={validationErrors.fullName ? 'input-error' : ''}
            value={formData.fullName}
            onChange={handleChange}
            placeholder="John Doe"
          />
          {validationErrors.fullName && <span className="field-error">{validationErrors.fullName}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="username">Username *</label>
          <input
            id="username"
            name="username"
            type="text"
            className={validationErrors.username ? 'input-error' : ''}
            value={formData.username}
            onChange={handleChange}
            onFocus={() => setFocusedField('username')}
            placeholder="e.g. Abcd1234@"
          />
          {validationErrors.username && <span className="field-error">{validationErrors.username}</span>}
          {focusedField === 'username' && renderRequirementsBox('Username', usernameReqs)}
        </div>

        <div className="form-group">
          <label htmlFor="email">Email *</label>
          <input
            id="email"
            name="email"
            type="email"
            className={validationErrors.email ? 'input-error' : ''}
            value={formData.email}
            onChange={handleChange}
            placeholder="john@example.com"
          />
          {validationErrors.email && <span className="field-error">{validationErrors.email}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="mobile">Mobile Number *</label>
          <input
            id="mobile"
            name="mobile"
            type="tel"
            className={validationErrors.mobile ? 'input-error' : ''}
            value={formData.mobile}
            onChange={handleChange}
            placeholder="1234567890"
          />
          {validationErrors.mobile && <span className="field-error">{validationErrors.mobile}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="role">Account Role *</label>
          <select id="role" name="role" value={formData.role} onChange={handleChange}>
            <option value="operator">Operator</option>
            <option value="admin">Admin</option>
          </select>
        </div>

        {formData.role === 'admin' && (
          <div className="form-group">
            <label htmlFor="adminKey">Admin Registration Key *</label>
            <input
              id="adminKey"
              name="adminKey"
              type="password"
              className={validationErrors.adminKey ? 'input-error' : ''}
              value={formData.adminKey}
              onChange={handleChange}
              placeholder="Enter Admin registration secret key"
            />
            {validationErrors.adminKey && <span className="field-error">{validationErrors.adminKey}</span>}
          </div>
        )}

        <div className="form-group">
          <label htmlFor="password">Password *</label>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <input
              id="password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              className={validationErrors.password ? 'input-error' : ''}
              value={formData.password}
              onChange={handleChange}
              onFocus={() => setFocusedField('password')}
              placeholder="At least 8 characters with Upper, Lower, Number & Symbol"
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
          {validationErrors.password && <span className="field-error">{validationErrors.password}</span>}
          {focusedField === 'password' && renderRequirementsBox('Password', passwordReqs)}
        </div>

        <div className="form-group">
          <label htmlFor="confirmPassword">Confirm Password *</label>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type={showConfirmPassword ? 'text' : 'password'}
              className={validationErrors.confirmPassword ? 'input-error' : ''}
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="Re-enter password"
              style={{ paddingRight: '2.5rem', width: '100%' }}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
              title={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
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
              {showConfirmPassword ? <EyeOffIcon /> : <EyeIcon />}
            </button>
          </div>
          {validationErrors.confirmPassword && <span className="field-error">{validationErrors.confirmPassword}</span>}
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Creating Account...' : 'Register'}
        </button>
      </form>

      <div className="auth-footer">
        <button type="button" className="btn-link" onClick={onNavigateLogin}>
          Already have an account? Log in
        </button>
      </div>
    </div>
  );
}
