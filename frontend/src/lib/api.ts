import axios from 'axios';

const api = axios.create({
  // Prefer the build-time env var (set in docker-compose / .env.local); fall back
  // to localhost for a plain `npm run dev`.
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
    }
    // Format error message for UI
    const message = error.response?.data?.detail || "An unexpected error occurred.";
    error.message = message;
    return Promise.reject(error);
  }
);

export default api;
