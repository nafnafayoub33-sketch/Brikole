import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'

import type { Language } from '@/lib/i18n'
import { Chat } from '@/ui/Chat'
import { NotFoundPage } from '@/features/public/NotFoundPage'

/** M12 — the tradesman's side of the same thread. */
export function ChatPage() {
  const { i18n } = useTranslation()
  const { conversationId } = useParams()

  const conversation = Number(conversationId)
  if (!Number.isFinite(conversation)) return <NotFoundPage />

  return (
    <Chat
      conversationId={conversation}
      language={i18n.language as Language}
      backTo="/pro/offers"
      jobTo={(jobId) => `/pro/jobs?job=${jobId}`}
    />
  )
}
