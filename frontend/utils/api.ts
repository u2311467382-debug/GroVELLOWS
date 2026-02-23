import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { Platform } from 'react-native';

// Get backend URL with fallbacks
const getBackendUrl = () => {
  // First try expo config
  const expoUrl = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL;
  if (expoUrl) return expoUrl;
  
  // Then try process.env
  const envUrl = process.env.EXPO_PUBLIC_BACKEND_URL;
  if (envUrl) return envUrl;
  
  // For web, use window location origin
  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    return window.location.origin;
  }
  
  // Default fallback
  return 'https://multi-user-preview.preview.emergentagent.com';
};

const BACKEND_URL = getBackendUrl();
console.log('Using backend URL:', BACKEND_URL);

const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;
