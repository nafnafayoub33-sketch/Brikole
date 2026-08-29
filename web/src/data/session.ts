/**
 * The access token, held in memory only.
 *
 * Deliberately not in localStorage: the long-lived credential is the refresh
 * cookie, which is httpOnly and therefore out of reach of any script on the
 * page. Keeping the short-lived token in a module-scoped store means a reload
 * costs one refresh call and an XSS bug cannot read a 30-day credential.
 */

import { create } from 'zustand'

interface SessionState {
  accessToken: string | null
  setAccessToken: (token: string | null) => void
  clear: () => void
}

export const useSessionStore = create<SessionState>((set) => ({
  accessToken: null,
  setAccessToken: (accessToken) => set({ accessToken }),
  clear: () => set({ accessToken: null }),
}))

/** For the api client, which is not a component and cannot use the hook. */
export const sessionStore = {
  get: () => useSessionStore.getState().accessToken,
  set: (token: string | null) => useSessionStore.getState().setAccessToken(token),
  clear: () => useSessionStore.getState().clear(),
}
