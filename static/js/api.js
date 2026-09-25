/**
 * POS API Client Module
 * Provides promise-based communication with the Python backend.
 */

const API = {
  async request(url, options = {}) {
    const defaultHeaders = {
      'Content-Type': 'application/json',
    };

    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok || data.success === false) {
        throw new Error(data.error || `HTTP error ${response.status}`);
      }
      return data;
    } catch (err) {
      console.error(`API Error [${options.method || 'GET'} ${url}]:`, err);
      throw err;
    }
  },

  async checkSync() {
    const res = await this.request('/api/sync');
    return res.sync || {};
  },

  async getSettings() {
    const res = await this.request('/api/settings');
    return res.settings || {};
  },

  async updateSettings(updates) {
    const res = await this.request('/api/settings', {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
    return res.settings;
  },

  async getProducts(category = null, search = null) {
    const params = new URLSearchParams();
    if (category && category !== 'All' && category !== 'Top Picks') params.append('category', category);
    if (search && search.trim()) params.append('q', search.trim());

    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await this.request(`/api/products${qs}`);
    return res.products || [];
  },

  async lookupBarcode(code) {
    const res = await this.request(`/api/products?barcode=${encodeURIComponent(code)}`);
    return res.product;
  },

  async addProduct(product) {
    const res = await this.request('/api/products', {
      method: 'POST',
      body: JSON.stringify(product),
    });
    return res.product;
  },

  async updateProduct(id, updates) {
    const res = await this.request(`/api/products/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
    return res.product;
  },

  async deleteProduct(id) {
    const res = await this.request(`/api/products/${id}`, {
      method: 'DELETE',
    });
    return res.message;
  },

  async checkout(items, cashReceived, cashier = 'Terminal 01') {
    const res = await this.request('/api/checkout', {
      method: 'POST',
      body: JSON.stringify({
        items,
        cash_received: cashReceived,
        cashier,
      }),
    });
    return res.transaction;
  },

  async getTransactions() {
    const res = await this.request('/api/transactions');
    return res.transactions || [];
  },

  async getStats() {
    const res = await this.request('/api/stats');
    return res.stats || {};
  }
};
