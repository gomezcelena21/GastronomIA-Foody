import { useCallback, useEffect, useState } from 'react'
import './Extra.css'
import { API, authHeaders, cerrarSesion } from './auth'
import { nombreRubro } from './rubros'

interface Item {
  id_comercio: number; email_dueno: string; nombre: string; rubros: string[]; modalidad: string; zona: string; localidad: string
  direccion: string; telefono: string; instagram: string; sitio_web: string; descripcion: string; sin_tacc: string
  vegetariano: boolean; vegano: boolean; declaracion: boolean; estado: string
}
type Estado = 'pendiente' | 'aprobado' | 'rechazado' | 'suspendido'

// Panel de administración: revisar comercios. Al aprobar, Foody empieza a recomendarlos.
export default function Admin({ onVolver }: { onVolver: () => void }) {
  const [estado, setEstado] = useState<Estado>('pendiente')
  const [lista, setLista] = useState<Item[]>([])
  const [notas, setNotas] = useState<Record<number, string>>({})
  const [msg, setMsg] = useState('')

  const cargar = useCallback(async (e: Estado) => {
    try {
      const r = await fetch(`${API}/api/admin/comercios?estado=${e}`, { headers: authHeaders() })
      if (r.status === 401) { cerrarSesion(); window.location.reload(); return }
      const d = (await r.json().catch(() => ({}))) as { comercios?: Item[]; detail?: string }
      if (!r.ok) { setMsg(d.detail || 'No pude cargar los comercios.'); return }
      setMsg(''); setLista(d.comercios || [])
    } catch { setMsg('No pude conectar con el servidor.') }
  }, [])
  useEffect(() => { cargar(estado) }, [cargar, estado])

  async function revisar(id: number, nuevo: 'aprobado' | 'rechazado' | 'suspendido') {
    setMsg('')
    try {
      const r = await fetch(`${API}/api/admin/comercios/${id}/estado`, { method: 'POST', headers: authHeaders(), body: JSON.stringify({ estado: nuevo, nota: notas[id] || '' }) })
      if (!r.ok) { const d = (await r.json().catch(() => ({}))) as { detail?: string }; setMsg(d.detail || 'No pude guardar la revisión.'); return }
      await cargar(estado)
    } catch { setMsg('No pude conectar con el servidor.') }
  }

  return (
    <div className="ex-wrap">
      <div className="ex-row"><h2>Revisión de comercios</h2><button className="ex-btn ex-ghost" style={{ marginLeft: 'auto' }} onClick={onVolver}>Volver</button></div>
      <p className="ex-sub">Antes de aprobar, revisá que el comercio exista y tenga al menos 6 meses de actividad (por ejemplo, mirando su Instagram o su sitio).</p>
      <div className="ex-row" style={{ marginBottom: 12 }}>
        {(['pendiente', 'aprobado', 'rechazado', 'suspendido'] as Estado[]).map(e => (
          <button key={e} className={e === estado ? 'ex-btn' : 'ex-btn ex-ghost'} onClick={() => setEstado(e)}>{e}</button>
        ))}
      </div>
      {msg && <div className="ex-msg">{msg}</div>}
      {lista.length === 0 && !msg && <p className="ex-note">No hay comercios en estado «{estado}».</p>}
      {lista.map(c => (
        <div className="ex-card" key={c.id_comercio}>
          <h3>{c.nombre}</h3>
          <p className="ex-note">{c.rubros.map(nombreRubro).join(', ')} · {c.modalidad} · {c.localidad} ({c.zona})</p>
          <ul className="ex-list">
            <li>Cuenta: {c.email_dueno}</li>
            {c.direccion && <li>Dirección: {c.direccion}</li>}
            {c.telefono && <li>Teléfono: {c.telefono}</li>}
            {c.instagram && <li>Instagram: <a href={`https://www.instagram.com/${c.instagram}`} target="_blank" rel="noopener noreferrer">@{c.instagram}</a></li>}
            {c.sitio_web && <li>Sitio: <a href={c.sitio_web} target="_blank" rel="noopener noreferrer">{c.sitio_web}</a></li>}
            <li>Sin TACC (declarado): {c.sin_tacc}{c.vegetariano ? ' · vegetariano' : ''}{c.vegano ? ' · vegano' : ''}</li>
            <li>Declaró ser responsable y tener 6+ meses de actividad: {c.declaracion ? 'sí' : 'no'}</li>
            {c.descripcion && <li>{c.descripcion}</li>}
          </ul>
          <label>Nota para el comercio (opcional)</label>
          <input type="text" maxLength={300} value={notas[c.id_comercio] || ''} onChange={e => setNotas({ ...notas, [c.id_comercio]: e.target.value })} />
          <div className="ex-row" style={{ marginTop: 10 }}>
            {c.estado !== 'aprobado' && <button className="ex-btn" onClick={() => revisar(c.id_comercio, 'aprobado')}>Aprobar</button>}
            {c.estado !== 'rechazado' && <button className="ex-btn ex-ghost" onClick={() => revisar(c.id_comercio, 'rechazado')}>Rechazar</button>}
            {c.estado === 'aprobado' && <button className="ex-btn ex-ghost" onClick={() => revisar(c.id_comercio, 'suspendido')}>Suspender</button>}
          </div>
        </div>
      ))}
    </div>
  )
}
