import { QueryClient } from '@tanstack/react-query'

import { ApiError } from '@/data/client'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        // Retrying a 403 or a 404 just makes the user wait longer for the same
        // answer. Only the network is worth a second attempt.
        if (error instanceof ApiError && !error.isNetwork) return false
        return failureCount < 2
      },
      refetchOnWindowFocus: false,
    },
    mutations: { retry: false },
  },
})
