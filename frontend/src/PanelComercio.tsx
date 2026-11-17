import { useCallback, useEffect, useState } from 'react'
import './Extra.css'
import { API, authHeaders, cerrarSesion, getUser } from './auth'
import { RUBROS } from './rubros'

interface Local {
  nombre: string; rubros: string[]; modalidad: 'local' | 'online' | 'ambos'; zona: string
  localidad: string; direccion: string; telefono: string; instagram: string; sitio_web: string; descripcion: string
  sin_tacc: 'todo' | 'opciones' | 'no'; vegetariano: boolean; vegano: boolean; declaracion: boolean
}
const ZONAS = ['CABA', 'Provincia de Buenos Aires', 'Catamarca', 'Chaco', 'Chubut', 'Córdoba', 'Corrientes',
  'Entre Ríos', 'Formosa', 'Jujuy', 'La Pampa', 'La Rioja', 'Mendoza', 'Misiones', 'Neuquén', 'Río Negro',
  'Salta', 'San Juan', 'San Luis', 'Santa Cruz', 'Santa Fe', 'Santiago del Estero', 'Tierra del Fuego', 'Tucumán']
const VACIO: Local = { nombre: '', rubros: [], modalidad: 'local', zona: 'CABA', localidad: '', direccion: '', telefono: '', instagram: '', sitio_web: '', descripcion: '', sin_tacc: 'no', vegetariano: false, vegano: false, declaracion: false }
type Respuesta = { detail?: string; comercio?: (Local & { estado: string; nota_revision: string }) | null }

