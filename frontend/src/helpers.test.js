// Unit tests for the helpers that turn backend output into plain English and Hindi.
// Run with `npm test`.
import { describe, expect, it } from 'vitest'
import { docTypeLabel } from './constants'
import { areaInLang, explainAdvice, explainIssue, explainReason } from './reasons'
import { parseTs } from './components/ui'
import { sortQueue } from './queue'
import { numbersReread } from './pages/DocumentView'

describe('sortQueue', () => {
  const rows = [
    { id: 1, flagged: 5, overall_confidence: 0.2 },
    { id: 2, flagged: 1, overall_confidence: 0.5 },
    { id: 3, flagged: 1, overall_confidence: 0.7 },
    { id: 4, overall_confidence: 0.1 },
  ]
  it('keeps the server order (lowest confidence first) by default', () => {
    expect(sortQueue(rows, 'confidence')).toBe(rows)
  })
  it('puts the quickest documents first, higher confidence breaking ties', () => {
    expect(sortQueue(rows, 'quick').map((r) => r.id)).toEqual([3, 2, 1, 4])
    expect(rows.map((r) => r.id)).toEqual([1, 2, 3, 4]) // the original list is untouched
  })
  it('handles an empty or missing list', () => {
    expect(sortQueue(null, 'quick')).toBe(null)
    expect(sortQueue([], 'quick')).toEqual([])
  })
})

describe('explainReason', () => {
  it('turns a low-confidence reason into a sentence with the field name', () => {
    expect(explainReason('low confidence: owner_name (0.55)')).toBe('Landowner Name: not sure of the reading (55%)')
    expect(explainReason('low confidence: owner_name (0.55)', 'hi')).toBe('खातेदार का नाम: पढ़ाई पर भरोसा कम (55%)')
  })
  it('explains missing fields, failed checks and duplicates', () => {
    expect(explainReason('missing required field: khata_number', 'hi')).toBe('खाता संख्या: पन्ने पर नहीं मिला')
    expect(explainReason('consistency failed: village_in_tehsil (Harrakheda / Berasia)'))
      .toBe('village does not belong to this tehsil (Harrakheda / Berasia)')
    expect(explainReason('possible duplicate of record 3 (same khata)', 'hi')).toBe('अभिलेख #3 जैसा लगता है (same khata)')
  })
  it('shows unknown reasons as they are', () => {
    expect(explainReason('something new', 'hi')).toBe('something new')
  })
})

describe('explainAdvice', () => {
  it('translates photo advice into Hindi and leaves English alone', () => {
    const blurred = 'image is blurred - hold the camera steady, tap to focus and retake'
    expect(explainAdvice(blurred)).toBe(blurred)
    expect(explainAdvice(blurred, 'hi')).toMatch(/^चित्र धुंधला है/)
  })
  it('keeps the numbers in the resolution advice', () => {
    expect(explainAdvice('low resolution (800px) - use at least 1000px / 150 dpi', 'hi'))
      .toBe('कम रिज़ॉल्यूशन (800px) — कम से कम 1000px / 150 dpi रखें')
  })
})

describe('explainIssue', () => {
  it('names the field for invalid values', () => {
    expect(explainIssue('invalid plot_area', 'hi')).toBe('क्षेत्रफल: नियम पर खरा नहीं')
  })
  it('translates known field issues and review-reason kinds', () => {
    expect(explainIssue('mixed scripts in name', 'hi')).toBe('नाम में हिंदी और अंग्रेज़ी मिले हैं')
    expect(explainIssue('low confidence', 'hi')).toBe('पढ़ाई पर भरोसा कम')
    expect(explainIssue('unit not readable, assumed bigha (state practice)', 'hi')).toMatch(/^इकाई नहीं पढ़ी गई/)
  })
  it('passes English and unknown issues through', () => {
    expect(explainIssue('mixed scripts in name')).toBe('mixed scripts in name')
    expect(explainIssue('brand new issue', 'hi')).toBe('brand new issue')
  })
})

describe('docTypeLabel', () => {
  it('names each document type in both languages', () => {
    expect(docTypeLabel('khatiyan', 'en')).toBe('Khatiyan')
    expect(docTypeLabel('record_of_rights', 'hi')).toBe('अधिकार अभिलेख')
  })
  it('handles missing and unmapped types', () => {
    expect(docTypeLabel(null, 'en')).toBe('unknown type')
    expect(docTypeLabel(undefined, 'hi')).toBe('अज्ञात प्रकार')
    expect(docTypeLabel('new_form_type', 'en')).toBe('new form type')
  })
})

describe('areaInLang', () => {
  it('shows the unit in Hindi and keeps the number unchanged', () => {
    expect(areaInLang('8.41 bigha', 'hi')).toBe('8.41 बीघा')
    expect(areaInLang('4.481 hectare', 'hi')).toBe('4.481 हेक्टेयर')
    expect(areaInLang('0.44 acre', 'hi')).toBe('0.44 एकड़')
  })
  it('leaves English and empty values alone', () => {
    expect(areaInLang('8.41 bigha', 'en')).toBe('8.41 bigha')
    expect(areaInLang(null, 'hi')).toBe(null)
  })
})

describe('parseTs', () => {
  it('reads backend timestamps without a zone as UTC', () => {
    expect(parseTs('2026-09-11T10:00:00').getTime()).toBe(Date.UTC(2026, 8, 11, 10, 0, 0))
    expect(parseTs('2026-09-11T10:00:00Z').getTime()).toBe(Date.UTC(2026, 8, 11, 10, 0, 0))
    expect(parseTs('2026-09-11T15:30:00+05:30').getTime()).toBe(Date.UTC(2026, 8, 11, 10, 0, 0))
  })
})

describe('numbersReread', () => {
  const page = (...steps) => ({ preprocess: { steps } })

  it('reads the count out of the step the pipeline wrote', () => {
    expect(numbersReread(page('grayscale', 'denoise', 'numbers:3'))).toBe(3)
  })

  it('is zero when no number was read again', () => {
    expect(numbersReread(page('grayscale', 'second read'))).toBe(0)
  })

  it('does not fall over on a page that has no preprocessing at all', () => {
    expect(numbersReread({})).toBe(0)
    expect(numbersReread({ preprocess: {} })).toBe(0)
  })

  it('is not confused by the table-cell step, which looks the same', () => {
    expect(numbersReread(page('table_cells:4'))).toBe(0)
  })
})
