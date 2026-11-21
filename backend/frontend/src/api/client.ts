import axios from 'axios'

export interface ApiErrorPayload {
  detail?: string | Array<{ msg?: string }>
}

export const apiClient = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1',
  timeout: 10_000,
  headers: {
    Accept: 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('careerlens_access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError<ApiErrorPayload>(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail) && detail[0]?.msg) {
      return detail[0].msg
    }
    if (!error.response) {
      return 'The CareerLens AI API could not be reached.'
    }
  }

  return 'The request could not be completed.'
}
