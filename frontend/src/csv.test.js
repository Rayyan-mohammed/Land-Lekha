import { describe, expect, it } from 'vitest'
import { toCsv } from './csv'

const CRLF = String.fromCharCode(13, 10)

describe('toCsv', () => {
  it('starts with a byte-order mark so Excel reads Hindi correctly', () => {
    expect(toCsv(['नाम'], [['राम प्रसाद']]).charCodeAt(0)).toBe(0xFEFF)
  })

  it('separates rows with CRLF', () => {
    expect(toCsv(['a'], [['b'], ['c']]).slice(1)).toBe(`"a"${CRLF}"b"${CRLF}"c"`)
  })

  it('keeps a comma inside a value in one cell', () => {
    expect(toCsv(['owners'], [['Ram; Shyam, son of Mohan']]).slice(1).split(CRLF)[1])
      .toBe('"Ram; Shyam, son of Mohan"')
  })

  it('doubles quotes and survives a line break inside a value', () => {
    expect(toCsv(['a'], [['he said "yes"']]).slice(1).split(CRLF)[1]).toBe('"he said ""yes"""')
  })

  it('writes nothing for a missing value rather than "null"', () => {
    expect(toCsv(['a', 'b'], [[null, undefined]]).slice(1).split(CRLF)[1]).toBe('"",""')
  })

  it('keeps 0 and false, which are not missing', () => {
    expect(toCsv(['a', 'b'], [[0, false]]).slice(1).split(CRLF)[1]).toBe('"0","false"')
  })
})
