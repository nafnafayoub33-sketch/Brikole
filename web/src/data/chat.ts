/**
 * C9 and M12 — the chat, and the handshake that ends it.
 *
 * One module for both sides. The client and the tradesman read the same
 * payload and render different cards from it; giving each a data module of its
 * own would be two copies of the same six calls.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/data/client'
import { CREDIT_KEY } from '@/data/offers'
import { JOBS_KEY } from '@/data/jobs'
import { REQUESTS_KEY } from '@/data/requests'

export type MessageKind = 'text' | 'image' | 'file' | 'system'

export interface ChatParty {
  id: number
  full_name: string
  avatar_url: string | null
  rating_avg?: number | null
  rating_count?: number | null
  jobs_done?: number | null
}

export interface ChatMessage {
  id: number
  kind: MessageKind
  /** Already redacted by the API. For a system line, a key and its arguments. */
  body: string
  /** How many contacts were struck out. The bubble says so when it is not 0. */
  redacted_count: number
  sender_id: number | null
  /** A storage path in the private bucket, fetched with the token — never a
   *  URL an `<img src>` could load on its own. */
  attachment_path: string | null
  attachment_name: string | null
  attachment_bytes: number | null
  created_at: string
}

export interface Conversation {
  id: number
  offer_id: number
  request_id: number
  request_title: string
  offer_status: 'pending' | 'accepted' | 'rejected' | 'withdrawn' | 'expired'
  other: ChatParty
  viewer_is_client: boolean
  /** The reader's own user id — the only thing a message's `sender_id`
   *  should ever be compared with. `other.id` is a profile id on one side
   *  of the thread and a user id on the other. */
  viewer_id: number

  price_centimes: number
  terms: string
  /** What a signature is against. A stale one is refused, never upgraded. */
  version: number
  client_agreed: boolean
  provider_agreed: boolean
  sealed_at: string | null
  job_id: number | null
  /** Set once the tradesman paid the lead fee to hand over a contact. From
   *  then on nothing is struck out of either side's messages. */
  lead_charged_at: string | null
  /** What that costs him — stated before he can be charged for it. */
  contact_fee_centimes: number

  last_message_at: string | null
}

export interface Thread {
  conversation: Conversation
  messages: ChatMessage[]
}

export const CHAT_KEY = ['chat'] as const

/** While they are still talking, the thread is polled. A real socket is worth
 *  it later; it is not worth it before the first hundred conversations. */
const POLL_MS = 5_000

export function useThread(conversationId: number | null) {
  return useQuery({
    queryKey: [...CHAT_KEY, conversationId],
    queryFn: () => api<Thread>(`/conversations/${conversationId}`),
    enabled: conversationId !== null,
    refetchInterval: (query) =>
      query.state.data?.conversation.sealed_at ? false : POLL_MS,
  })
}

/** The badge in the nav. Without it the tradesman has no way to learn that a
 *  client opened a chat on his offer: he sent it and went back to work. */
export function useUnreadChats(enabled: boolean) {
  return useQuery({
    queryKey: [...CHAT_KEY, 'unread'],
    queryFn: () => api<{ count: number }>('/conversations/unread'),
    enabled,
    refetchInterval: POLL_MS * 6,
  })
}

/** Tapping an offer on C3. Commits to nothing — it only opens the thread. */
export function useOpenConversation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (offerId: number) =>
      api<Conversation>(`/offers/${offerId}/conversation`, { method: 'POST' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: CHAT_KEY })
    },
  })
}

/** Tell the API he has seen it, so the nav badge lets go.
 *
 *  Fired from the screen rather than by the GET: reading a thread is a
 *  deliberate act, and a `GET` that writes is a `GET` that surprises somebody
 *  the day it is called from a prefetch. */
export function useMarkRead(conversationId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      api<Conversation>(`/conversations/${conversationId}/read`, { method: 'POST' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...CHAT_KEY, 'unread'] })
    },
  })
}

export function useSendMessage(conversationId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      body: string
      /** The tradesman agreeing to the lead fee for a message carrying his
       *  number. Without it the API refuses with the price rather than
       *  charging him for something he did not know would cost. */
      accept_charge?: boolean
      attachment_path?: string | null
      attachment_name?: string | null
      attachment_bytes?: number | null
    }) => api<ChatMessage>(`/conversations/${conversationId}/messages`, { method: 'POST', body }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...CHAT_KEY, conversationId] })
      void queryClient.invalidateQueries({ queryKey: [...CHAT_KEY, 'unread'] })
      // Revealing a contact takes the lead fee, so his balance moved.
      void queryClient.invalidateQueries({ queryKey: CREDIT_KEY })
    },
  })
}

/** Every move on the deal can be the one that creates the job, so all three
 *  invalidate the job and request lists rather than only `agree`. */
function useDealAction<TVariables>(
  conversationId: number,
  send: (variables: TVariables) => Promise<Conversation>,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: send,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...CHAT_KEY, conversationId] })
      void queryClient.invalidateQueries({ queryKey: JOBS_KEY })
      void queryClient.invalidateQueries({ queryKey: REQUESTS_KEY })
      void queryClient.invalidateQueries({ queryKey: CREDIT_KEY })
    },
  })
}

export function usePropose(conversationId: number) {
  return useDealAction(conversationId, (body: { price_centimes: number; terms: string }) =>
    api<Conversation>(`/conversations/${conversationId}/propose`, { method: 'POST', body }),
  )
}

export function useAgree(conversationId: number) {
  return useDealAction(conversationId, (version: number) =>
    api<Conversation>(`/conversations/${conversationId}/agree`, {
      method: 'POST',
      body: { version },
    }),
  )
}

export function useWithdrawAgreement(conversationId: number) {
  return useDealAction(conversationId, (_: void) =>
    api<Conversation>(`/conversations/${conversationId}/withdraw`, { method: 'POST' }),
  )
}
