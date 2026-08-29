/**
 * Which city the visitor is shopping in.
 *
 * It sits above every screen that counts or lists tradesmen, because the
 * answer is meaningless without it: forty plumbers is a great number until you
 * learn they are all in Casablanca and the leak is in Meknès. Remembered
 * between visits, since a person's city rarely changes between two of them.
 */

import { create } from 'zustand'

const STORAGE_KEY = 'brikole.city'

function readStored(): number | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return null
    const parsed = Number(stored)
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null
  } catch {
    // Site data blocked. "All cities" is a fine answer.
    return null
  }
}

interface CityState {
  /** Null means the whole country. */
  cityId: number | null
  setCity: (cityId: number | null) => void
}

export const useCityStore = create<CityState>((set) => ({
  cityId: readStored(),
  setCity: (cityId) => {
    try {
      if (cityId === null) localStorage.removeItem(STORAGE_KEY)
      else localStorage.setItem(STORAGE_KEY, String(cityId))
    } catch {
      // Not remembering it is not a reason to fail to apply it.
    }
    set({ cityId })
  },
}))
