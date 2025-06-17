import React, { createContext, useState, useEffect, useContext } from 'react';
import axios from '../api/axios';

// Create the authentication context
const AuthContext = createContext();

// Custom hook to use the auth context
export const useAuth = () => {
  return useContext(AuthContext);
};

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Check if the user is authenticated on component mount
  useEffect(() => {
    const token = localStorage.getItem('token');
    
    if (token) {
      fetchUserProfile(token);
    } else {
      setLoading(false);
    }
  }, []);
  
  // Fetch the user's profile using the token
  const fetchUserProfile = async (token) => {
    try {
      console.log('Fetching user profile with token:', token.substring(0, 10) + '...');
      
      const response = await axios.get('/api/auth/me', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      console.log('User profile fetched successfully:', response.data);
      
      // Store the user data in state
      setCurrentUser(response.data);
      
      // Explicitly store the user ID in localStorage for OAuth flows
      // Backend might return either _id (MongoDB) or id field
      const userId = response.data && (response.data._id || response.data.id);
      if (userId) {
        localStorage.setItem('userId', userId);
        console.log('Stored user ID in localStorage:', userId);
      } else {
        console.error('No user ID found in response data:', response.data);
      }
      
      setError(null);
    } catch (err) {
      console.error('Error fetching user profile:', err);
      console.error('Error details:', err.response ? err.response.data : 'No response data');
      setError('Session expired. Please login again.');
      logout();
    } finally {
      setLoading(false);
    }
  };
  
  // Login the user with a token
  const login = async (token) => {
    localStorage.setItem('token', token);
    await fetchUserProfile(token);
  };
  
  // Logout the user
  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('userId');
    setCurrentUser(null);
    
    // Call the logout endpoint
    axios.post('/api/auth/logout')
      .catch(err => console.error('Error logging out:', err));
  };
  
  // Get the auth header for API requests
  const getAuthHeader = () => {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  };
  
  // Check if the user is authenticated
  const isAuthenticated = () => {
    return !!currentUser;
  };
  
  // The context value
  const value = {
    currentUser,
    loading,
    error,
    login,
    logout,
    getAuthHeader,
    isAuthenticated
  };
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
