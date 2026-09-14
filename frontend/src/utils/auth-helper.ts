/**
 * Get authentication token from localStorage
 * Used by admin pages and other components that need direct token access
 */
export const getAuthToken = (): string => {
  const authStorage = localStorage.getItem('auth-storage')
  if (authStorage) {
    try {
      const { state } = JSON.parse(authStorage)
      return state?.accessToken || ''
    } catch {
      return ''
    }
  }
  return ''
}

/**
 * Get authorization headers for API requests
 */
export const getAuthHeaders = (): Record<string, string> => {
  const token = getAuthToken()
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
}
