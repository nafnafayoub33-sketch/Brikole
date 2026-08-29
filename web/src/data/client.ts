/**
 * The only place this app talks to the network.
 *
 * Components never call `fetch`. They call a hook in `src/data`, which calls
 * this.
 */

import { sessionStore } from '@/data/session'
import type { AccessToken } from '@/data/types'

const BASE = `${import.meta.env.VITE_API_BASE ?? ''}/api/v1`

/**
 * An error the API described with a code.
 *
 * `code` is the whole point: it maps straight onto `errors.<code>` in
 * `src/lib/i18n.ts`, which is how one server response reads correctly in three
 * languages without the server knowing any of them.
 */
export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: Record<string, unknown>

  constructor(code: string, status: number, details: Record<string, unknown> = {}) {
    super(code)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }

  /** True when retrying might work — the network, not the request. */
  get isNetwork(): boolean {
    return this.code === 'network'
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: unknown
  /** Attach the access token, and refresh it once if it has expired. */
  authenticated?: boolean
  signal?: AbortSignal
}

/**
 * One refresh at a time.
 *
 * Without this, three queries firing on a stale token would each start their
 * own refresh, and rotation means two of them would then be holding a token
 * that has already been replaced.
 */
let inFlightRefresh: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  inFlightRefresh ??= (async () => {
    try {
      const response = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      })
      if (!response.ok) return null
      const token = (await response.json()) as AccessToken
      sessionStore.set(token.access_token)
      return token.access_token
    } catch {
      return null
    } finally {
      inFlightRefresh = null
    }
  })()
  return inFlightRefresh
}

async function send<T>(path: string, options: RequestOptions, token: string | null): Promise<T> {
  const headers: Record<string, string> = {}
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, {
      method: options.method ?? 'GET',
      headers,
      credentials: 'include',
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    })
  } catch {
    throw new ApiError('network', 0)
  }

  if (response.status === 204) return undefined as T

  const payload: unknown = await response.json().catch(() => null)

  if (!response.ok) {
    const body = (payload ?? {}) as { code?: string; details?: Record<string, unknown> }
    throw new ApiError(body.code ?? 'generic', response.status, body.details ?? {})
  }

  return payload as T
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = options.authenticated === false ? null : sessionStore.get()

  try {
    return await send<T>(path, options, token)
  } catch (error) {
    const expired =
      error instanceof ApiError &&
      error.status === 401 &&
      (error.code === 'token_expired' || error.code === 'not_authenticated')

    if (!expired || options.authenticated === false) throw error

    // One retry, with a fresh token. If the refresh cookie is gone too, the
    // original 401 is the honest answer.
    const refreshed = await refreshAccessToken()
    if (!refreshed) {
      sessionStore.clear()
      throw error
    }
    return send<T>(path, options, refreshed)
  }
}

/** Called once at start-up: turns a surviving refresh cookie into a session. */
export async function restoreSession(): Promise<boolean> {
  return (await refreshAccessToken()) !== null
}

export { BASE as API_BASE }
