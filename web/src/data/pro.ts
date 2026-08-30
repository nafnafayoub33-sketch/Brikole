/** The tradesman's own profile: reading it, filling it in, uploading its photos. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError, api } from '@/data/client'
import { SESSION_KEY } from '@/data/auth'
import type { ProviderProfile } from '@/data/types'

export interface MyProviderProfile extends ProviderProfile {
  rejection_reason: string | null
  id_card_path: string | null
}

export const MY_PROFILE_KEY = ['pro', 'profile'] as const

/**
 * His application, at whatever status.
 *
 * `null` means he has not filled one in — the absence of a profile is the
 * signal that routes him to M1, rather than a flag somewhere on the account.
 */
export function useMyProfile(enabled = true) {
  return useQuery({
    queryKey: MY_PROFILE_KEY,
    queryFn: async (): Promise<MyProviderProfile | null> => {
      try {
        return await api<MyProviderProfile>('/pro/profile')
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
    enabled,
    staleTime: 30_000,
    retry: false,
  })
}

export type UploadPurpose = 'avatar' | 'id_card' | 'portfolio'

export interface UploadResult {
  path: string
  url: string | null
}

export function useUpload() {
  return useMutation({
    mutationFn: ({ file, purpose }: { file: File; purpose: UploadPurpose }) => {
      const form = new FormData()
      form.append('purpose', purpose)
      form.append('file', file)
      return api<UploadResult>('/uploads', { method: 'POST', body: form })
    },
  })
}

export interface ApplicationBody {
  trade_ids: number[]
  city_id: number
  radius_km: number
  headline: string
  bio: string
  years_experience: number
  starting_price_centimes: number | null
  avatar_path: string | null
  id_card_path: string | null
  photo_paths: string[]
}

export function useSubmitApplication() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ApplicationBody) =>
      api<MyProviderProfile>('/pro/profile', { method: 'POST', body }),
    onSuccess: (profile) => {
      queryClient.setQueryData(MY_PROFILE_KEY, profile)
      // `/auth/me` carries the provider summary the router gates on, and the
      // avatar the header shows.
      void queryClient.invalidateQueries({ queryKey: SESSION_KEY })
    },
  })
}
