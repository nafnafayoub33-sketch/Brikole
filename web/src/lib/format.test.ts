import { describe, expect, it } from 'vitest'

import {
  formatBudget,
  formatCount,
  formatDH,
  formatDirhams,
  formatMonth,
  formatMonthLong,
  formatPhone,
} from '@/lib/format'

describe('formatDH', () => {
  it('renders centimes as dirhams with two decimals', () => {
    expect(formatDH(3000)).toContain('30')
    expect(formatDH(3000)).toMatch(/DH$/)
    expect(formatDH(0)).toContain('0')
  })

  it('keeps Latin digits in Arabic, because a price is read as a number', () => {
    // ar-MA would otherwise render ٣٠٫٠٠ — the point of -u-nu-latn.
    expect(formatDH(3000, 'ar')).toMatch(/[0-9]/)
    expect(formatDH(3000, 'ar')).not.toMatch(/[٠-٩]/)
  })

  it('does not lose centimes to floating point', () => {
    expect(formatDH(12_345)).toMatch(/123[.,]45/)
  })
})

describe('formatDirhams', () => {
  it('drops the decimals when there is nothing worth showing', () => {
    expect(formatDirhams(15_000)).toMatch(/^150\s?DH$/)
  })
})

describe('formatBudget', () => {
  it('renders a range', () => {
    expect(formatBudget(10_000, 30_000)).toMatch(/100.*–.*300/)
  })

  it('renders a single side when only one is given', () => {
    expect(formatBudget(10_000, null)).toMatch(/100/)
    expect(formatBudget(null, 30_000)).toMatch(/300/)
  })

  it('is null when no budget was given at all', () => {
    expect(formatBudget(null, null)).toBeNull()
  })
})

describe('formatPhone', () => {
  it('renders E.164 as the national form people recognise', () => {
    expect(formatPhone('+212612345678')).toBe('06 12 34 56 78')
  })

  it('leaves anything that is not a Moroccan E.164 number alone', () => {
    expect(formatPhone('0612345678')).toBe('0612345678')
  })
})

describe('formatCount', () => {
  it('groups a count the same way a price is grouped', () => {
    // Two separators on one screen — `1,073` beside `10.700 DH` — reads as two
    // different numbering systems.
    for (const language of ['ar', 'fr', 'en'] as const) {
      const grouping = formatCount(1073, language).replace(/\d/g, '')
      const price = formatDirhams(107_300, language).replace(/[\d\s]|DH/g, '')
      expect(grouping).toBe(price)
    }
  })

  it('keeps Latin digits in Arabic', () => {
    expect(formatCount(1073, 'ar')).toMatch(/1.073/)
  })
})

describe('formatMonth', () => {
  it('names the month the key actually says', () => {
    expect(formatMonth('2026-01', 'en')).toMatch(/Jan/)
    expect(formatMonth('2026-12', 'en')).toMatch(/Dec/)
  })

  it('does not roll back a month in a negative timezone', () => {
    // `new Date('2026-08')` is UTC midnight; read locally, west of Greenwich
    // that is July, and the column would carry the wrong label.
    expect(formatMonthLong('2026-08', 'en')).toMatch(/August 2026/)
  })
})
