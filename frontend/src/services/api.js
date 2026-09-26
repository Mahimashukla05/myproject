const RAW_BASE = (import.meta.env.VITE_API_BASE_URL || '').trim();

export function getApiUrl(path) {
  if (!path) return RAW_BASE || '/api';
  const cleanPath = path.startsWith('/') ? path : `/${path}`;

  if (!RAW_BASE) {
    return cleanPath.startsWith('/api') ? cleanPath : `/api${cleanPath}`;
  }

  const base = RAW_BASE.replace(/\/+$/, '');

  if (base.endsWith('/api') && cleanPath.startsWith('/api/')) {
    return `${base}${cleanPath.substring(4)}`;
  }
  if (base.endsWith('/api') && cleanPath === '/api') {
    return base;
  }
  if (!base.endsWith('/api') && !cleanPath.startsWith('/api')) {
    return `${base}/api${cleanPath}`;
  }

  return `${base}${cleanPath}`;
}

export async function apiFetch(path, options = {}) {
  const url = getApiUrl(path);
  const mergedOptions = {
    credentials: 'include',
    ...options,
    headers: {
      ...(options.headers || {}),
    },
  };
  return fetch(url, mergedOptions);
}
