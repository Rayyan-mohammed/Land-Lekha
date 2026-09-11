// Thin fetch wrapper around the FastAPI backend (see docs/contracts.md and /docs).
const TOKEN_KEY = 'landlekha.token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY))

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : detail?.message || `HTTP ${status}`)
    this.status = status
    this.detail = detail
  }
}

async function request(path, { method = 'GET', body, form, raw } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let payload
  if (form) payload = form
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }
  const res = await fetch(path, { method, headers, body: payload })
  if (res.status === 401 && token) {
    setToken(null)
    // tell the sign-in page why the user is back there (a deliberate sign-out never gets here)
    try { sessionStorage.setItem('landlekha.expired', '1') } catch { /* storage blocked */ }
    window.dispatchEvent(new Event('landlekha:logout'))
  }
  if (!res.ok) {
    let detail
    try { detail = (await res.json()).detail } catch { detail = res.statusText }
    throw new ApiError(res.status, detail)
  }
  if (raw) return res
  return res.status === 204 ? null : res.json()
}

export const api = {
  login: (username, password) => {
    const form = new URLSearchParams({ username, password })
    return fetch('/api/auth/login', { method: 'POST', body: form }).then(async (r) => {
      if (!r.ok) throw new ApiError(r.status, (await r.json().catch(() => ({}))).detail || 'login failed')
      return r.json()
    })
  },
  me: () => request('/api/auth/me'),

  upload: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/api/documents', { method: 'POST', form })
  },
  documents: (params = {}) => request('/api/documents?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null))),
  document: (id) => request(`/api/documents/${id}`),
  pageBlob: (id, n) => request(`/api/documents/${id}/pages/${n}`, { raw: true }).then((r) => r.blob()),
  reprocess: (id) => request(`/api/documents/${id}/reprocess`, { method: 'POST' }),

  queue: () => request('/api/review/queue'),
  verify: (id, body) => request(`/api/documents/${id}/verify`, { method: 'POST', body }),

  stats: () => request('/api/admin/stats'),
  audit: (params = {}) => request('/api/admin/audit?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null))),
  users: () => request('/api/admin/users'),
  createUser: (body) => request('/api/admin/users', { method: 'POST', body }),
  updateUser: (id, body) => request(`/api/admin/users/${id}`, { method: 'PATCH', body }),

  lrmsRecords: (params = {}) => request('/api/integration/lrms/records?' + new URLSearchParams(params)),
  lrmsPush: (id) => request(`/api/integration/lrms/push/${id}`, { method: 'POST' }),
  dilrmp: () => request('/api/integration/dilrmp/progress'),
  parcels: () => request('/api/integration/gis/parcels'),
  extract: (id) => request(`/api/records/${id}/extract`),
  publicVerify: (id, fp) => fetch(`/api/public/records/${id}/verify?fp=${encodeURIComponent(fp)}`).then((r) => {
    if (!r.ok) throw new ApiError(r.status, 'verification service error')
    return r.json()
  }),
}
