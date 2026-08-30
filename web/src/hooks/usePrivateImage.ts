import { useEffect, useState } from 'react'

import { apiBlob } from '@/data/client'

/**
 * Show a file from the private bucket.
 *
 * The identity document is readable only with the admin's token, and an image
 * element cannot carry one — so the bytes are fetched and handed to the
 * browser as an object URL, which is revoked when the component goes away or
 * the path changes. Without the revoke, reviewing a queue leaks a blob per
 * application looked at.
 */
export function usePrivateImage(path: string | null) {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!path) {
      setUrl(null)
      return
    }

    let objectUrl: string | null = null
    let cancelled = false

    setLoading(true)
    setError(null)

    apiBlob(`/uploads/${path}`)
      .then((blob) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(cause)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
      setUrl(null)
    }
  }, [path])

  return { url, error, loading }
}
