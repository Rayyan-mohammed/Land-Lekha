// The retake advice a page can come back with is written in backend/ocr/quality.py. If a new one
// is added there and nobody translates it, an operator on the Hindi app is told what to do in
// English. This test fails first.
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { explainAdvice } from './reasons'

const QUALITY = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'backend', 'ocr', 'quality.py')

// advice.append("text is small - ...") and f-string variants, with the f-string holes filled in
function adviceStrings() {
  const code = readFileSync(QUALITY, 'utf8')
  return [...code.matchAll(/advice\.append\(f?"([^"]+)"/g)].map((m) => m[1].replace(/\{[^}]*\}/g, '900'))
}

describe('retake advice', () => {
  it('finds the advice in backend/ocr/quality.py', () => {
    expect(adviceStrings().length).toBeGreaterThan(3)
  })

  it('is shown in Hindi, every line of it', () => {
    const missing = adviceStrings().filter((a) => explainAdvice(a, 'hi') === a)
    expect(missing).toEqual([])
  })

  it('leaves English alone', () => {
    const [first] = adviceStrings()
    expect(explainAdvice(first, 'en')).toBe(first)
  })
})
