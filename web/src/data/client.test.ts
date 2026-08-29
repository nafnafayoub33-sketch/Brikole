import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, api } from '@/data/client'
import { sessionStore } from '@/data/session'

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response
}

describe('api client', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    sessionStore.clear()
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns the parsed body on success', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { id: 1 }))
    await expect(api<{ id: number }>('/thing')).resolves.toEqual({ id: 1 })
  })

  it('turns an error body into an ApiError carrying the code', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(409, { code: 'phone_taken', details: { field: 'phone' } }),
    )

    const error = await api('/auth/register', { method: 'POST' }).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).code).toBe('phone_taken')
    expect((error as ApiError).status).toBe(409)
    expect((error as ApiError).details).toEqual({ field: 'phone' })
  })

  it('reports a dead network as its own code rather than a generic failure', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    const error = (await api('/thing').catch((e: unknown) => e)) as ApiError
    expect(error.isNetwork).toBe(true)
  })

  it('sends the access token when there is one', async () => {
    sessionStore.set('token-abc')
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {}))

    await api('/auth/me')

    const headers = fetchMock.mock.calls[0]![1].headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer token-abc')
  })

  it('refreshes once on an expired token and replays the request', async () => {
    sessionStore.set('stale')
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { code: 'token_expired' }))
      .mockResolvedValueOnce(jsonResponse(200, { access_token: 'fresh', expires_in: 1800 }))
      .mockResolvedValueOnce(jsonResponse(200, { id: 7 }))

    await expect(api<{ id: number }>('/auth/me')).resolves.toEqual({ id: 7 })

    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[1]![0]).toContain('/auth/refresh')
    const replayHeaders = fetchMock.mock.calls[2]![1].headers as Record<string, string>
    expect(replayHeaders.Authorization).toBe('Bearer fresh')
    expect(sessionStore.get()).toBe('fresh')
  })

  it('gives up and clears the session when the refresh cookie is gone too', async () => {
    sessionStore.set('stale')
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { code: 'token_expired' }))
      .mockResolvedValueOnce(jsonResponse(401, { code: 'not_authenticated' }))

    const error = (await api('/auth/me').catch((e: unknown) => e)) as ApiError

    expect(error.code).toBe('token_expired')
    expect(sessionStore.get()).toBeNull()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('does not retry a 403 — the answer would be the same', async () => {
    sessionStore.set('token')
    fetchMock.mockResolvedValueOnce(jsonResponse(403, { code: 'forbidden' }))

    await expect(api('/admin/overview')).rejects.toBeInstanceOf(ApiError)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('shares one refresh between concurrent callers', async () => {
    // Rotation means a second refresh would invalidate the first caller's
    // brand-new token.
    sessionStore.set('stale')
    fetchMock.mockImplementation((url: string) => {
      if (url.includes('/auth/refresh')) {
        return Promise.resolve(jsonResponse(200, { access_token: 'fresh', expires_in: 1800 }))
      }
      const header = fetchMock.mock.calls.at(-1)?.[1]?.headers as Record<string, string>
      if (header?.Authorization === 'Bearer stale') {
        return Promise.resolve(jsonResponse(401, { code: 'token_expired' }))
      }
      return Promise.resolve(jsonResponse(200, { ok: true }))
    })

    await Promise.all([api('/a'), api('/b'), api('/c')])

    const refreshCalls = fetchMock.mock.calls.filter(([url]) =>
      String(url).includes('/auth/refresh'),
    )
    expect(refreshCalls).toHaveLength(1)
  })

  it('returns undefined for 204 rather than trying to parse a body', async () => {
    fetchMock.mockResolvedValueOnce({ ok: true, status: 204 } as Response)
    await expect(api('/auth/logout', { method: 'POST' })).resolves.toBeUndefined()
  })
})
