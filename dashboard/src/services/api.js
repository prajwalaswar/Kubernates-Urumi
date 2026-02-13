import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const storeAPI = {
  // Get all stores
  getAllStores: async () => {
    const response = await api.get('/stores');
    return response.data;
  },

  // Get single store
  getStore: async (storeName) => {
    const response = await api.get(`/stores/${storeName}`);
    return response.data;
  },

  // Create new store
  createStore: async (storeName, ownerEmail) => {
    const response = await api.post('/stores', {
      store_name: storeName,
      owner_email: ownerEmail,
    });
    return response.data;
  },

  // Delete store
  deleteStore: async (storeName) => {
    const response = await api.delete(`/stores/${storeName}`);
    return response.data;
  },
};

export default api;
