import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CircleMarker, GeoJSON, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import { Download, Map as MapIcon, Search, Send } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Empty, EmptyState, ErrorNote, PageHeader, SkeletonRows } from '../components/ui'
import { LAND_CLASSES } from '../constants'
import { useToast } from '../components/toast'
import { useT } from '../i18n'
import { areaInLang } from '../reasons'

function FitBounds({ data, focus }) {
  const map = useMap()
  useEffect(() => {
    if (!data?.features.length) return
    const coords = data.features
      .filter((f) => !focus || f.id === focus)
      .flatMap((f) => f.geometry.coordinates[0].map(([lon, lat]) => [lat, lon]))
    if (!coords.length) return
    const lats = coords.map((c) => c[0])
    const lons = coords.map((c) => c[1])
    map.fitBounds([[Math.min(...lats), Math.min(...lons)], [Math.max(...lats), Math.max(...lons)]], { padding: [30, 30], maxZoom: focus ? 16 : 9 })
  }, [data, focus, map])
  return null
}

export default function Records() {
  const { can } = useAuth()
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const focus = params.get('focus') ? Number(params.get('focus')) : null
  const [recs, setRecs] = useState(null)
  const [geo, setGeo] = useState(null)
  const [dilrmp, setDilrmp] = useState(null)
  const [error, setError] = useState(null)
  const [pushing, setPushing] = useState(null)
  const [query, setQuery] = useState('')
  const [onlyUnpushed, setOnlyUnpushed] = useState(false) // the tehsil's to-do: verified but not yet sent to LRMS
  const { t, lang } = useT()
  // LAND_CLASSES labels are "English · हिंदी"; show the half for the chosen language
  const landClass = (k) => LAND_CLASSES[k]?.split(' · ')[lang === 'hi' ? 1 : 0] || '—'

  const load = () => Promise.all([api.lrmsRecords({ limit: 200 }), api.parcels(), api.dilrmp()])
    .then(([r, g, d]) => { setRecs(r.records); setGeo(g); setDilrmp(d) }).catch(setError)
  useEffect(() => { load() }, [])

  const push = async (id) => {
    setPushing(id)
    try {
      const r = await api.lrmsPush(id)
      toast(`${t('Record')} #${id} ${t('sent to LRMS')}`, { body: `${t('Reference')} ${r.lrms_ref} (${t('simulated acknowledgement')})` })
      await load()
    } catch (e) { toast(t('LRMS push failed'), { type: 'error', body: e.message }) } finally { setPushing(null) }
  }
  // send every listed record that is not yet in LRMS, one after another, with one summary at the end
  const pushAll = async (rows) => {
    setPushing('all')
    let sent = 0
    for (const r of rows) {
      try { await api.lrmsPush(r.record_id); sent += 1 } catch { /* counted below as not sent */ }
    }
    toast(`${sent} ${t('records sent to LRMS')}`, sent === rows.length
      ? { body: t('simulated acknowledgement') }
      : { type: 'error', body: `${rows.length - sent} ${t('could not be sent')}` })
    await load()
    setPushing(null)
  }
  const style = useMemo(() => (f) => ({
    color: f.id === focus ? '#b91c1c' : '#0f3d3e', weight: f.id === focus ? 3 : 1.5, fillColor: '#f2c14e', fillOpacity: 0.45,
  }), [focus])

  if (error) return <ErrorNote error={error} />
  if (!recs) return <div className="space-y-4"><PageHeader title={t('Records & GIS')} /><div className="card"><SkeletonRows cols={7} /></div></div>

  const q = query.trim().toLowerCase()
  const searched = !q ? recs : recs.filter((r) => [r.account.khata_no, r.parcel?.khasra_no, r.location.village, r.location.district,
    ...(r.parcels || []).map((p) => p.khasra_no), ...r.account.owners.map((o) => o.name)].some((v) => String(v || '').toLowerCase().includes(q)))
  const shown = onlyUnpushed ? searched.filter((r) => !r.lrms_ref) : searched

  // the rows on screen (after search) as a spreadsheet; the BOM makes Excel read Hindi names correctly
  const downloadCsv = () => {
    const cell = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
    const head = ['record', 'owners', 'father / husband', 'khata', 'khasra', 'area', 'area_ha', 'class', 'village', 'tehsil', 'district',
      'verified by', 'source document', 'lrms ref']
    const rows = shown.map((r) => [r.record_id, r.account.owners.map((o) => o.name).join('; '),
      r.account.owners.map((o) => o.father_or_husband || '').join('; '), r.account.khata_no,
      (r.parcels?.length > 1 ? r.parcels : [r.parcel]).map((p) => p.khasra_no).join('; '), r.parcel.area, r.parcel.area_hectares,
      r.parcel.land_class, r.location.village, r.location.tehsil, r.location.district, r.provenance.verification,
      r.provenance.source_document_id, r.lrms_ref])
    const csv = '﻿' + [head, ...rows].map((row) => row.map(cell).join(',')).join('\r\n')
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    a.download = `landlekha-records-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
    toast(t('Downloaded') + ` ${rows.length} ` + t('records'))
  }
  return <div className="space-y-4">
    <PageHeader title={t('Records & GIS')} subtitle={t('Verified records in LRMS exchange format, parcel map, and DILRMP progress report')} />
    <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
      <div className="card overflow-hidden">
        <div className="border-b border-slate-100 px-4 py-2 text-xs text-slate-500">{t('Parcel map')} · {t('geometry is synthetic in this prototype (placed near district HQ, sized by area)')}</div>
        <div className="h-96">
          <MapContainer center={[25.5, 80]} zoom={5} className="h-full w-full" scrollWheelZoom>
            <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {/* lang in the key: Leaflet popups are plain HTML built once, so rebuild them on a language switch */}
            {geo && <GeoJSON key={`${geo.features.length}-${focus}-${lang}`} data={geo} style={style}
              onEachFeature={(f, layer) => layer.bindPopup(
                `<b>${t('Khasra')} ${f.properties.khasra_no}</b> · ${t('Khata')} ${f.properties.khata_no}<br/>${f.properties.owner}<br/>${f.properties.village}, ${f.properties.district}<br/>${f.properties.area_hectares ?? '?'} ha`)} />}
            {/* parcels are a few hectares: invisible at state zoom, so also mark their centroids */}
            {geo?.features.map((f) => {
              const ring = f.geometry.coordinates[0]
              const lat = ring.reduce((a, c) => a + c[1], 0) / ring.length
              const lon = ring.reduce((a, c) => a + c[0], 0) / ring.length
              return <CircleMarker key={f.id} center={[lat, lon]} radius={f.id === focus ? 9 : 6}
                pathOptions={{ color: f.id === focus ? '#b91c1c' : '#0f3d3e', fillColor: '#f2c14e', fillOpacity: 0.9, weight: 2 }}
                eventHandlers={{ click: () => setParams({ focus: f.id }) }}>
                <Popup><b>{t('Khasra')} {f.properties.khasra_no}</b> · {t('Khata')} {f.properties.khata_no}<br />{f.properties.owner}<br />
                  {f.properties.village}, {f.properties.district} · {f.properties.area_hectares ?? '?'} ha</Popup>
              </CircleMarker>
            })}
            <FitBounds data={geo} focus={focus} />
          </MapContainer>
        </div>
      </div>
      <div className="card p-4">
        <div className="font-medium">{t('DILRMP progress report')}</div>
        <div className="text-xs text-slate-500 mb-3">GET /api/integration/dilrmp/progress</div>
        {dilrmp?.states.length ? dilrmp.states.map((s) => <div key={s.state} className="mb-3">
          <div className="flex justify-between text-sm font-medium"><span>{t(s.state)}</span><span className="tabular-nums">{s.digitized}/{s.documents_received} · {s.progress_pct}%</span></div>
          <div className="h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-brand-600" style={{ width: `${s.progress_pct}%` }} /></div>
          {s.districts.map((d) => <div key={d.district} className="mt-1 flex justify-between pl-3 text-xs text-slate-600">
            {/* place names pass through t() unchanged; only the backend's "Unknown" placeholder is translated */}
            <span>{t(d.district)}</span><span className="tabular-nums">{d.digitized}/{d.documents_received} {t('digitized')} · {d.pending_verification} {t('pending')}</span></div>)}
        </div>) : <Empty>{t('No data yet.')}</Empty>}
      </div>
    </div>

    <div className="card">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <div className="font-medium">{t('Land records')} ({shown.length}{(query || onlyUnpushed) && ` / ${recs.length}`})</div>
        <div className="flex w-full flex-wrap gap-2 sm:w-auto">
          <div className="relative min-w-0 flex-1 sm:w-72 sm:flex-none"><Search size={15} className="absolute left-3 top-2.5 text-slate-500" />
            <input className="input pl-9" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('Owner, khata, khasra or village')} aria-label={t('Search records')} /></div>
          <button onClick={() => setOnlyUnpushed((v) => !v)} aria-pressed={onlyUnpushed}
            className={`min-h-9 rounded-full border px-3 text-xs font-medium transition-colors duration-200 ${onlyUnpushed
              ? 'border-brand-700 bg-brand-700 text-white' : 'border-slate-300 bg-white text-slate-700 hover:border-brand-500 hover:text-brand-700'}`}>
            {t('Not sent to LRMS')}</button>
          {onlyUnpushed && can('verifier') && shown.some((r) => !r.lrms_ref) &&
            <button className="btn-primary" disabled={pushing != null} onClick={() => pushAll(shown.filter((r) => !r.lrms_ref))}>
              <Send size={15} /> {pushing === 'all' ? t('Sending…') : `${t('Send all to LRMS')} (${shown.filter((r) => !r.lrms_ref).length})`}</button>}
          <button className="btn-outline" onClick={downloadCsv} disabled={!shown.length} title={t('Download these records as a spreadsheet (CSV)')}>
            <Download size={15} /> CSV</button>
        </div>
      </div>
      {recs.length === 0 ? <EmptyState icon={MapIcon} title={t('No verified records yet')}>{t('A record is created when a verifier approves a document, or when a document passes every check on its own.')}</EmptyState> : <>
        {/* a filter or search can leave nothing to show: say why instead of an empty list */}
        {shown.length === 0 && <div className="px-4 py-8 text-center text-sm text-slate-500">
          {onlyUnpushed && !query ? t('Every record has been sent to LRMS.') : t('Nothing matches this search.')}</div>}
        {/* phones: one card per record, with its actions in reach instead of off-screen table columns */}
        <ul className="divide-y divide-slate-100 sm:hidden">{shown.map((r) => <li key={r.record_id} className={`px-4 py-3 ${r.record_id === focus ? 'bg-amber-50' : ''}`}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="font-medium text-slate-900">{r.account.owners[0].name}</div>
              <div className="text-xs text-slate-500">{r.account.owners[0].father_or_husband}</div>
              {r.account.owners.length > 1 && <div className="text-xs text-brand-700">+ {r.account.owners.slice(1).map((o) => o.name).join(', ')}</div>}
            </div>
            <button className="shrink-0 text-xs tabular-nums text-slate-500 hover:underline" onClick={() => setParams({ focus: r.record_id })}>#{r.record_id}</button>
          </div>
          <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
            <div><dt className="inline text-slate-500">{t('Khata')}: </dt><dd className="inline tabular-nums text-slate-800">{r.account.khata_no}</dd></div>
            <div><dt className="inline text-slate-500">{t('Khasra')}: </dt><dd className="inline tabular-nums text-slate-800">{(r.parcels?.length > 1 ? r.parcels : [r.parcel]).map((p) => p.khasra_no).join(', ')}</dd></div>
            <div><dt className="inline text-slate-500">{t('Area')}: </dt><dd className="inline tabular-nums text-slate-800">{areaInLang(r.parcel.area, lang)}</dd></div>
            <div><dt className="inline text-slate-500">{t('Class')}: </dt><dd className="inline text-slate-800">{landClass(r.parcel.land_class)}</dd></div>
            <div className="col-span-2 text-slate-600">{r.location.village}, {r.location.tehsil}, {r.location.district}</div>
          </dl>
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            {r.lrms_ref ? <span className="text-xs font-mono text-ok">{r.lrms_ref}</span>
              : can('verifier') ? <button className="btn-outline py-1 text-xs" disabled={pushing === r.record_id || pushing === 'all'} onClick={() => push(r.record_id)}><Send size={13} /> {t('Push')}</button>
                : <span className="text-xs text-slate-500">{t('not pushed')}</span>}
            <Link className="btn-outline py-1 text-xs" to={`/records/${r.record_id}/extract`}>{t('Extract')}</Link>
            <Link className="ml-auto text-xs text-brand-700 hover:underline" to={`/documents/${r.provenance.source_document_id}`}>{t(r.provenance.verification === 'auto' ? 'auto' : 'human')} · {t('doc')} #{r.provenance.source_document_id}</Link>
          </div>
        </li>)}</ul>
        <div className="table-wrap hidden sm:block"><table className="data">
          <thead><tr><th>#</th><th>{t('Owner')}</th><th>{t('Khata')}</th><th>{t('Khasra')}</th><th>{t('Area')}</th><th>{t('Class')}</th><th>{t('Village / District')}</th><th>{t('Verified')}</th><th>LRMS</th><th><span className="sr-only">{t('Actions')}</span></th></tr></thead>
          <tbody>{shown.map((r) => <tr key={r.record_id} className={r.record_id === focus ? 'bg-amber-50' : ''}>
            <td className="tabular-nums text-slate-500"><button className="hover:underline" onClick={() => setParams({ focus: r.record_id })}>{r.record_id}</button></td>
            <td className="font-medium">{r.account.owners[0].name}<div className="text-xs font-normal text-slate-500">{r.account.owners[0].father_or_husband}</div>
              {r.account.owners.length > 1 && <div className="text-xs font-normal text-brand-700" title={r.account.owners.slice(1).map((o) => o.name).join(', ')}>
                + {r.account.owners.slice(1).map((o) => o.name).join(', ')}</div>}</td>
            <td className="tabular-nums">{r.account.khata_no}</td>
            <td className="tabular-nums">{(r.parcels?.length > 1 ? r.parcels : [r.parcel]).map((p) => p.khasra_no).join(', ')}
              {r.parcels?.length > 1 && <div className="text-xs text-slate-500">{r.parcels.length} {t('parcels')}</div>}</td>
            <td className="tabular-nums whitespace-nowrap">{areaInLang(r.parcel.area, lang)}{r.parcel.area_hectares != null && <div className="text-xs text-slate-500">{r.parcel.area_hectares} ha</div>}</td>
            <td className="text-xs">{landClass(r.parcel.land_class)}</td>
            <td>{r.location.village}<div className="text-xs text-slate-500">{r.location.tehsil}, {r.location.district}</div></td>
            <td><Link className="text-xs text-brand-700 hover:underline" to={`/documents/${r.provenance.source_document_id}`}>{t(r.provenance.verification === 'auto' ? 'auto' : 'human')} · {t('doc')} #{r.provenance.source_document_id}</Link></td>
            <td>{r.lrms_ref ? <span className="text-xs font-mono text-ok">{r.lrms_ref}</span>
              : can('verifier') ? <button className="btn-outline py-1 text-xs" disabled={pushing === r.record_id || pushing === 'all'} onClick={() => push(r.record_id)}><Send size={13} /> {t('Push')}</button>
                : <span className="text-xs text-slate-500">{t('not pushed')}</span>}</td>
            <td><Link className="btn-outline py-1 text-xs" to={`/records/${r.record_id}/extract`}>{t('Extract')}</Link></td>
          </tr>)}</tbody>
        </table></div></>}
    </div>
  </div>
}
