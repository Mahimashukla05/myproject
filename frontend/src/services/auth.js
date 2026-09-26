let activeCsrfToken = null;

export function setCsrfToken(token) {
  if (token) {
    activeCsrfToken = token;
  }
}

export function getCsrfToken() {
  return activeCsrfToken;
}

export async function registerUser(userData) {
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(activeCsrfToken ? { 'X-CSRF-Token': activeCsrfToken } : {}),
    },
    body: JSON.stringify(userData),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Registration failed');
  }
  return data;
}

export async function loginUser(credentials) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Login failed');
  }
  if (data.csrfToken) {
    setCsrfToken(data.csrfToken);
  }
  return data;
}

export async function logoutUser() {
  const response = await fetch('/api/auth/logout', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(activeCsrfToken ? { 'X-CSRF-Token': activeCsrfToken } : {}),
    },
  });
  const data = await response.json();
  activeCsrfToken = null;
  return data;
}

export async function getCurrentUser() {
  const response = await fetch('/api/auth/me');
  if (!response.ok) {
    activeCsrfToken = null;
    return null;
  }
  const data = await response.json();
  if (data.csrfToken) {
    setCsrfToken(data.csrfToken);
  }
  return data.user;
}

export async function requestForgotPassword(identifier) {
  const response = await fetch('/api/auth/forgot-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Password reset request failed');
  }
  return data;
}
