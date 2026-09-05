import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api, restoreSession } from '@/data/client'
import { platformStore, usePlatformStore } from '@/data/platform'
import { sessionStore } from '@/data/session'

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response
}

/**
 * S3 and S4 — the client noticing that the app should stop being an app.
 *
 * The interesting rule is the asymmetry: maintenance is about the platform, so
 * any answer disproves it; a suspension is about the person, and the public
 * endpoints keep answering 200 for a suspended account.
 */
describe('platform blocks', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    sessionStore.clear()
    platformStore.clear()
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  const block = () => usePlatformStore.getState().block

  it('records maintenance from any request, signed in or not', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(503, { code: 'maintenance' }))

    await api('/trades', { authenticated: false }).catch(() => null)

    expect(block()).toBe('maintenance')
  })

  it('records a suspension with the reason and the date', async () => {
    sessionStore.set('token')
    fetchMock.mockResolvedValueOnce(
      jsonResponse(403, {
        code: 'account_suspended',
        details: { until: '2026-10-01T00:00:00Z', reason: 'Faux devis' },
      }),
    )

    await api('/auth/me').catch(() => null)

    expect(block()).toBe('suspended')
    expect(usePlatformStore.getState().suspension).toEqual({
      until: '2026-10-01T00:00:00Z',
      reason: 'Faux devis',
    })
  })

  it('treats a permanent suspension as one without a date', async () => {
    sessionStore.set('token')
    fetchMock.mockResolvedValueOnce(
      jsonResponse(403, { code: 'account_suspended', details: {} }),
    )

    await api('/auth/me').catch(() => null)

    expect(usePlatformStore.getState().suspension).toEqual({ until: null, reason: null })
  })

  it('lifts maintenance as soon as anything answers', async () => {
    // The gate reads the switch on every request, so there is no cache to wait
    // out: one successful call is the whole recovery.
    platformStore.close('maintenance', null)
    fetchMock.mockResolvedValueOnce(jsonResponse(200, []))

    await api('/trades', { authenticated: false })

    expect(block()).toBeNull()
  })

  it('does not lift a suspension because a public call succeeded', async () => {
    // The bug this pins down: the landing page loads its trades, that 200
    // arrives, and S3 vanishes off a suspended account's screen.
    platformStore.close('suspended', { until: null, reason: null })
    fetchMock.mockResolvedValueOnce(jsonResponse(200, []))

    await api('/trades', { authenticated: false })

    expect(block()).toBe('suspended')
  })

  it('notices a suspension on the refresh that starts a reloaded page', async () => {
    // The first call a reloaded app makes is /auth/refresh, and it does not go
    // through `send`. Without this the person is bounced to sign-in, where a
    // suspension looks exactly like a session that expired.
    fetchMock.mockResolvedValueOnce(
      jsonResponse(403, {
        code: 'account_suspended',
        details: { until: null, reason: 'Faux devis' },
      }),
    )

    await expect(restoreSession()).resolves.toBe(false)

    expect(block()).toBe('suspended')
    expect(usePlatformStore.getState().suspension?.reason).toBe('Faux devis')
  })

  it('lifts it when a call made with his token succeeds', async () => {
    // A timed suspension lifts itself on the way in, so "try again" has to be
    // able to actually clear the screen.
    platformStore.close('suspended', { until: null, reason: null })
    sessionStore.set('token')
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { id: 1 }))

    await api('/auth/me')

    expect(block()).toBeNull()
  })
})
