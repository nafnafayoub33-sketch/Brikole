import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import type { ChatMessage, Conversation } from '@/data/chat'
import {
  useAgree,
  useMarkRead,
  usePropose,
  useSendMessage,
  useThread,
  useWithdrawAgreement,
} from '@/data/chat'
import { useUpload } from '@/data/pro'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import { usePrivateImage } from '@/hooks/usePrivateImage'
import { formatDateTime, formatDirhams, isolate } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { ErrorState } from '@/ui/ErrorState'
import { Field } from '@/ui/Field'
import { Skeleton } from '@/ui/Skeleton'
import { Stars } from '@/ui/Stars'
import { cn } from '@/ui/cn'

/** What the API puts in place of a struck-out contact. */
const MARK = '[###]'

/**
 * The chat between a client and a tradesman, and the handshake inside it.
 *
 * One component for both sides. They read the same thread and may do the same
 * things — either can move the price, and it takes both signatures to make a
 * job — so the difference is which card is drawn at the top and which of the
 * two "waiting for" lines is showing. Two components would have been the same
 * screen twice, and the day they drift is the day one side can do something
 * the other cannot.
 *
 * The screen exists because of one rule: **no phone number until both have
 * signed.** Until then the API strikes contacts out of every message, and the
 * number is on the job payload and on nothing that comes before it.
 */
export function Chat({
  conversationId,
  language,
  backTo,
  jobTo,
}: {
  conversationId: number
  language: Language
  /** Where the back arrow goes — C3 for the client, M6 for the tradesman. */
  backTo: string
  /** Where the sealed deal goes: C4 or M7, the screen with the phone on it. */
  jobTo: (jobId: number) => string
}) {
  const { t } = useTranslation()
  const thread = useThread(conversationId)
  const markRead = useMarkRead(conversationId)

  // Looking at the thread is what clears the badge, and the newest message is
  // what "looked at" means — so this fires again when one arrives while the
  // screen is open, not only when it mounts.
  const newest = thread.data?.messages.at(-1)?.id ?? null
  const { mutate: markReadNow } = markRead
  useEffect(() => {
    if (newest !== null) markReadNow()
  }, [newest, markReadNow])

  if (thread.isPending) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Skeleton className="h-24" />
        <Skeleton className="h-32" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (thread.isError) {
    return (
      <div className="mx-auto max-w-3xl">
        <ErrorState error={thread.error} onRetry={() => void thread.refetch()} />
      </div>
    )
  }

  const { conversation, messages } = thread.data

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <Link
        to={backTo}
        className="text-sm font-semibold text-primary underline-offset-2 hover:underline"
      >
        <span className="inline-block rtl:rotate-180">←</span> {t('chat.back')}
      </Link>

      <Header conversation={conversation} />

      {conversation.sealed_at ? (
        <Sealed conversation={conversation} jobTo={jobTo} />
      ) : (
        <>
          <Deal conversation={conversation} language={language} />
          <Alert tone="info">{t('chat.noNumbers')}</Alert>
        </>
      )}

      <Messages
        messages={messages}
        conversation={conversation}
        language={language}
      />

      <Composer conversation={conversation} />
    </div>
  )
}

function Header({ conversation }: { conversation: Conversation }) {
  const { t } = useTranslation()
  const { other } = conversation

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-lg font-bold text-fg">{other.full_name}</h1>
          <p className="mt-1 text-sm text-fg-muted">{conversation.request_title}</p>
        </div>

        {/* No phone, no email, no way off the platform. That is the screen. */}
        {conversation.viewer_is_client && other.rating_count != null && (
          <div className="flex items-center gap-2 text-sm text-fg-muted">
            <Stars value={other.rating_avg ?? 0} />
            <span className="numeric">
              {other.rating_count > 0 ? other.rating_avg?.toFixed(1) : t('chat.noRating')}
            </span>
          </div>
        )}
      </div>
    </Card>
  )
}

