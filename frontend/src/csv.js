// Spreadsheet downloads (the records list, the documents list, the audit trail).
//
// Two details matter for the offices that open these in Excel: the byte-order mark, without
// which Hindi names come out as mojibake, and CRLF line endings. Both are written as escapes
// here so that the characters cannot be lost by an editor or a copy-paste.
const BOM = String.fromCharCode(0xFEFF)
const CRLF = String.fromCharCode(13, 10)

const cell = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`

export function toCsv(head, rows) {
  return BOM + [head, ...rows].map((row) => row.map(cell).join(',')).join(CRLF)
}

/** Save `rows` as `landlekha-<what>-<today>.csv`. */
export function saveCsv(what, head, rows) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([toCsv(head, rows)], { type: 'text/csv;charset=utf-8' }))
  a.download = `landlekha-${what}-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}
