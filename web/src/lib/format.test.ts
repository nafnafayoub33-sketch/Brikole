import { describe, expect, it } from 'vitest'

import { formatBudget, formatDH, formatDirhams, formatPhone } from '@/lib/format'

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
