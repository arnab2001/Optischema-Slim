const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api'
const DEFAULT_TENANT_ID = '00000000-0000-0000-0000-000000000001'

interface ApiResponse<T> {
  data?: T
  error?: string
}

class ApiClient {
  private tenantId: string = DEFAULT_TENANT_ID

  setTenantId(id: string) {
    // Basic UUID format check; fallback to default if invalid
    if (typeof id === 'string' && id.length >= 36) {
      this.tenantId = id
    } else {
      this.tenantId = DEFAULT_TENANT_ID
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    try {
      // Get auth token from localStorage or other storage
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-Tenant-ID': this.tenantId,
        ...options.headers,
      };

      // Add authorization header if token exists
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE}${endpoint}`, {
        headers,
        ...options,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return { data }
    } catch (error) {
      return { error: error instanceof Error ? error.message : 'Unknown error' }
    }
  }

  // Metrics endpoints
  async getMetrics() {
    return this.request('/metrics/raw')
  }

  async getMetricsSummary() {
    return this.request('/metrics/summary')
  }

  async getHotQueries() {
    return this.request('/metrics/hot')
  }

  // Suggestions endpoints
  async getSuggestions() {
    return this.request('/suggestions/latest')
  }

  async getSuggestion(id: string) {
    return this.request(`/suggestions/${id}`)
  }

  async applySuggestion(suggestionId: string) {
    return this.request('/suggestions/apply', {
      method: 'POST',
      body: JSON.stringify({ suggestion_id: suggestionId }),
    })
  }

  // Analysis endpoints
  async analyzeQuery(query: string) {
    return this.request('/analysis/query', {
      method: 'POST',
      body: JSON.stringify({ query }),
    })
  }

  async getAnalysisStatus() {
    return this.request('/analysis/status')
  }

  // Health endpoint
  async getHealth() {
    return this.request('/health')
  }

  // Authentication methods
  async login(email: string, password: string) {
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        throw new Error(`Login failed! status: ${response.status}`);
      }

      const data = await response.json();

      // Store token in localStorage
      if (data.access_token && typeof window !== 'undefined') {
        localStorage.setItem('auth_token', data.access_token);
      }

      return { data };
    } catch (error) {
      return { error: error instanceof Error ? error.message : 'Unknown error' };
    }
  }

  async logout() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
  }

  async getAuthToken(): Promise<string | null> {
    return typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  }

  async setAuthToken(token: string) {
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token);
    }
  }
}

export const apiClient = new ApiClient() 
