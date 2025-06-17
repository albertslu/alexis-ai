import axios from 'axios';

// Create an axios instance with base URL for Flask backend server
const instance = axios.create({
  baseURL: window.isElectron ? window.API_BASE_URL : (process.env.REACT_APP_API_URL || 'http://localhost:5002'),  // Flask backend server
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true  // Enable sending cookies with cross-origin requests
});

// Add request interceptor for authentication and debugging
instance.interceptors.request.use(
  config => {
    // Add JWT token to headers if available
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    console.log('Making request to:', config.baseURL + config.url);
    console.log('Request details:', {
      method: config.method,
      headers: config.headers,
      data: config.data,
      withCredentials: config.withCredentials
    });
    return config;
  },
  error => {
    console.error('Request error interceptor:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for debugging
instance.interceptors.response.use(
  response => {
    console.log('Response received:', {
      status: response.status,
      statusText: response.statusText,
      data: response.data,
      headers: response.headers
    });
    return response;
  },
  error => {
    console.error('Response error interceptor:', error);
    if (error.response) {
      console.error('Error response data:', error.response.data);
      console.error('Error response status:', error.response.status);
      console.error('Error response headers:', error.response.headers);
    } else if (error.request) {
      console.error('Error request:', error.request);
    } else {
      console.error('Error message:', error.message);
    }
    console.error('Error config:', error.config);
    return Promise.reject(error);
  }
);

export default instance;
