import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

/**
 * Guards a trap that costs an afternoon to find.
 *
 * esbuild's tsconfig discovery walks up from each source file and takes the
 * first tsconfig.json it can parse. Its parser rejects `//` comments silently:
 * add one here, and esbuild skips this file and keeps climbing — out of this
 * folder and into the unrelated Expo project at the repository root, whose
 * `paths` maps `@/*` at *its own* src.
 *
 * TypeScript itself allows comments in tsconfig, which is exactly why the
 * failure is invisible. So: this file stays strict JSON.
 */
describe('tsconfig.json', () => {
  it('is strict JSON, with no comments', () => {
    // cwd, not import.meta.url: the jsdom environment reports an http URL.
    const raw = readFileSync(resolve(process.cwd(), 'tsconfig.json'), 'utf8')

    expect(() => JSON.parse(raw) as unknown).not.toThrow()
    expect(raw, 'a // comment here makes esbuild silently use another project’s tsconfig').not.toMatch(
      /^\s*\/\//m,
    )
  })
})
