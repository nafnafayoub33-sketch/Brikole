/**
 * S3 and S4 — the two answers that replace the app rather than appear in it.
 *
 * Both arrive the same way: any request, anywhere, comes back with a code that
 * says the app should not be running. A screen cannot catch that on its own —
 * an anonymous visitor on the landing page never touches `useSession`, and the
 * failing call could be any of a dozen. So the api client reports it here, and
 * one component at the root reads it.
 *
 * Cleared on a successful response, so the platform reopening or a suspension
 * being lifted needs nothing more than the next call succeeding.
 */

import { create } from 'zustand'

export type PlatformBlock = 'maintenance' | 'suspended'

export interface Suspension {
  /** ISO date, or null for a permanent suspension. */
  until: string | null
  reason: string | null
}

interface PlatformState {
  block: PlatformBlock | null
  suspension: Suspension | null
  close: (block: PlatformBlock, suspension: Suspension | null) => void
  open: () => void
}

export const usePlatformStore = create<PlatformState>((set) => ({
  block: null,
  suspension: null,
  close: (block, suspension) => set({ block, suspension }),
  open: () => set({ block: null, suspension: null }),
}))

/** For the api client, which is not a component and cannot use the hook. */
export const platformStore = {
  close: (block: PlatformBlock, suspension: Suspension | null) =>
    usePlatformStore.getState().close(block, suspension),

  /**
   * A request came back fine. What that clears depends on which block is up.
   *
   * Maintenance is about the platform, so any answer at all disproves it. A
   * suspension is about the *person*, and the public endpoints keep answering
   * 200 for a suspended account — so clearing on those would tear the screen
   * down the moment the landing page loaded its trades. Only a call made with
   * his token says the suspension is over.
   */
  succeeded: ({ authenticated }: { authenticated: boolean }) => {
    const { block } = usePlatformStore.getState()
    if (block === null) return
    if (block === 'maintenance' || authenticated) usePlatformStore.getState().open()
  },

  /** Signing out ends a suspension screen: it belonged to that session. */
  clear: () => usePlatformStore.getState().open(),
}