// Panel del comercio o emprendimiento: se guarda en la base y, una vez aprobado, Foody lo recomienda.
export default function PanelComercio({ onSalir, onUsuario }: { onSalir: () => void; onUsuario: () => void }) {
  const [loc, setLoc] = useState<Local>(VACIO)
  const [estado, setEstado] = useState('')
  const [nota, setNota] = useState('')
  const [msg, setMsg] = useState('')
  const [ok, setOk] = useState('')
  const [cargando, setCargando] = useState(true)

  const llamar = useCallback(async (init?: RequestInit) => {
    try {
      const r = await fetch(`${API}/api/comercio/mio`, { ...init, headers: authHeaders() })
      if (r.status === 401) { cerrarSesion(); window.location.reload() }
      return { ok: r.ok, data: (await r.json().catch(() => ({}))) as Respuesta }
    } catch { return { ok: false, data: { detail: 'No pude conectar con el servidor.' } as Respuesta } }
  }, [])

  useEffect(() => {
    let vivo = true
    llamar().then(r => {
      if (!vivo) return
      const c = r.data.comercio
      if (r.ok && c) { setLoc({ ...VACIO, ...c }); setEstado(c.estado); setNota(c.nota_revision || '') }
      if (!r.ok) setMsg(r.data.detail || 'No pude cargar los datos de tu comercio.')
      setCargando(false)
    })
    return () => { vivo = false }
  }, [llamar])

  async function guardar() {
    setMsg(''); setOk('')
    const r = await llamar({ method: 'PUT', body: JSON.stringify(loc) })
    if (!r.ok) { setMsg(r.data.detail || 'Revisá los datos del comercio.'); return }
    const c = r.data.comercio
    setEstado(c?.estado || 'pendiente'); setNota(c?.nota_revision || ''); setOk('Datos guardados.')
  }

  const texto = (k: 'nombre' | 'localidad' | 'direccion' | 'telefono' | 'instagram' | 'sitio_web', titulo: string, max: number, ayuda?: string) => (
    <div><label>{titulo}</label><input type="text" maxLength={max} value={loc[k]} placeholder={ayuda} onChange={e => setLoc({ ...loc, [k]: e.target.value })} /></div>
  )
  const alternar = (c: string) => setLoc({ ...loc, rubros: loc.rubros.includes(c) ? loc.rubros.filter(x => x !== c) : loc.rubros.length < 3 ? [...loc.rubros, c] : loc.rubros })
  const SIN_TACC: ['todo' | 'opciones' | 'no', string][] = [['todo', 'Todo lo que vendo es sin TACC'], ['opciones', 'Tengo opciones sin TACC'], ['no', 'No tengo opciones sin TACC']]
  const fisico = loc.modalidad !== 'online'
  const online = loc.modalidad !== 'local'
  const listo = loc.nombre.trim().length >= 2 && loc.rubros.length >= 1 && loc.localidad.trim().length >= 2 && loc.declaracion

  if (cargando) return <div className="ex-wrap"><p className="ex-note">Cargando...</p></div>
  const ESTADOS: Record<string, string> = {
    pendiente: 'Pendiente de revisión. Cuando se apruebe, Foody empieza a recomendar tu comercio.',
    aprobado: 'Aprobado: Foody ya puede recomendar tu comercio.',
    rechazado: 'Rechazado. Corregí los datos y volvé a guardar para que se revise de nuevo.',
    suspendido: 'Suspendido. Contactá a GastronomIA.',
  }
  return (
    <div className="ex-wrap">
      <div className="ex-row"><h2>Mi comercio</h2>
        <div style={{ marginLeft: 'auto' }} className="ex-row">
          <button className="ex-btn ex-ghost" onClick={onUsuario}>Usar Foody como usuario</button>
          <button className="ex-btn ex-ghost" onClick={onSalir}>Cerrar sesión</button>
        </div>
      </div>
      <p className="ex-sub">Cuenta: {getUser()?.email}. Completá los datos de tu comercio o emprendimiento (puede ser online y sin local físico): se guardan en la base de datos de GastronomIA.</p>
      {estado && <div className="ex-card"><span className="ex-pill">{estado}</span> {ESTADOS[estado] || ''}{nota && <p className="ex-note">Nota de la revisión: {nota}</p>}</div>}
      {msg && <div className="ex-msg">{msg}</div>}
      {ok && <div className="ex-ok">{ok}</div>}

      <div className="ex-card">
        <h3>Datos del comercio</h3>
        <div className="ex-grid">
          {texto('nombre', 'Nombre *', 120)}
          <div>
            <label>¿Cómo vendés? *</label>
            <select value={loc.modalidad} onChange={e => setLoc({ ...loc, modalidad: e.target.value as Local['modalidad'] })}>
              <option value="local">Tengo local físico</option>
              <option value="online">Soy un emprendimiento online (sin local)</option>
              <option value="ambos">Las dos cosas</option>
            </select>
          </div>
          <div>
            <label>Provincia *</label>
            <select value={loc.zona} onChange={e => setLoc({ ...loc, zona: e.target.value })}>
              {ZONAS.map(z => <option key={z} value={z}>{z === 'CABA' ? 'Ciudad de Buenos Aires (CABA)' : z}</option>)}
            </select>
          </div>
          {texto('localidad', 'Barrio o localidad donde atendés o entregás *', 80, 'Ej.: Lomas de Zamora')}
          {fisico && texto('direccion', 'Dirección del local *', 200)}
          {texto('telefono', 'Teléfono del comercio', 40)}
          {texto('instagram', online ? 'Instagram del emprendimiento *' : 'Instagram (opcional)', 31, '@usuario')}
          {texto('sitio_web', online ? 'Sitio web (alcanza con Instagram o sitio)' : 'Sitio web (opcional)', 300, 'https://...')}
        </div>
        <div style={{ marginTop: 12 }}>
          <label>Qué vendés * (hasta 3)</label>
          {RUBROS.map(([c, n]) => (
            <label className="ex-chk" key={c}><input type="checkbox" checked={loc.rubros.includes(c)} onChange={() => alternar(c)} />{n}</label>
          ))}
        </div>
        <div style={{ marginTop: 12 }}><label>Descripción</label><textarea maxLength={500} value={loc.descripcion} onChange={e => setLoc({ ...loc, descripcion: e.target.value })} /></div>
        <div style={{ marginTop: 12 }}>
          <label>Sin TACC</label>
          {SIN_TACC.map(([v, t]) => <label className="ex-radio" key={v}><input type="radio" name="tacc" checked={loc.sin_tacc === v} onChange={() => setLoc({ ...loc, sin_tacc: v })} />{t}</label>)}
          <p className="ex-note">Lo declarás vos: Foody lo informa como dato del comercio y sugiere confirmarlo con ustedes.</p>
        </div>
        <div style={{ margin: '12px 0' }}>
          <label className="ex-chk"><input type="checkbox" checked={loc.vegetariano} onChange={e => setLoc({ ...loc, vegetariano: e.target.checked })} />Opciones vegetarianas</label>
          <label className="ex-chk"><input type="checkbox" checked={loc.vegano} onChange={e => setLoc({ ...loc, vegano: e.target.checked })} />Opciones veganas</label>
        </div>
        <label className="ex-radio"><input type="checkbox" checked={loc.declaracion} onChange={e => setLoc({ ...loc, declaracion: e.target.checked })} />Declaro que soy responsable de este comercio o emprendimiento y que tiene al menos 6 meses de actividad. *</label>
        <p className="ex-note">Un administrador revisa cada comercio antes de que aparezca en Foody. Si modificás los datos, se vuelve a revisar. Cargá solo información del comercio, sin datos personales.</p>
        <button className="ex-btn" onClick={guardar} disabled={!listo}>{estado ? 'Guardar cambios' : 'Registrar mi comercio'}</button>
      </div>

      <div className="ex-card ex-soon">
        <div className="ex-row"><h3 style={{ margin: 0 }}>Plan Premium para comercios</h3><span className="ex-pill ex-prem">Próximamente</span></div>
        <ul className="ex-list" style={{ marginTop: 10 }}>
          <li>Mayor visibilidad, marcada como «Destacado», entre resultados relevantes.</li>
          <li>Promociones y descuentos para usuarios Premium.</li>
          <li>Menú ampliado y estadísticas de visitas.</li>
        </ul>
        <p className="ex-note">Todavía no está disponible.</p>
      </div>
    </div>
  )
}
