import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CircleMarker, GeoJSON, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import { Send } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Empty, ErrorNote, PageHeader, Spinner } from '../components/ui'
import { LAND_CLASSES } from '../constants'
import { useToast } from '../components/toast'

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

  const load = () => Promise.all([api.lrmsRecords({ limit: 200 }), api.parcels(), api.dilrmp()])
    .then(([r, g, d]) => { setRecs(r.records); setGeo(g); setDilrmp(d) }).catch(setError)
  useEffect(() => { load() }, [])

  const push = async (id) => {
    setPushing(id)
    try {
      const r = await api.lrmsPush(id)
      toast(`Record #${id} sent to LRMS`, { body: `Reference ${r.lrms_ref} (simulated acknowledgement)` })
      await load()
    } catch (e) { toast('LRMS push failed', { type: 'error', body: e.message }) } finally { setPushing(null) }
  }
  const style = useMemo(() => (f) => ({
    color: f.id === focus ? '#b91c1c' : '#0f3d3e', weight: f.id === focus ? 3 : 1.5, fillColor: '#f2c14e', fillOpacity: 0.45,
  }), [focus])

  if (error) return <ErrorNote error={error} />
  if (!recs) return <div className="flex justify-center p-16"><Spinner /></div>

  return <div className="space-y-4">
    <PageHeader title="Digitized records & GIS" subtitle="Verified records in LRMS exchange format, parcel map, and DILRMP progress report" />
    <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
      <div className="card overflow-hidden">
        <div className="border-b border-slate-100 px-4 py-2 text-xs text-slate-500">Parcel map · geometry is synthetic in this prototype (placed near district HQ, sized by area)</div>
        <div className="h-96">
          <MapContainer center={[25.5, 80]} zoom={5} className="h-full w-full" scrollWheelZoom>
            <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {geo && <GeoJSON key={`${geo.features.length}-${focus}`} data={geo} style={style}
              onEachFeature={(f, layer) => layer.bindPopup(
                `<b>Khasra ${f.properties.khasra_no}</b> · Khata ${f.properties.khata_no}<br/>${f.properties.owner}<br/>${f.properties.village}, ${f.properties.district}<br/>${f.properties.area_hectares ?? '?'} ha`)} />}
            {/* parcels are a few hectares: invisible at state zoom, so also mark their centroids */}
            {geo?.features.map((f) => {
              const ring = f.geometry.coordinates[0]
              const lat = ring.reduce((a, c) => a + c[1], 0) / ring.length
              const lon = ring.reduce((a, c) => a + c[0], 0) / ring.length
              return <CircleMarker key={f.id} center={[lat, lon]} radius={f.id === focus ? 9 : 6}
                pathOptions={{ color: f.id === focus ? '#b91c1c' : '#0f3d3e', fillColor: '#f2c14e', fillOpacity: 0.9, weight: 2 }}
                eventHandlers={{ click: () => setParams({ focus: f.id }) }}>
                <Popup><b>Khasra {f.properties.khasra_no}</b> · Khata {f.properties.khata_no}<br />{f.properties.owner}<br />
                  {f.properties.village}, {f.properties.district} · {f.properties.area_hectares ?? '?'} ha</Popup>
              </CircleMarker>
            })}
            <FitBounds data={geo} focus={focus} />
          </MapContainer>
        </div>
      </div>
      <div className="card p-4">
        <div className="font-medium">DILRMP progress report</div>
        <div className="text-xs text-slate-500 mb-3">GET /api/integration/dilrmp/progress</div>
        {dilrmp?.states.length ? dilrmp.states.map((s) => <div key={s.state} className="mb-3">
          <div className="flex justify-between text-sm font-medium"><span>{s.state}</span><span className="tabular-nums">{s.digitized}/{s.documents_received} · {s.progress_pct}%</span></div>
          <div className="h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-brand-600" style={{ width: `${s.progress_pct}%` }} /></div>
          {s.districts.map((d) => <div key={d.district} className="mt-1 flex justify-between pl-3 text-xs text-slate-600">
            <span>{d.district}</span><span className="tabular-nums">{d.digitized}/{d.documents_received} digitized · {d.pending_verification} pending</span></div>)}
        </div>) : <Empty>No data yet.</Empty>}
      </div>
    </div>

    <div className="card">
      <div className="border-b border-slate-100 px-4 py-3 font-medium">Land records ({recs.length})</div>
      {recs.length === 0 ? <Empty>No verified records yet.</Empty> :
        <div className="table-wrap"><table className="data">
          <thead><tr><th>#</th><th>Owner</th><th>Khata</th><th>Khasra</th><th>Area</th><th>Class</th><th>Village / District</th><th>Verified</th><th>LRMS</th><th /></tr></thead>
          <tbody>{recs.map((r) => <tr key={r.record_id} className={r.record_id === focus ? 'bg-amber-50' : ''}>
            <td className="tabular-nums text-slate-500"><button className="hover:underline" onClick={() => setParams({ focus: r.record_id })}>{r.record_id}</button></td>
            <td className="font-medium">{r.account.owners[0].name}<div className="text-xs font-normal text-slate-500">{r.account.owners[0].father_or_husband}</div>
              {r.account.owners.length > 1 && <div className="text-xs font-normal text-brand-700" title={r.account.owners.slice(1).map((o) => o.name).join(', ')}>
                + {r.account.owners.slice(1).map((o) => o.name).join(', ')}</div>}</td>
            <td className="tabular-nums">{r.account.khata_no}</td>
            <td className="tabular-nums">{(r.parcels?.length > 1 ? r.parcels : [r.parcel]).map((p) => p.khasra_no).join(', ')}
              {r.parcels?.length > 1 && <div className="text-xs text-slate-500">{r.parcels.length} parcels</div>}</td>
            <td className="tabular-nums whitespace-nowrap">{r.parcel.area}{r.parcel.area_hectares != null && <div className="text-xs text-slate-500">{r.parcel.area_hectares} ha</div>}</td>
            <td className="text-xs">{LAND_CLASSES[r.parcel.land_class]?.split(' · ')[0] || '—'}</td>
            <td>{r.location.village}<div className="text-xs text-slate-500">{r.location.tehsil}, {r.location.district}</div></td>
            <td><Link className="text-xs text-brand-700 hover:underline" to={`/documents/${r.provenance.source_document_id}`}>{r.provenance.verification === 'auto' ? 'auto' : 'human'} · doc #{r.provenance.source_document_id}</Link></td>
            <td>{r.lrms_ref ? <span className="text-xs font-mono text-ok">{r.lrms_ref}</span>
              : can('verifier') ? <button className="btn-outline py-1 text-xs" disabled={pushing === r.record_id} onClick={() => push(r.record_id)}><Send size={13} /> Push</button>
                : <span className="text-xs text-slate-500">not pushed</span>}</td>
            <td><Link className="btn-outline py-1 text-xs" to={`/records/${r.record_id}/extract`}>Extract</Link></td>
          </tr>)}</tbody>
        </table></div>}
    </div>
  </div>
}
