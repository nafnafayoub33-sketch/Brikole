import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'

import type { Language } from '@/lib/i18n'
import { Chat } from '@/ui/Chat'
import { NotFoundPage } from '@/features/public/NotFoundPage'

/**
 * C9 — the client's side of the chat.
 *
 * Thin on purpose: the thread and the handshake are the same for both people,
 * so they live in `ui/Chat`. What differs is where "back" goes and which job
 * screen the sealed deal opens.
 */
export function ChatPage() {
  const { i18n } = useTranslation()
  const { conversationId, id } = useParams()

  const conversation = Number(conversationId)
  if (!Number.isFinite(conversation)) return <NotFoundPage />

  return (
    <Chat
      conversationId={conversation}
      language={i18n.language as Language}
      backTo={id ? `/client/requests/${id}` : '/client/requests'}
      jobTo={(jobId) => `/client/jobs/${jobId}`}
    />
  )
}