/**
 * The deal on the table: a price, what it covers, and the two signatures.
 *
 * Both sides see the same card. Changing anything on it clears both
 * signatures — including the changer's own — so nobody is ever held to a
 * number they did not see.
 */
function Deal({
  conversation,
  language,
}: {
  conversation: Conversation
  language: Language
}) {
  const { t } = useTranslation()
  const message = useErrorMessage()

  const propose = usePropose(conversation.id)
  const agree = useAgree(conversation.id)
  const withdrawAgreement = useWithdrawAgreement(conversation.id)

  const [editing, setEditing] = useState(false)
  const [price, setPrice] = useState(String(conversation.price_centimes / 100))
  const [terms, setTerms] = useState(conversation.terms)

  // A new version means somebody moved the deal; the form must show what is on
  // the table now, not what this person last typed into it.
  useEffect(() => {
    setPrice(String(conversation.price_centimes / 100))
    setTerms(conversation.terms)
    setEditing(false)
  }, [conversation.version, conversation.price_centimes, conversation.terms])

  const mine = conversation.viewer_is_client
    ? conversation.client_agreed
    : conversation.provider_agreed
  const theirs = conversation.viewer_is_client
    ? conversation.provider_agreed
    : conversation.client_agreed

  const error =
    message(propose.error) ?? message(agree.error) ?? message(withdrawAgreement.error)

  return (
    <Card>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="text-base font-semibold text-fg">{t('chat.dealTitle')}</h2>
        <span className="numeric text-2xl font-bold text-fg">
          {formatDirhams(conversation.price_centimes, language)}
        </span>
      </div>

      {conversation.terms ? (
        <p className="mt-2 whitespace-pre-line text-sm text-fg-muted">{conversation.terms}</p>
      ) : (
        <p className="mt-2 text-sm text-fg-subtle">{t('chat.noTerms')}</p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <Badge tone={mine ? 'success' : 'neutral'}>
          {mine ? t('chat.youAgreed') : t('chat.youHaveNot')}
        </Badge>
        <Badge tone={theirs ? 'success' : 'neutral'}>
          {theirs ? t('chat.theyAgreed') : t('chat.theyHaveNot')}
        </Badge>
      </div>

      {error && (
        <Alert tone="danger" className="mt-4">
          {error}
        </Alert>
      )}

      {editing ? (
        <div className="mt-4 flex flex-col gap-3">
          <Field
            label={t('chat.price')}
            numeric
            inputMode="numeric"
            value={price}
            suffix="DH"
            onChange={(event) => setPrice(event.target.value)}
          />
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-fg" htmlFor="deal-terms">
              {t('chat.terms')}
            </label>
            <textarea
              id="deal-terms"
              rows={3}
              className="rounded-md border border-border-strong bg-surface p-3 text-sm text-fg"
              placeholder={t('chat.termsHint')}
              value={terms}
              onChange={(event) => setTerms(event.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              loading={propose.isPending}
              disabled={!Number(price)}
              onClick={() =>
                propose.mutate({
                  price_centimes: Math.round(Number(price) * 100),
                  terms,
                })
              }
            >
              {t('chat.send')}
            </Button>
            <Button variant="ghost" onClick={() => setEditing(false)}>
              {t('chat.cancel')}
            </Button>
          </div>
          <p className="text-xs text-fg-subtle">{t('chat.changeClears')}</p>
        </div>
      ) : (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          {mine ? (
            <Button
              variant="secondary"
              loading={withdrawAgreement.isPending}
              onClick={() => withdrawAgreement.mutate()}
            >
              {t('chat.takeBack')}
            </Button>
          ) : (
            <Button
              loading={agree.isPending}
              onClick={() => agree.mutate(conversation.version)}
            >
              {t('chat.agree')}
            </Button>
          )}

          <Button variant="ghost" onClick={() => setEditing(true)}>
            {t('chat.change')}
          </Button>
        </div>
      )}

      {mine && !theirs && (
        <p className="mt-3 text-xs text-fg-subtle">{t('chat.waitingOnThem')}</p>
      )}
    </Card>
  )
}

function Sealed({
  conversation,
  jobTo,
}: {
  conversation: Conversation
  jobTo: (jobId: number) => string
}) {
  const { t } = useTranslation()

  return (
    <Alert tone="success">
      <p className="font-semibold">{t('chat.sealed')}</p>
      <p className="mt-1">{t('chat.sealedBody')}</p>
      {conversation.job_id != null && (
        <Link
          to={jobTo(conversation.job_id)}
          className="mt-2 inline-block font-semibold underline underline-offset-2"
        >
          {t('chat.openJob')}
        </Link>
      )}
    </Alert>
  )
}

function Messages({
  messages,
  conversation,
  language,
}: {
  messages: ChatMessage[]
  conversation: Conversation
  language: Language
}) {
  const { t } = useTranslation()
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: 'nearest' })
  }, [messages.length])

  if (messages.length === 0) {
    return <p className="py-8 text-center text-sm text-fg-subtle">{t('chat.empty')}</p>
  }

  return (
    <div className="flex max-h-[55vh] flex-col gap-3 overflow-y-auto">
      {messages.map((message) =>
        message.kind === 'system' ? (
          <SystemLine
            key={message.id}
            message={message}
            conversation={conversation}
            language={language}
          />
        ) : (
          <Bubble
            key={message.id}
            message={message}
            language={language}
            mine={isMine(message, conversation)}
          />
        ),
      )}
      <div ref={bottom} />
    </div>
  )
}

