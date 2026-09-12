// Every quoted string passed to t() / tr() on screen must have a Hindi translation, so nothing
// is left in English when the app is switched to Hindi. Run with `npm test`.
import { readdirSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { HI } from './i18n'

const SRC = dirname(fileURLToPath(import.meta.url))

function sourceFiles(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = join(dir, e.name)
    if (e.isDirectory()) return sourceFiles(p)
    return /\.(jsx?|tsx?)$/.test(e.name) && !e.name.includes('.test.') && e.name !== 'i18n.jsx' ? [p] : []
  })
}

// t('Label'), t(cond ? 'A' : 'B') and tr(...) alike: every quoted string inside the call, except
// values that are only compared (the 'quick' in t(order === 'quick' ? 'A' : 'B') is never shown)
function translatedKeys(code) {
  const keys = new Set()
  for (const call of code.matchAll(/\b(?:t|tr)\(([^()]*)\)/g)) {
    for (const s of call[1].matchAll(/(['"])((?:\\.|(?!\1).)+)\1/g)) {
      if (/[!=]==?\s*$/.test(call[1].slice(0, s.index))) continue
      keys.add(s[2].replace(/\\'/g, "'"))
    }
  }
  return keys
}

// Text that reaches the screen without passing through t() in the same file: a title/subtitle
// prop the component translates for us (<Section title="..."), and a plain tooltip.
function attributeStrings(code) {
  return new Set([...code.matchAll(/\s(?:title|subtitle|placeholder)="([^"]+)"/g)].map((m) => m[1]))
}

describe('Hindi translations', () => {
  it('cover every string the screens pass to t()', () => {
    const missing = []
    let checked = 0
    for (const file of sourceFiles(SRC)) {
      for (const key of translatedKeys(readFileSync(file, 'utf8'))) {
        checked += 1
        if (!HI[key]) missing.push(`${file.slice(SRC.length + 1)}: ${key}`)
      }
    }
    expect(checked).toBeGreaterThan(100) // the scan itself works (a broken pattern would find nothing)
    expect(missing).toEqual([])
  })

  it('cover the titles handed to a component that translates them', () => {
    const missing = []
    for (const file of sourceFiles(SRC)) {
      for (const key of attributeStrings(readFileSync(file, 'utf8'))) {
        if (!HI[key]) missing.push(`${file.slice(SRC.length + 1)}: ${key}`)
      }
    }
    expect(missing).toEqual([])
  })

  it('has no empty translations', () => {
    expect(Object.entries(HI).filter(([, v]) => !v.trim())).toEqual([])
  })
})
