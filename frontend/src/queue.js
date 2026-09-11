// Order of the review queue, shared by the queue page and by "open the next document" after a
// review, so both follow the order the verifier chose.
export const QUEUE_ORDER_KEY = 'landlekha.queueOrder'

export function getQueueOrder() {
  try { return localStorage.getItem(QUEUE_ORDER_KEY) || 'confidence' } catch { return 'confidence' }
}

// "confidence": as the server sends it (lowest confidence first). "quick": fewest fields to
// check first, higher confidence breaking ties. Never changes the array it is given.
export function sortQueue(rows, order) {
  if (!rows || order !== 'quick') return rows
  return [...rows].sort((a, b) => (a.flagged ?? Infinity) - (b.flagged ?? Infinity)
    || (b.overall_confidence ?? 0) - (a.overall_confidence ?? 0))
}