/** Whose bubble it is. Against `viewer_id` and nothing else — `other.id` is a
 *  profile id on the client's side of the thread and a user id on the
 *  tradesman's, so comparing with it gets one of the two sides wrong. */
function isMine(message: ChatMessage, conversation: Conversation): boolean {
  return message.sender_id === conversation.viewer_id
}

function Bubble({
  message,
  language,
  mine,
}: {
  message: ChatMessage
  language: Language
  mine: boolean
}) {
  const { t } = useTranslation()

  return (
    <div className={cn('flex', mine ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-3.5 py-2.5',
          mine ? 'bg-primary text-primary-fg' : 'bg-surface-2 text-fg',
        )}
      >
        {message.attachment_path && <Attachment message={message} />}

        {message.body && (
          /* `dir="auto"` per bubble: a message written in French inside an
             Arabic interface must read left to right, and the reverse. The
             page's direction is the interface's, not the sender's. */
          <p dir="auto" className="whitespace-pre-line text-sm">
            {renderRedacted(message.body, mine)}
          </p>
        )}

        {message.redacted_count > 0 && (
          <p
            className={cn(
              'mt-1.5 text-xs',
              mine ? 'text-primary-fg/75' : 'text-fg-subtle',
            )}
          >
            {t('chat.wasRedacted')}
          </p>
        )}

        <p
          className={cn(
            'numeric mt-1 text-[0.6875rem]',
            mine ? 'text-primary-fg/70' : 'text-fg-subtle',
          )}
        >
          {formatDateTime(message.created_at, language)}
        </p>
      </div>
    </div>
  )
}

/** The struck-out contact renders as a chip, not as text somebody could read
 *  as the sender's own typing. */
function renderRedacted(body: string, mine: boolean) {
  return body.split(MARK).flatMap((part, index) =>
    index === 0
      ? [part]
      : [
          <span
            key={index}
            className={cn(
              'mx-0.5 rounded-sm px-1.5 py-0.5 text-xs font-semibold',
              mine ? 'bg-primary-fg/20' : 'bg-danger-soft text-danger',
            )}
          >
            •••
          </span>,
          part,
        ],
  )
}

