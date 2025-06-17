import axios from 'axios';

// Create a dedicated API client with the correct base URL
const API_BASE_URL = 'http://localhost:5002';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  withCredentials: true // Important for CORS with credentials
});

// Add request interceptor for debugging
apiClient.interceptors.request.use(
  config => {
    console.log(`Making ${config.method.toUpperCase()} request to: ${config.baseURL}${config.url}`);
    return config;
  },
  error => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for debugging
apiClient.interceptors.response.use(
  response => {
    console.log(`Response from ${response.config.url}:`, response.status);
    return response;
  },
  error => {
    console.error('Response error:', error.message);
    if (error.response) {
      console.error('Error response:', error.response.data);
    }
    return Promise.reject(error);
  }
);

export default apiClient;
