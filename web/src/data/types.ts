/**
 * The shapes the API returns.
 *
 * Hand-written for now and kept deliberately small. FastAPI publishes an
 * OpenAPI schema at /openapi.json, so once the surface grows past what one
 * file can hold honestly, these get generated from it rather than drifting.
 */

export const ROLES = ['client', 'provider', 'moderator', 'admin'] as const
export type Role = (typeof ROLES)[number]

export type UserStatus = 'active' | 'suspended' | 'deleted'
export type ProviderStatus = 'pending' | 'approved' | 'rejected' | 'suspended'

export interface ProviderSummary {
  id: number
  status: ProviderStatus
  city_id: number
  rating_avg: number
  rating_count: number
  jobs_done: number
}

export interface Me {
  id: number
  phone: string
  full_name: string
  role: Role
  status: UserStatus
  language: string
  city_id: number | null
  avatar_url: string | null
  /** What this role may do. Read this instead of comparing role names. */
  permissions: string[]
  /** Where this role belongs. Mirrors `app.core.permissions.home_path`. */
  home_path: string
  /** Null for a tradesman who has not completed onboarding (M1). */
  provider: ProviderSummary | null
}

export interface AccessToken {
  access_token: string
  token_type: string
  expires_in: number
}

export interface LoginResponse {
  token: AccessToken
  user: Me
}

export interface Trade {
  id: number
  slug: string
  name_ar: string
  name_fr: string
  name_en: string
  icon: string
  sort_order: number
  /** Approved tradesmen in this trade — inside the requested city, if any. */
  providers_count: number
}

export interface City {
  id: number
  slug: string
  name_ar: string
  name_fr: string
  name_en: string
  latitude: number
  longitude: number
}

export interface ProviderCity {
  id: number
  slug: string
  name_ar: string
  name_fr: string
  name_en: string
}

/** One card in the grid: everything a client decides with, and nothing else. */
export interface Provider {
  id: number
  full_name: string
  avatar_url: string | null
  headline: string | null
  status: ProviderStatus
  city: ProviderCity
  trades: Trade[]
  rating_avg: number
  rating_count: number
  jobs_done: number
  years_experience: number
  /** Null when he would rather quote per job — the card omits it. */
  starting_price_centimes: number | null
}

export interface ProviderPhoto {
  id: number
  url: string
}

/** The card, plus what a decision needs a whole page for. */
export interface ProviderProfile extends Provider {
  bio: string
  radius_km: number
  member_since: string
  /** How many reviews gave each score, 1 through 5. */
  rating_breakdown: Record<string, number>
  photos: ProviderPhoto[]
}

export interface Review {
  id: number
  rating: number
  comment: string | null
  created_at: string
  reply: string | null
  replied_at: string | null
  author: { display_name: string; city: ProviderCity | null }
  trade: Trade | null
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  per_page: number
}

/** Trades and cities carry their own three names — an admin adds them at
 *  runtime, so they cannot be translation keys. */
export function localisedName(
  item: { name_ar: string; name_fr: string; name_en: string },
  language: string,
): string {
  if (language === 'ar') return item.name_ar
  if (language === 'fr') return item.name_fr
  return item.name_en
}