function Attachment({ message }: { message: ChatMessage }) {
  const { t } = useTranslation()
  const isImage = message.kind === 'image'
  const { url, loading } = usePrivateImage(isImage ? message.attachment_path : null)

  if (isImage) {
    if (loading || !url) return <Skeleton className="h-40 w-56 rounded-md" />
    return (
      <img
        src={url}
        alt={message.attachment_name ?? ''}
        className="mb-1.5 max-h-64 rounded-md"
      />
    )
  }

  return (
    <p className="mb-1.5 text-sm font-semibold">
      📎 {message.attachment_name ?? t('chat.file')}
    </p>
  )
}

function SystemLine({
  message,
  conversation,
  language,
}: {
  message: ChatMessage
  conversation: Conversation
  language: Language
}) {
  const { t } = useTranslation()

  // Stored as a key and its arguments, so the two people in one thread each
  // read it in their own language — and so the line can name who did it. "One
  // of you agreed" is not a history of a negotiation.
  const [key, query] = message.body.split('?')
  const args = new URLSearchParams(query ?? '')
  const mine = Number(args.get('by')) === conversation.viewer_id
  const who = firstName(conversation.other.full_name)
  // Isolated: an amount interpolated into an Arabic sentence renders as
  // "DH 550" without it.
  const price = isolate(formatDirhams(Number(args.get('price_centimes') ?? 0), language))

  // Two keys per line rather than one with a `{{who}}` in it. French conjugates
  // the verb to its subject — "Vous **a** proposé" is what one key gets you —
  // and so does Darija. The subject and its verb have to travel together.
  const label = {
    'conversation.opened': t('chat.systemOpened'),
    'conversation.proposed': mine
      ? t('chat.systemProposedYou', { price })
      : t('chat.systemProposedThem', { who, price }),
    'conversation.agreed': mine ? t('chat.systemAgreedYou') : t('chat.systemAgreedThem', { who }),
    'conversation.withdrew': mine
      ? t('chat.systemWithdrewYou')
      : t('chat.systemWithdrewThem', { who }),
    'conversation.sealed': t('chat.systemSealed'),
  }[key ?? '']

  if (!label) return null

  return <p className="py-1 text-center text-xs text-fg-subtle">{label}</p>
}

/** Enough to say who did something without repeating the header. */
function firstName(fullName: string): string {
  return fullName.split(' ')[0] ?? fullName
}

function Composer({ conversation }: { conversation: Conversation }) {
  const { t } = useTranslation()
  const message = useErrorMessage()
  const send = useSendMessage(conversation.id)
  const upload = useUpload()

  const [body, setBody] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)

  const busy = send.isPending || upload.isPending
  const error = message(send.error) ?? message(upload.error)

  const submit = () => {
    if (!body.trim()) return
    send.mutate({ body }, { onSuccess: () => setBody('') })
  }

  const attach = (file: File) => {
    upload.mutate(
      { file, purpose: 'chat_file' },
      {
        onSuccess: (result) =>
          send.mutate({
            body: '',
            attachment_path: result.path,
            attachment_name: file.name,
            attachment_bytes: file.size,
          }),
      },
    )
  }

  return (
    <Card>
      {error && (
        <Alert tone="danger" className="mb-3">
          {error}
        </Alert>
      )}

      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        <div className="min-w-48 flex-1">
          <Field
            label={t('chat.write')}
            value={body}
            onChange={(event) => setBody(event.target.value)}
          />
        </div>

        <input
          ref={fileInput}
          type="file"
          accept="image/jpeg,image/png,image/webp,application/pdf"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) attach(file)
            event.target.value = ''
          }}
        />

        <Button
          type="button"
          variant="secondary"
          disabled={busy}
          onClick={() => fileInput.current?.click()}
        >
          {t('chat.attach')}
        </Button>

        <Button type="submit" loading={send.isPending} disabled={!body.trim()}>
          {t('chat.sendMessage')}
        </Button>
      </form>
    </Card>
  )
}
