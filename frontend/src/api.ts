import type { AuthResponse } from './types'

const TOKEN_KEY = 'aethra.token'

function defaultApiUrl(): string {
  const host = window.location.hostname
  if (host.endsWith('github.io')) return 'https://viniciuskhan-aethra.hf.space'
  if (['localhost', '127.0.0.1'].includes(host) && window.location.port && window.location.port !== '8081') {
    return 'http://127.0.0.1:8081'
  }
  return window.location.origin === 'null' ? 'http://127.0.0.1:8081' : window.location.origin
}

export const API_URL = defaultApiUrl().replace(/\/$/, '')

export function getToken(): string {
  return sessionStorage.getItem(TOKEN_KEY) ?? ''
}

export function saveAuth(auth: AuthResponse): void {
  sessionStorage.setItem(TOKEN_KEY, auth.access_token)
}

export function clearAuth(): void {
  sessionStorage.removeItem(TOKEN_KEY)
}

function errorMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail?: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (item && typeof item === 'object' && 'msg' in item ? String(item.msg) : ''))
        .filter(Boolean)
        .join(' · ')
    }
  }
  return `Não foi possível concluir (HTTP ${status}).`
}

type ApiOptions = Omit<RequestInit, 'body'> & { body?: unknown }

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body !== undefined) headers.set('Content-Type', 'application/json; charset=utf-8')

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  if (response.status === 204) return undefined as T
  const payload: unknown = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/auth/')) {
      clearAuth()
      window.dispatchEvent(new Event('aethra:unauthorized'))
    }
    throw new Error(errorMessage(payload, response.status))
  }
  return payload as T
}
