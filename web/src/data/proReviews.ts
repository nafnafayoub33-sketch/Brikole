/**
 * M10 — his reviews, and the one answer he gets to each.
 *
 * The summary is its own query rather than a field on every page: the numbers
 * do not change as he pages, so they are fetched once and stay put while he
 * reads. Replying invalidates both — the review changes, and so does how many
 * are still waiting on him.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/data/client'
import { PROVIDER_KEY } from '@/data/providers'
import type { Page, Review } from '@/data/types'

export const MY_REVIEWS_KEY = ['pro', 'reviews'] as const
//: A prefix of the list's key on purpose: TanStack matches by prefix, so
//: invalidating the list refreshes the count of unanswered ones with it.
export const MY_REVIEWS_SUMMARY_KEY = ['pro', 'reviews', 'summary'] as const

export const REVIEWS_PER_PAGE = 10

export interface MyReviewsSummary {
  rating_avg: number
  rating_count: number
  breakdown: Record<string, number>
  /** How many are still waiting on him. The number that makes this a queue. */
  unanswered: number
}

export function useMyReviewsSummary() {
  return useQuery({
    queryKey: MY_REVIEWS_SUMMARY_KEY,
    queryFn: () => api<MyReviewsSummary>('/pro/reviews/summary'),
    staleTime: 30_000,
  })
}

export function useMyReviews(page: number) {
  return useQuery({
    queryKey: [...MY_REVIEWS_KEY, 'page', page],
    queryFn: () =>
      api<Page<Review>>(`/pro/reviews?page=${page}&per_page=${REVIEWS_PER_PAGE}`),
    staleTime: 15_000,
  })
}

export function useReplyToReview() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reply }: { id: number; reply: string }) =>
      api<Review>(`/pro/reviews/${id}/reply`, { method: 'POST', body: { reply } }),
    onSuccess: () => {
      // One call covers the list and the summary — see the key above.
      void queryClient.invalidateQueries({ queryKey: MY_REVIEWS_KEY })
      // His public page carries the reply too, and P3 is where the client will
      // read it.
      void queryClient.invalidateQueries({ queryKey: PROVIDER_KEY })
    },
  })
}
