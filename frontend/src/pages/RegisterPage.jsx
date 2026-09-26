import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext.jsx';

export default function RegisterPage({ onNavigateLogin }) {
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    fullName: '',
    username: '',
    email: '',
    mobile: '',
    password: '',
    confirmPassword: '',
    role: 'user',
    adminKey: '',
  });
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [validationErrors, setValidationErrors] = useState({});

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setValidationErrors({ ...validationErrors, [e.target.name]: '' });
  };

  const validate = () => {
    const errors = {};
    if (!formData.fullName.trim()) errors.fullName = 'Full Name is required';
    if (!formData.username.trim()) errors.username = 'Username is required';
    if (!formData.email.trim()) errors.email = 'Email is required';
    if (!formData.mobile.trim()) errors.mobile = 'Mobile Number is required';
    if (!formData.password) errors.password = 'Password is required';
    if (formData.password && formData.password.length < 8) errors.password = 'Password must be at least 8 characters';
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
            placeholder="johndoe"
          />
          {validationErrors.username && <span className="field-error">{validationErrors.username}</span>}
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
            <option value="user">Normal User</option>
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
          <input
            id="password"
            name="password"
            type="password"
            className={validationErrors.password ? 'input-error' : ''}
            value={formData.password}
            onChange={handleChange}
            placeholder="At least 8 characters"
          />
          {validationErrors.password && <span className="field-error">{validationErrors.password}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="confirmPassword">Confirm Password *</label>
          <input
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            className={validationErrors.confirmPassword ? 'input-error' : ''}
            value={formData.confirmPassword}
            onChange={handleChange}
            placeholder="Re-enter password"
          />
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
