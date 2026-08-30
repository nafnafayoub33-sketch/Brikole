import { useId, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { useUpload, type UploadPurpose } from '@/data/pro'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import { cn } from '@/ui/cn'

export interface PickedPhoto {
  /** What the API stores. A private file has no URL, so this is the identity. */
  path: string
  /** A local object URL, so the preview works before anything is public. */
  preview: string
}

/**
 * Pick a photo, upload it, see it.
 *
 * The preview comes from the file the browser already has rather than from the
 * server: an identity document has no public URL by design, and waiting for a
 * round trip to show somebody their own photo is a delay with no purpose.
 */
export function PhotoInput({
  label,
  hint,
  note,
  purpose,
  value,
  onChange,
  round = false,
}: {
  label: string
  hint?: string
  note?: string
  purpose: UploadPurpose
  value: PickedPhoto | null
  onChange: (photo: PickedPhoto | null) => void
  round?: boolean
}) {
  const { t } = useTranslation()
  const id = useId()
  const input = useRef<HTMLInputElement>(null)
  const upload = useUpload()
  const message = useErrorMessage()
  const [error, setError] = useState<string | null>(null)

  async function pick(file: File | undefined) {
    if (!file) return
    setError(null)
    const preview = URL.createObjectURL(file)
    try {
      const result = await upload.mutateAsync({ file, purpose })
      onChange({ path: result.path, preview })
    } catch (uploadError) {
      URL.revokeObjectURL(preview)
      setError(message(uploadError))
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-semibold text-fg">{label}</span>

      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={() => input.current?.click()}
          aria-describedby={hint ? `${id}-hint` : undefined}
          className={cn(
            'flex size-24 shrink-0 items-center justify-center overflow-hidden border-2 border-dashed',
            'border-border-strong bg-surface-2 text-fg-subtle',
            'transition-colors duration-(--duration-fast) hover:border-primary hover:text-primary',
            round ? 'rounded-full' : 'rounded-md',
          )}
        >
          {value ? (
            <img src={value.preview} alt="" className="size-full object-cover" />
          ) : upload.isPending ? (
            <span className="size-5 animate-spin rounded-full border-2 border-current border-t-transparent" />
          ) : (
            <PlusGlyph />
          )}
        </button>

        <div className="flex flex-col items-start gap-1.5">
          <button
            type="button"
            onClick={() => input.current?.click()}
            disabled={upload.isPending}
            className="text-sm font-semibold text-primary underline-offset-4 hover:underline disabled:opacity-50"
          >
            {upload.isPending ? t('onboarding.uploading') : t('onboarding.addPhoto')}
          </button>
          {value && (
            <button
              type="button"
              onClick={() => {
                URL.revokeObjectURL(value.preview)
                onChange(null)
              }}
              className="text-xs font-medium text-danger underline-offset-4 hover:underline"
            >
              {t('onboarding.removePhoto')}
            </button>
          )}
        </div>
      </div>

      <input
        ref={input}
        id={id}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        onChange={(event) => {
          void pick(event.target.files?.[0])
          event.target.value = ''
        }}
      />

      {hint && (
        <p id={`${id}-hint`} className="text-xs text-fg-subtle">
          {hint}
        </p>
      )}
      {note && (
        <p className="flex items-start gap-2 rounded-md bg-primary-soft px-3 py-2 text-xs text-fg-muted">
          <LockGlyph />
          <span>{note}</span>
        </p>
      )}
      {error && (
        <p role="alert" className="text-xs font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  )
}

/** The same picker, several times over, for a portfolio. */
export function PhotoGallery({
  label,
  hint,
  value,
  onChange,
  max,
  purpose = 'portfolio',
}: {
  label: string
  hint?: string
  value: PickedPhoto[]
  onChange: (photos: PickedPhoto[]) => void
  max: number
  purpose?: UploadPurpose
}) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col gap-3">
      <span className="text-sm font-semibold text-fg">{label}</span>

      <ul className="flex flex-wrap gap-3">
        {value.map((photo) => (
          <li key={photo.path} className="relative">
            <img
              src={photo.preview}
              alt=""
              className="size-24 rounded-md border border-border object-cover"
            />
            <button
              type="button"
              onClick={() => {
                URL.revokeObjectURL(photo.preview)
                onChange(value.filter((item) => item.path !== photo.path))
              }}
              aria-label={t('onboarding.removePhoto')}
              className="absolute -end-2 -top-2 flex size-6 items-center justify-center rounded-full bg-danger text-xs font-bold text-white shadow-sm"
            >
              ×
            </button>
          </li>
        ))}

        {value.length < max && (
          <li className="w-full max-w-56">
            <PhotoInput
              label=""
              purpose={purpose}
              value={null}
              onChange={(photo) => photo && onChange([...value, photo])}
            />
          </li>
        )}
      </ul>

      {hint && <p className="text-xs text-fg-subtle">{hint}</p>}
    </div>
  )
}

function PlusGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="size-7"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      aria-hidden
    >
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

function LockGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="mt-0.5 size-4 shrink-0 text-primary"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <rect x="4.5" y="10.5" width="15" height="10" rx="2.5" />
      <path d="M8 10.5V7.8a4 4 0 0 1 8 0v2.7" />
    </svg>
  )
}
