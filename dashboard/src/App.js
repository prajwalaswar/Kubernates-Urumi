import React, { useState, useEffect } from 'react';
import { storeAPI } from './services/api';
import './App.css';

function App() {
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Create store form state
  const [storeName, setStoreName] = useState('');
  const [ownerEmail, setOwnerEmail] = useState('');
  const [creating, setCreating] = useState(false);
  const [createdStoreData, setCreatedStoreData] = useState(null);

  // Fetch stores on component mount
  useEffect(() => {
    fetchStores();
  }, []);

  const fetchStores = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await storeAPI.getAllStores();
      setStores(data.stores || []);
    } catch (err) {
      setError('Failed to fetch stores: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateStore = async (e) => {
    e.preventDefault();
    
    // Validate store name
    const storeNameRegex = /^[a-z0-9-]+$/;
    if (!storeNameRegex.test(storeName)) {
      setError('Store name must be lowercase alphanumeric with hyphens only');
      return;
    }

    if (storeName.length < 3 || storeName.length > 20) {
      setError('Store name must be 3-20 characters');
      return;
    }

    try {
      setCreating(true);
      setError('');
      setSuccess('');
      setCreatedStoreData(null);
      
      const result = await storeAPI.createStore(storeName, ownerEmail);
      
      setSuccess(`Store '${storeName}' created successfully!`);
      setCreatedStoreData(result.data);
      
      // Reset form
      setStoreName('');
      setOwnerEmail('');
      
      // Refresh store list
      setTimeout(() => fetchStores(), 2000);
      
    } catch (err) {
      setError('Failed to create store: ' + (err.response?.data?.detail || err.message));
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteStore = async (storeNameToDelete) => {
    if (!window.confirm(`Are you sure you want to delete store '${storeNameToDelete}'? This action cannot be undone.`)) {
      return;
    }

    try {
      setError('');
      setSuccess('');
      await storeAPI.deleteStore(storeNameToDelete);
      setSuccess(`Store '${storeNameToDelete}' deleted successfully!`);
      
      // Refresh store list
      fetchStores();
    } catch (err) {
      setError('Failed to delete store: ' + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🏪 Store Provisioning Platform</h1>
        <p>Kubernetes-based WooCommerce Store Management</p>
      </header>

      <div className="container">
        {/* Create Store Form */}
        <div className="create-store-section">
          <h2>Create New Store</h2>
          <form onSubmit={handleCreateStore} className="create-form">
            <div className="form-group">
              <label htmlFor="storeName">Store Name:</label>
              <input
                type="text"
                id="storeName"
                value={storeName}
                onChange={(e) => setStoreName(e.target.value)}
                placeholder="my-awesome-store"
                pattern="[a-z0-9-]+"
                minLength="3"
                maxLength="20"
                required
                disabled={creating}
              />
              <small>Lowercase, alphanumeric, hyphens only (3-20 chars)</small>
            </div>

            <div className="form-group">
              <label htmlFor="ownerEmail">Owner Email:</label>
              <input
                type="email"
                id="ownerEmail"
                value={ownerEmail}
                onChange={(e) => setOwnerEmail(e.target.value)}
                placeholder="owner@example.com"
                required
                disabled={creating}
              />
            </div>

            <button type="submit" className="btn btn-primary" disabled={creating}>
              {creating ? 'Creating Store... (2-3 min)' : 'Create Store'}
            </button>
          </form>

          {/* Created Store Credentials */}
          {createdStoreData && (
            <div className="credentials-box">
              <h3>✅ Store Created Successfully!</h3>
              <div className="credentials-content">
                <p><strong>Store Name:</strong> {createdStoreData.store_name}</p>
                <p><strong>Store URL:</strong> <a href={createdStoreData.url} target="_blank" rel="noopener noreferrer">{createdStoreData.url}</a></p>
                <p><strong>Admin URL:</strong> <a href={createdStoreData.admin_url} target="_blank" rel="noopener noreferrer">{createdStoreData.admin_url}</a></p>
                <p><strong>Username:</strong> {createdStoreData.credentials?.username}</p>
                <p><strong>Password:</strong> <code>{createdStoreData.credentials?.password}</code></p>
                <small>⚠️ Save these credentials! They won't be shown again.</small>
              </div>
            </div>
          )}
        </div>

        {/* Messages */}
        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        {/* Store List */}
        <div className="store-list-section">
          <div className="section-header">
            <h2>Provisioned Stores ({stores.length})</h2>
            <button onClick={fetchStores} className="btn btn-secondary" disabled={loading}>
              {loading ? 'Refreshing...' : '🔄 Refresh'}
            </button>
          </div>

          {loading && <p className="loading">Loading stores...</p>}

          {!loading && stores.length === 0 && (
            <p className="empty-state">No stores provisioned yet. Create your first store above!</p>
          )}

          {!loading && stores.length > 0 && (
            <table className="store-table">
              <thead>
                <tr>
                  <th>Store Name</th>
                  <th>Namespace</th>
                  <th>Status</th>
                  <th>Created At</th>
                  <th>Store URL</th>
                  <th>Admin URL</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {stores.map((store) => (
                  <tr key={store.store_name}>
                    <td><strong>{store.store_name}</strong></td>
                    <td><code>{store.namespace}</code></td>
                    <td>
                      <span className={`status ${store.status === 'Active' ? 'status-active' : 'status-inactive'}`}>
                        {store.status}
                      </span>
                    </td>
                    <td>
                      <small>{store.created_at ? new Date(store.created_at).toLocaleString() : 'N/A'}</small>
                    </td>
                    <td>
                      <a href={store.url} target="_blank" rel="noopener noreferrer" className="link">
                        View Store
                      </a>
                    </td>
                    <td>
                      <a href={store.admin_url} target="_blank" rel="noopener noreferrer" className="link">
                        Admin Panel
                      </a>
                    </td>
                    <td>
                      <button
                        onClick={() => handleDeleteStore(store.store_name)}
                        className="btn btn-danger btn-sm"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <footer className="App-footer">
        <p>Built with React + FastAPI + Kubernetes + Helm</p>
      </footer>
    </div>
  );
}

export default App;
