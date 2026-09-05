/**
 * Session, sign-in, registration.
 *
 * `useSession` is the single source of truth for "who is signed in": the
 * router, the layouts and the role gate all read it, and none of them keeps a
 * copy.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError, api, restoreSession } from '@/data/client'
import { platformStore } from '@/data/platform'
import { sessionStore } from '@/data/session'
import type { LoginResponse, Me, Role } from '@/data/types'

export const SESSION_KEY = ['session'] as const

async function fetchSession(): Promise<Me | null> {
  // No access token in memory yet — a reload, or a first visit. If the refresh
  // cookie survived, this turns it back into a session; if not, we are simply
  // signed out, which is not an error.
  if (!sessionStore.get() && !(await restoreSession())) return null

  try {
    return await api<Me>('/auth/me')
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      sessionStore.clear()
      return null
    }
    throw error
  }
}

export function useSession() {
  return useQuery({
    queryKey: SESSION_KEY,
    queryFn: fetchSession,
    staleTime: 5 * 60_000,
    retry: false,
  })
}

interface Credentials {
  phone: string
  password: string
}

interface Registration extends Credentials {
  full_name: string
  role: Extract<Role, 'client' | 'provider'>
  language?: string
}

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (credentials: Credentials) =>
      api<LoginResponse>('/auth/login', {
        method: 'POST',
        body: credentials,
        authenticated: false,
      }),
    onSuccess: (response) => {
      sessionStore.set(response.token.access_token)
      queryClient.setQueryData(SESSION_KEY, response.user)
    },
  })
}

export function useRegister() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (registration: Registration) =>
      api<LoginResponse>('/auth/register', {
        method: 'POST',
        body: registration,
        authenticated: false,
      }),
    onSuccess: (response) => {
      sessionStore.set(response.token.access_token)
      queryClient.setQueryData(SESSION_KEY, response.user)
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api<void>('/auth/logout', { method: 'POST' }),
    // Even a failed call must sign the user out locally: they asked to leave.
    onSettled: () => {
      sessionStore.clear()
      // A suspension screen belongs to the session that hit it. Leaving ends
      // both, or S3 stays up over the landing page of a signed-out browser.
      platformStore.clear()
      queryClient.setQueryData(SESSION_KEY, null)
      void queryClient.invalidateQueries()
    },
  })
}
