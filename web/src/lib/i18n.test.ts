import { describe, expect, it } from 'vitest'

import { DEFAULT_LANGUAGE, LANGUAGES, isRtl, resources } from '@/lib/i18n'

type Tree = { [key: string]: string | Tree }

function paths(tree: Tree, prefix = ''): string[] {
  return Object.entries(tree).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key
    return typeof value === 'string' ? [path] : paths(value, path)
  })
}

describe('translations', () => {
  const byLanguage = Object.fromEntries(
    LANGUAGES.map((language) => [
      language,
      new Set(paths(resources[language].translation as unknown as Tree)),
    ]),
  )

  it.each(LANGUAGES.filter((language) => language !== DEFAULT_LANGUAGE))(
    '%s has exactly the same keys as the default language',
    (language) => {
      const reference = byLanguage[DEFAULT_LANGUAGE]!
      const candidate = byLanguage[language]!

      const missing = [...reference].filter((key) => !candidate.has(key))
      const extra = [...candidate].filter((key) => !reference.has(key))

      expect({ missing, extra }).toEqual({ missing: [], extra: [] })
    },
  )

  it('has no empty string anywhere', () => {
    for (const language of LANGUAGES) {
      const tree = resources[language].translation as unknown as Tree
      for (const path of paths(tree)) {
        const value = path.split('.').reduce<string | Tree>((node, key) => {
          return (node as Tree)[key]!
        }, tree)
        expect(value, `${language}.${path}`).not.toBe('')
      }
    }
  })

  it('interpolates rather than concatenating, where a value appears', () => {
    // Word order differs between the three, so a sentence assembled with `+`
    // is wrong in at least one of them. Placeholders must survive translation.
    for (const language of LANGUAGES) {
      const tree = resources[language].translation as unknown as Tree
      const locked = (tree.errors as Tree).account_locked as string
      expect(locked, language).toContain('{{minutes}}')
    }
  })
})

describe('direction', () => {
  it('is right to left for Arabic only', () => {
    expect(isRtl('ar')).toBe(true)
    expect(isRtl('fr')).toBe(false)
    expect(isRtl('en')).toBe(false)
  })

  it('defaults to Arabic', () => {
    expect(DEFAULT_LANGUAGE).toBe('ar')
  })
})
