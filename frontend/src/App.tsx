import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import bot from './assets/foody.webp'
import './App.css'
import { API, GOOGLE_CLIENT_ID, authHeaders, cerrarSesion, entrarComoInvitado, getRol, getToken, getUser, guardarRol, guardarSesion, sesionVigente, type Rol, type Sesion } from './auth'
import PanelComercio from './PanelComercio'
import Premium from './Premium'
import Admin from './Admin'

interface Place { id: number; name: string; zone: string; cuisine: string[]; lat?: number; lon?: number; rating?: number; reviews?: number; hours?: string; price?: number; src?: string; tacc?: boolean; veg?: boolean; vegan?: boolean }
interface Msg { role: 'user' | 'bot'; text: string; places?: Place[] }
interface Prof { name: string; email: string; bio: string; cuisines: string[]; tacc: boolean; veg: boolean; vegan: boolean; province: string }
type Tab = 'chat' | 'explorar' | 'lugares' | 'favoritos' | 'perfil' | 'premium'
const TABS_OK: Tab[] = ['chat', 'explorar', 'lugares', 'favoritos', 'perfil', 'premium']
// Cada pestaña tiene su propia URL: /explorar, /lugares, /favoritos, /perfil y /premium.
const RUTA_TAB: Record<string, Tab> = { '/chat': 'chat', '/explorar': 'explorar', '/lugares': 'lugares', '/favoritos': 'favoritos', '/premium': 'premium', '/perfil': 'perfil' }
const TAB_RUTA: Record<Tab, string> = { chat: '/chat', explorar: '/explorar', lugares: '/lugares', favoritos: '/favoritos', premium: '/premium', perfil: '/perfil' }
// La página de inicio (Landing) deja anotada la sección y la búsqueda con las que se abre la aplicación.
const tabInicial = (): Tab => {
  const desdeRuta = RUTA_TAB[window.location.pathname.replace(/\/+$/, '')]
  if (desdeRuta) return desdeRuta
  try { const t = sessionStorage.getItem('foody_tab') as Tab | null; return t && TABS_OK.includes(t) ? t : 'chat' } catch { return 'chat' }
}
const consultaInicial = (): string => { try { return sessionStorage.getItem('foody_q') || '' } catch { return '' } }

const DEF: Prof = { name: '', email: '', bio: '', cuisines: [], tacc: false, veg: false, vegan: false, province: 'Buenos Aires' }
const CUIS: [string, string][] = [['Todas', ''], ['Italiana', 'italiana'], ['Pizza', 'pizzeria'], ['Hamburguesas', 'hamburguesa'], ['Sushi', 'japonesa'], ['Asiática', 'asiatica'], ['Parrilla', 'parrilla'], ['Café', 'cafe'], ['Comida rápida', 'comida_rapida']]
const EMO: Record<string, string> = { pizzeria: '🍕', hamburguesa: '🍔', japonesa: '🍣', cafe: '☕', parrilla: '🥩', italiana: '🍝', asiatica: '🥢', china: '🥡', mexicana: '🌮', comida_rapida: '🍟', peruana: '🐟', sandwicheria: '🥪' }
const TABS: [Tab, string, string][] = [['chat', '💬', 'Chat'], ['explorar', '🔍', 'Explorar'], ['lugares', '📍', 'Mis lugares'], ['favoritos', '♡', 'Favoritos'], ['premium', '💎', 'Premium'], ['perfil', '👤', 'Perfil']]
const SUG = ['Restaurantes en Palermo', 'Opciones sin TACC en Belgrano', 'Parrillas en Recoleta', 'Comida vegana en Caballito']

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const norm = (r: any): Place => {
  const f = r.features || r
  return {
    id: r.restaurant_id, name: r.name, zone: [r.neighborhood, r.city].filter(Boolean).join(', '),
    cuisine: r.cuisine_type || [], lat: r.latitude ?? undefined, lon: r.longitude ?? undefined,
    rating: r.rating ?? undefined, reviews: r.review_count ?? undefined, hours: r.opening_hours ?? undefined,
    price: r.price_range ?? undefined, src: r.source_name ?? r.source?.name ?? undefined, tacc: f.has_gluten_free_options, veg: f.has_vegetarian_options, vegan: f.has_vegan_options,
  }
}
const label = (c: string) => c.replace(/_/g, ' ')
const emo = (p: Place) => EMO[p.cuisine.find(c => EMO[c]) || ''] || '🍽️'
const grad = (id: number) => `linear-gradient(135deg,hsl(${(id * 47) % 360} 85% 90%),hsl(${(id * 47 + 60) % 360} 85% 80%))`

function useLS<T>(k: string, init: T): [T, (v: T) => void] {
  const [v, s] = useState<T>(() => { try { const x = localStorage.getItem(k); return x ? JSON.parse(x) : init } catch { return init } })
  return [v, (n: T) => { s(n); try { localStorage.setItem(k, JSON.stringify(n)) } catch { /* sin storage */ } }]
}

interface GIS { accounts: { id: { initialize: (c: { client_id: string; callback: (r: { credential: string }) => void }) => void; renderButton: (el: HTMLElement, o: Record<string, unknown>) => void } } }
const gis = () => (window as unknown as { google?: GIS }).google

// Botón oficial de Google: devuelve un token que el backend verifica (/api/auth/google). No se guardan contraseñas.
function GoogleBtn({ onUser, onError }: { onUser: (u: Sesion) => void; onError: (m: string) => void }) {
  const ref = useRef<HTMLDivElement>(null)
  const cb = useRef({ onUser, onError })
  cb.current = { onUser, onError }
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) { cb.current.onError('Falta configurar VITE_GOOGLE_CLIENT_ID (ver docs/despliegue_y_login.md).'); return }
    const iniciar = () => {
      const g = gis()
      if (!g || !ref.current) return
      // React StrictMode monta el efecto dos veces en desarrollo: si el botón
      // ya se dibujó, no se duplica.
      if (ref.current.childElementCount > 0) return
      g.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async r => {
          try {
            const res = await fetch(`${API}/api/auth/google`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ credential: r.credential }) })
            const d = await res.json().catch(() => ({}))
            if (!res.ok) { cb.current.onError(d.detail || 'No pudimos iniciar sesión. Probá de nuevo.'); return }
            guardarSesion(d.token, d.usuario)
            cb.current.onUser(d.usuario)
          } catch { cb.current.onError('No pude conectar con el servidor.') }
        },
      })
      g.accounts.id.renderButton(ref.current, { theme: 'outline', size: 'large', shape: 'pill', text: 'continue_with', width: 280 })
    }
    if (gis()) { iniciar(); return }
    const sc = document.createElement('script')
    sc.src = 'https://accounts.google.com/gsi/client'
    sc.async = true
    sc.onload = iniciar
    document.head.appendChild(sc)
  }, [])
  return <div ref={ref} className="gwrap" />
}

function Login({ onEnter }: { onEnter: (u?: Sesion) => void }) {
  const word = 'GastronomIA'
  const [n, setN] = useState(0)
  const [stage, setStage] = useState(0)
  const [msg, setMsg] = useState('')
  useEffect(() => {
    if (stage !== 0) return
    const t = setTimeout(() => (n < word.length ? setN(n + 1) : setStage(1)), n < word.length ? 115 : 850)
    return () => clearTimeout(t)
  }, [n, stage])
  useEffect(() => {
    if (stage !== 1) return
    const t = setTimeout(() => setStage(2), 2400)
    return () => clearTimeout(t)
  }, [stage])
  return (
    <main className="login">
      <div className="scene">
        {stage === 0 && <div className="typed">{word.slice(0, Math.min(n, 9))}<span className="ia">{word.slice(9, n)}</span><i className="caret" /></div>}
        {stage >= 1 && (
          <div className="auth">
            <img className="bot" src={bot} alt="Foody" style={{ width: stage === 1 ? 230 : 150 }} />
            <h1>Hola, soy <b>Foody</b>,</h1>
            <p>tu asistente de gastronomía.</p>
            {stage === 2 && (
              <div className="opts">
                <GoogleBtn onUser={onEnter} onError={setMsg} />
                <button className="obtn" onClick={() => { entrarComoInvitado(); guardarRol('usuario'); onEnter() }}>Continuar sin registrarme</button>
                <small>{msg || 'Sin registrarte tenés un cupo diario de consultas. Con Google es mayor y se guarda tu historial. Si tenés un comercio, ingresá con Google y después entrá a Perfil → Mi comercio.'}</small>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  )
}

function Card({ p, fav, saved, onFav, onSave, onFicha, route }: { p: Place; fav: boolean; saved: boolean; onFav: () => void; onSave: () => void; onFicha?: () => void; route?: boolean }) {
  const q = p.lat && p.lon ? `${p.lat},${p.lon}` : encodeURIComponent(`${p.name} ${p.zone}`)
  const url = `https://www.google.com/maps/${route ? 'dir/?api=1&destination=' : 'search/?api=1&query='}${q}`
  return (
    <div className="card">
      <div className="pic" style={{ background: grad(p.id) }}>
        <span>{emo(p)}</span>
        <button className={'ico' + (fav ? ' on' : '')} title="Favorito" onClick={onFav}>{fav ? '♥' : '♡'}</button>
        <button className={'ico sv' + (saved ? ' on' : '')} title="Guardar en Mis lugares" onClick={onSave}>{saved ? '✓' : '+'}</button>
      </div>
      <h4>{p.name}</h4>
      <p className="m">📍 {p.zone || 'Argentina'}</p>
      {p.cuisine.length > 0 && <p className="m">🍴 {p.cuisine.slice(0, 2).map(label).join(' · ')}</p>}
      {p.rating && <p className="m">⭐ {p.rating}{p.reviews ? ` (${p.reviews} reseñas)` : ''}</p>}
      {p.hours && <p className="m ok">🕒 {p.hours}</p>}
      {p.price && <p className="m">{'$'.repeat(p.price)}</p>}
      {p.src && <p className="m">Fuente: {p.src}</p>}
      <div className="tags">{p.tacc && <i>Sin TACC</i>}{p.veg && <i>Vegetariano</i>}{p.vegan && <i>Vegano</i>}</div>
      {onFicha && <button className="btn" onClick={onFicha}>Ver ficha ›</button>}
      <a className="btn" href={url} target="_blank" rel="noreferrer noopener">{route ? 'Crear ruta' : 'Ver en Maps'} ›</a>
    </div>
  )
}

type CP = (p: Place) => { p: Place; fav: boolean; saved: boolean; onFav: () => void; onSave: () => void; onFicha: () => void }

function Hero({ t, s }: { t: string; s: string }) {
  return <div className="hero"><img src={bot} alt="" /><div><h2>{t}</h2><p>{s}</p></div></div>
}

interface ChatResumen { chat_id: string; titulo: string; fecha?: string | null; mensajes?: number }

function Chat({ cp, prof, on }: { cp: CP; prof: Prof; on: boolean }) {
  const first: Msg = { role: 'bot', text: '¡Hola! Soy **Foody**, tu asistente gastronómico. Puedo ayudarte a encontrar lugares en toda la Argentina, con opciones sin TACC, vegetarianas o veganas.' }
  const cuenta = !!getToken()
  const uid = getUser()?.id_usuario
  // Cada cuenta recuerda en qué conversación estaba; el invitado empieza una nueva en cada pestaña.
  const claveChat = `foody_chat_${uid ?? 0}`
  const [msgs, setMsgs] = useState<Msg[]>([first])
  const [txt, setTxt] = useState(consultaInicial)
  useEffect(() => { try { sessionStorage.removeItem('foody_q') } catch { /* sin storage */ } }, [])
  const [busy, setBusy] = useState(false)
  const [chats, setChats] = useState<ChatResumen[]>([])
  const [chatId, setChatId] = useState<string>(() => {
    if (!cuenta) return 'session_' + Date.now()
    try { return localStorage.getItem(claveChat) || 'principal' } catch { return 'principal' }
  })
  // Descarta la respuesta de un historial que ya no es el que se está mirando.
  const pedido = useRef(0)
  const bandeja = useRef<HTMLDivElement>(null)
  // Solo se desplaza la lista de mensajes, nunca la página completa.
  useEffect(() => {
    const caja = bandeja.current
    if (caja) caja.scrollTo({ top: caja.scrollHeight, behavior: 'smooth' })
  }, [msgs, busy])
  const recordar = (id: string) => { if (cuenta) { try { localStorage.setItem(claveChat, id) } catch { /* sin storage */ } } }
  const cargarChats = () => {
    if (!cuenta) return
    fetch(`${API}/api/chat/conversaciones`, { headers: authHeaders() })
      .then(r => { if (r.status === 401) { cerrarSesion(); window.location.reload() } return r.ok ? r.json() : { conversaciones: [] } })
      .then(d => setChats(d.conversaciones || []))
      .catch(() => { /* sin servidor */ })
  }
  // Abre una conversación: si es de la cuenta, trae sus mensajes del servidor.
  const abrir = async (id: string) => {
    const mio = ++pedido.current
    setChatId(id); recordar(id); setMsgs([first])
    if (!cuenta) return
    try {
      const r = await fetch(`${API}/api/chat/historial?chat_id=${encodeURIComponent(id)}`, { headers: authHeaders() })
      if (r.status === 401) { cerrarSesion(); window.location.reload(); return }
      if (!r.ok) return
      const d = await r.json()
      if (mio !== pedido.current) return
      if (d.mensajes?.length) setMsgs([first, ...d.mensajes.map((m: { rol: string; contenido: string }) => ({ role: m.rol === 'usuario' ? 'user' : 'bot', text: m.contenido }) as Msg)])
    } catch { /* sin servidor */ }
  }
  // Al entrar, se retoma la última conversación de la cuenta (o la que se estaba mirando).
  useEffect(() => {
    if (!cuenta) return          // el invitado no tiene historial guardado
    let vivo = true
    fetch(`${API}/api/chat/conversaciones`, { headers: authHeaders() })
      .then(r => { if (r.status === 401) { cerrarSesion(); window.location.reload() } return r.ok ? r.json() : { conversaciones: [] } })
      .then(d => {
        if (!vivo) return
        const lista: ChatResumen[] = d.conversaciones || []
        setChats(lista)
        const elegido = lista.some(c => c.chat_id === chatId) ? chatId : (lista[0]?.chat_id || 'principal')
        abrir(elegido)
      })
      .catch(() => { /* sin servidor */ })
    return () => { vivo = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  function nuevoChat() {
    const id = (cuenta ? 'chat_' : 'session_') + Date.now()
    pedido.current++            // ignora cualquier historial que estuviera cargando
    setChatId(id); recordar(id); setMsgs([first]); setBusy(false)
  }
  async function send(t: string) {
    const m = t.trim()
    if (!m || busy) return
    setTxt(''); setBusy(true); setMsgs(x => [...x, { role: 'user', text: m }])
    const f = [prof.tacc && 'Requiere opciones sin TACC (celiaquía)', prof.veg && 'Busca opciones vegetarianas', prof.vegan && 'Busca opciones veganas'].filter(Boolean)
    try {
      const r = await fetch(`${API}/api/chat`, { method: 'POST', headers: authHeaders(), body: JSON.stringify({ message: f.length ? `${m}\n\n[Filtros activos: ${f.join(', ')}]` : m, session_id: chatId, chat_id: cuenta ? chatId : '' }) })
      if (r.status === 401) { cerrarSesion(); window.location.reload(); return }
      const d = await r.json()
      const aviso = r.status === 429 ? (d.detail || 'Estás escribiendo muy rápido. Esperá un minuto y probá de nuevo.') : 'No pude procesar tu mensaje. Probá de nuevo.'
      setMsgs(x => [...x, { role: 'bot', text: r.ok ? d.response : aviso, places: r.ok ? (d.restaurants || []).map(norm) : [] }])
      if (r.ok) cargarChats()     // el primer mensaje pasa a ser el título de la conversación
    } catch {
      setMsgs(x => [...x, { role: 'bot', text: 'Disculpá, no pude conectar con el servidor. Verificá que el backend esté corriendo.' }])
    } finally { setBusy(false) }
  }
  return (
    <section className={'chat' + (on ? '' : ' off')}>
      <div className="chatbar">
        <button className="nuevo" onClick={nuevoChat} title="Empezar una conversación nueva">＋ Nuevo chat</button>
        {cuenta && chats.length > 0 && (
          <select className="chatsel" value={chatId} onChange={e => abrir(e.target.value)}
            aria-label="Conversaciones anteriores" title="Conversaciones anteriores">
            {!chats.some(c => c.chat_id === chatId) && <option value={chatId}>Chat nuevo</option>}
            {chats.map(c => <option key={c.chat_id} value={c.chat_id}>{c.titulo}</option>)}
          </select>
        )}
      </div>
      <div className="msgs" ref={bandeja}>
        {msgs.map((m, i) => (
          <div key={i} className={'row ' + m.role}>
            {m.role === 'bot' && <img src={bot} alt="" className="av" />}
            <div className="col">
              <div className="bub"><Markdown>{m.text}</Markdown></div>
              {m.places && m.places.length > 0 && <div className="strip">{m.places.slice(0, 6).map(p => <Card key={p.id} {...cp(p)} />)}</div>}
            </div>
          </div>
        ))}
        {msgs.length === 1 && <div className="sug">{SUG.map(s => <button key={s} onClick={() => send(s)}>{s}</button>)}</div>}
        {busy && <div className="row bot"><img src={bot} alt="" className="av" /><div className="bub dots">Foody está buscando…</div></div>}
      </div>
      <div className="inp">
        <input value={txt} placeholder="Escribí tu mensaje…" onChange={e => setTxt(e.target.value)} onKeyDown={e => e.key === 'Enter' && send(txt)} />
        <button className="send" onClick={() => send(txt)} disabled={busy}>➤</button>
      </div>
    </section>
  )
}

function Explore({ cp, prof, provs, q }: { cp: CP; prof: Prof; provs: string[]; q: string }) {
  const [prov, setProv] = useState(prof.province)
  const [zone, setZone] = useState('')
  const [cu, setCu] = useState('')
  const [d, setD] = useState({ tacc: prof.tacc, veg: prof.veg, vegan: prof.vegan })
  const [items, setItems] = useState<Place[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const [sel, setSel] = useState<Place | null>(null)
  useEffect(() => {
    const ctl = new AbortController()
    const p = new URLSearchParams({ limit: '30' })
    if (prov) p.set('province', prov)
    if (zone) p.set('neighborhood', zone)
    if (cu) p.set('cuisine', cu)
    if (q) p.set('search', q)
    if (d.tacc) p.set('gluten_free', 'true')
    if (d.veg) p.set('vegetarian', 'true')
    if (d.vegan) p.set('vegan', 'true')
    const t = setTimeout(() => {
      setLoading(true)
      fetch(`${API}/api/restaurants?${p}`, { signal: ctl.signal }).then(r => r.json()).then(j => {
        const l: Place[] = (j.results || []).map(norm)
        setItems(l); setTotal(j.total || 0); setSel(l.find(x => x.lat && x.lon) || null); setErr(''); setLoading(false)
      }).catch(e => { if (e.name !== 'AbortError') { setErr('No pude conectar con el servidor (¿está corriendo en el puerto 8001?)'); setLoading(false) } })
    }, 250)
    return () => { clearTimeout(t); ctl.abort() }
  }, [prov, zone, cu, q, d])
  const map = sel && sel.lat && sel.lon ? `https://www.openstreetmap.org/export/embed.html?bbox=${sel.lon - 0.01},${sel.lat - 0.007},${sel.lon + 0.01},${sel.lat + 0.007}&layer=mapnik&marker=${sel.lat},${sel.lon}` : ''
  return (
    <>
      <Hero t="¡Descubrí los mejores lugares para disfrutar!" s="Explorá restaurantes y cafeterías según tu zona y tus restricciones alimentarias." />
      <div className="filters">
        <select value={prov} onChange={e => setProv(e.target.value)}><option value="">Todo el país</option>{provs.map(x => <option key={x}>{x}</option>)}</select>
        <input value={zone} placeholder="Barrio (ej. Palermo)" onChange={e => setZone(e.target.value)} />
      </div>
      <div className="pills">
        {CUIS.map(([l, v]) => <button key={l} className={cu === v ? 'on' : ''} onClick={() => setCu(v)}>{l}</button>)}
        <span className="sep" />
        <button className={d.tacc ? 'on' : ''} onClick={() => setD({ ...d, tacc: !d.tacc })}>🌾 Sin TACC</button>
        <button className={d.veg ? 'on' : ''} onClick={() => setD({ ...d, veg: !d.veg })}>🥗 Vegetariano</button>
        <button className={d.vegan ? 'on' : ''} onClick={() => setD({ ...d, vegan: !d.vegan })}>🌱 Vegano</button>
      </div>
      <div className="split">
        <div className="list">
          <div className="cnt">{loading ? 'Buscando…' : `${total.toLocaleString('es-AR')} lugares${prov ? ' en ' + prov : ''}${q ? ` para “${q}”` : ''}`}</div>
          {err && <div className="empty">{err}</div>}
          {!err && !loading && items.length === 0 && <div className="empty">No encontré lugares con esos filtros.</div>}
          {items.map(p => (
            <div key={p.id} className={'li' + (sel?.id === p.id ? ' sel' : '')} onClick={() => setSel(p)}>
              <div className="th" style={{ background: grad(p.id) }}>{emo(p)}</div>
              <div className="inf"><b>{p.name}</b><span>{p.cuisine.slice(0, 2).map(label).join(' · ') || 'Gastronomía'}</span><span>📍 {p.zone || 'Argentina'}</span>
                <div className="tags">{p.tacc && <i>Sin TACC</i>}{p.veg && <i>Vegetariano</i>}{p.vegan && <i>Vegano</i>}</div></div>
              <div className="acts">
                <button className="ico" onClick={e => { e.stopPropagation(); cp(p).onFav() }}>{cp(p).fav ? '♥' : '♡'}</button>
                <button className="ico" onClick={e => { e.stopPropagation(); cp(p).onSave() }}>{cp(p).saved ? '✓' : '+'}</button>
              </div>
            </div>
          ))}
        </div>
        <div className="map">{map ? <iframe title="mapa" src={map} /> : <div className="empty">Elegí un lugar con ubicación para verlo en el mapa.</div>}</div>
      </div>
    </>
  )
}

function Saved({ list, cp, t, s, route }: { list: Place[]; cp: CP; t: string; s: string; route?: boolean }) {
  return (
    <>
      <Hero t={t} s={s} />
      {list.length === 0 ? <div className="empty">Todavía no hay lugares acá. Explorá y tocá ♡ o + en cualquier lugar.</div>
        : <div className="grid">{list.map(p => <Card key={p.id} {...cp(p)} route={route} />)}</div>}
    </>
  )
}

function Profile({ prof, set, provs, out, cuenta, tieneComercio, esAdmin, onRol }: {
  prof: Prof; set: (p: Prof) => void; provs: string[]; out: () => void
  cuenta: boolean; tieneComercio: boolean; esAdmin: boolean; onRol: (r: 'comercio' | 'admin') => void
}) {
  const [edit, setEdit] = useState(false)
  const tg = (c: string) => set({ ...prof, cuisines: prof.cuisines.includes(c) ? prof.cuisines.filter(x => x !== c) : [...prof.cuisines, c] })
  return (
    <>
      <div className="hero prof">
        <img src={bot} alt="" />
        <div>
          {edit ? <><input value={prof.name} onChange={e => set({ ...prof, name: e.target.value })} /><input value={prof.email} readOnly title="Es el correo de tu cuenta de Google" /><input value={prof.bio} onChange={e => set({ ...prof, bio: e.target.value })} /></>
            : <><h2>{prof.name}</h2><p>✉ {prof.email}</p><p>{prof.bio}</p></>}
        </div>
        <button className="edit" onClick={() => setEdit(!edit)}>{edit ? 'Listo' : '✎ Editar perfil'}</button>
      </div>
      <div className="two">
        <div className="panel">
          <h3>🍴 Mis preferencias alimentarias</h3>
          <p>Tipos de comida que más te gustan:</p>
          <div className="pills">{CUIS.slice(1).map(([l, v]) => <button key={v} className={prof.cuisines.includes(v) ? 'on' : ''} onClick={() => tg(v)}>{EMO[v]} {l}</button>)}</div>
          <p>Restricciones (se aplican por defecto al explorar y en el chat):</p>
          <div className="pills">
            <button className={prof.tacc ? 'on' : ''} onClick={() => set({ ...prof, tacc: !prof.tacc })}>🌾 Sin TACC</button>
            <button className={prof.veg ? 'on' : ''} onClick={() => set({ ...prof, veg: !prof.veg })}>🥗 Vegetariano</button>
            <button className={prof.vegan ? 'on' : ''} onClick={() => set({ ...prof, vegan: !prof.vegan })}>🌱 Vegano</button>
          </div>
        </div>
        <div className="panel">
          <h3>📍 Mi zona de residencia</h3>
          <p>Zona de búsqueda principal:</p>
          <select value={prof.province} onChange={e => set({ ...prof, province: e.target.value })}>{(provs.length ? provs : [prof.province]).map(x => <option key={x}>{x}</option>)}</select>
          <button className="out" onClick={out}>Cerrar sesión</button>
        </div>
      </div>
      {cuenta && (
        <div className="panel" id="mi-comercio">
          <h3>🏪 Mi comercio</h3>
          <p>{tieneComercio
            ? 'Ya registraste un comercio con esta cuenta. Podés ver su estado o editar sus datos.'
            : 'Si tenés un local o un emprendimiento, sumalo para que Foody lo recomiende. Un administrador lo revisa antes de publicarlo.'}</p>
          <button className="ex-btn" onClick={() => onRol('comercio')}>{tieneComercio ? 'Ir a mi comercio' : 'Registrar mi comercio'}</button>
          {esAdmin && <button className="ex-btn ex-ghost" onClick={() => onRol('admin')}>🛠 Administración: revisar comercios</button>}
        </div>
      )}
    </>
  )
}


interface Detalle {
  name: string; address?: string; neighborhood?: string; city?: string; phone?: string; website?: string; opening_hours?: string
  rating?: number; price_range?: number; data_date?: string; advertencia_alimentaria?: string | null
  features?: { has_gluten_free_options?: boolean; has_vegetarian_options?: boolean; has_vegan_options?: boolean; has_lactose_free_options?: boolean }
  source?: { name?: string; url?: string; reliability?: string; last_updated?: string } | null
}
const esWeb = (u?: string) => !!u && /^https?:\/\//i.test(u)

// Ficha del establecimiento: contacto, fuente, advertencia alimentaria y por qué se recomienda
function Ficha({ p, prof, onClose }: { p: Place; prof: Prof; onClose: () => void }) {
  const [d, setD] = useState<Detalle | null>(null)
  const [err, setErr] = useState(false)
  useEffect(() => {
    fetch(`${API}/api/establecimientos/${p.id}`).then(r => { if (!r.ok) throw new Error(); return r.json() }).then(setD).catch(() => setErr(true))
  }, [p.id])
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [onClose])
  const f = d?.features
  const porque = [
    prof.tacc && f?.has_gluten_free_options && 'Tiene opciones sin TACC según la fuente.',
    prof.veg && f?.has_vegetarian_options && 'Tiene opciones vegetarianas según la fuente.',
    prof.vegan && f?.has_vegan_options && 'Tiene opciones veganas según la fuente.',
    p.cuisine.some(c => prof.cuisines.includes(c)) && 'Coincide con tus tipos de comida favoritos.',
  ].filter(Boolean) as string[]
  return (
    <div className="modal" onClick={onClose}>
      <div className="ficha" role="dialog" aria-modal="true" aria-label={`Ficha de ${p.name}`} onClick={e => e.stopPropagation()}>
        <button className="x" onClick={onClose} aria-label="Cerrar">✕</button>
        <h3>{p.name}</h3>
        <p className="m">📍 {[d?.address, d?.neighborhood, d?.city].filter(Boolean).join(', ') || p.zone}</p>
        {err && <p className="m">No pude cargar la ficha completa. Probá de nuevo en un momento.</p>}
        {!d && !err && <p className="m">Cargando…</p>}
        {d && <>
          {d.phone && <p className="m">📞 {d.phone}</p>}
          {d.opening_hours && <p className="m ok">🕒 {d.opening_hours}</p>}
          {d.rating && <p className="m">⭐ {d.rating}{d.price_range ? ` · ${'$'.repeat(d.price_range)}` : ''}</p>}
          <div className="tags">{f?.has_gluten_free_options && <i>Sin TACC</i>}{f?.has_vegetarian_options && <i>Vegetariano</i>}{f?.has_vegan_options && <i>Vegano</i>}{f?.has_lactose_free_options && <i>Sin lactosa</i>}{!(f?.has_gluten_free_options || f?.has_vegetarian_options || f?.has_vegan_options || f?.has_lactose_free_options) && <i>Sin datos</i>}</div>
          <div className="why"><b>¿Por qué te lo recomendamos?</b><br />{porque.length ? porque.join(' ') : 'Coincide con tu búsqueda en esa zona.'}</div>
          {d.advertencia_alimentaria && <div className="warn"><b>⚠ Información alimentaria</b><br />{d.advertencia_alimentaria}</div>}
          <p className="src">Fuente: {d.source?.name || 'sin dato'}{d.source?.reliability ? ` · confiabilidad ${d.source.reliability}` : ''}{(d.source?.last_updated || d.data_date) ? ` · actualizado ${d.source?.last_updated || d.data_date}` : ''}{esWeb(d.source?.url) && <> · <a href={d.source!.url} target="_blank" rel="noreferrer noopener">ver fuente</a></>}</p>
          <div className="acts">
            {d.phone && <a className="btn" href={`tel:${d.phone.replace(/[^\d+]/g, '')}`}>📞 Contactar</a>}
            {esWeb(d.website) && <a className="btn" href={d.website} target="_blank" rel="noreferrer noopener">🌐 Sitio web</a>}
          </div>
        </>}
      </div>
    </div>
  )
}

export default function App() {
  // Si ya iniciaste sesión con Google y el token no venció, se abre el chat directo: no se vuelve a pedir el inicio
  // ni a elegir entre usuario y comercio (el comercio se maneja desde Perfil → Mi comercio). Al cerrar sesión se borra.
  // El invitado sí vuelve a la pantalla de inicio al recargar.
  const sesionRestaurada = sesionVigente() && !!getUser()
  const [auth, setAuth] = useState(sesionRestaurada)
  const [rol, setRol] = useState<Rol | null>(sesionRestaurada ? (getRol() ?? 'usuario') : null)
  const [tab, setTab] = useState<Tab>(tabInicial)
  useEffect(() => { try { sessionStorage.removeItem('foody_tab') } catch { /* sin storage */ } }, [])
  const [q, setQ] = useState('')
  const [applied, setApplied] = useState('')
  // Botón Atrás/Adelante del navegador: la pestaña vuelve a coincidir con la URL.
  useEffect(() => {
    const alVolver = () => {
      const t = RUTA_TAB[window.location.pathname.replace(/\/+$/, '')]
      if (!t) return
      setTab(t)
      if (t !== 'explorar') setApplied('')
    }
    window.addEventListener('popstate', alVolver)
    return () => window.removeEventListener('popstate', alVolver)
  }, [])
  const [prof, setProf] = useLS<Prof>('foody_prof', DEF)
  const [favs, setFavs] = useLS<Place[]>('foody_favs', [])
  const [saved, setSaved] = useLS<Place[]>('foody_saved', [])
  // Sesión restaurada: el perfil guardado en el navegador tiene que ser el de esta cuenta, y el servidor confirma que el
  // token sirve (si fue rechazado, por ejemplo porque se cambió la clave de sesiones, se vuelve al inicio).
  useEffect(() => {
    if (!sesionRestaurada) return
    const u = getUser()
    if (u && prof.email !== u.email) { setProf({ ...DEF, name: u.nombre, email: u.email }); setFavs([]); setSaved([]) }
    fetch(`${API}/api/auth/me`, { headers: authHeaders() })
      .then(r => { if (r.status === 401) { cerrarSesion(); setAuth(false); setRol(null) } })
      .catch(() => { /* sin servidor: se conserva la sesión */ })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  const [provs, setProvs] = useState<string[]>([])
  const [ficha, setFicha] = useState<Place | null>(null)
  useEffect(() => {
    fetch(`${API}/api/provinces`).then(r => r.json()).then(d => setProvs((d.provinces || []).map((p: { name: string }) => p.name))).catch(() => { /* sin servidor */ })
  }, [])
  // Perfil -> backend (PUT sobre el usuario de tu cuenta de Google; el correo no se envía ni se puede cambiar).
  useEffect(() => {
    if (!auth || !/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(prof.email)) return
    const t = setTimeout(async () => {
      const cuerpo = {
        nombre: prof.name.slice(0, 100) || 'Usuario',
        restricciones: [prof.tacc && 'Celíaco (sin TACC)', prof.veg && 'Vegetariano', prof.vegan && 'Vegano'].filter(Boolean),
        preferencias: [...prof.cuisines.slice(0, 15).map(valor => ({ tipo: 'cocina', valor })), { tipo: 'zona', valor: prof.province }],
      }
      try {
        const uid = getUser()?.id_usuario
        if (!uid) return
        await fetch(`${API}/api/usuarios/${uid}`, { method: 'PUT', headers: authHeaders(), body: JSON.stringify(cuerpo) })
      } catch { /* sin servidor */ }
    }, 800)
    return () => clearTimeout(t)
  }, [prof, auth])
  const salir = () => { cerrarSesion(); setAuth(false); setRol(null); window.location.assign('/') }
  if (!auth) return <Login onEnter={u => { if (u && prof.email !== u.email) { setProf({ ...DEF, name: u.nombre, email: u.email }); setFavs([]); setSaved([]) } setRol(getRol() ?? 'usuario'); setAuth(true) }} />
  if (rol === 'comercio') return <PanelComercio onSalir={salir} onUsuario={() => { guardarRol('usuario'); setRol('usuario') }} />
  if (rol === 'admin') return <Admin onVolver={() => { guardarRol('usuario'); setRol('usuario') }} />
  const tog = (l: Place[], set: (v: Place[]) => void, p: Place) => set(l.some(x => x.id === p.id) ? l.filter(x => x.id !== p.id) : [p, ...l])
  const cp: CP = p => ({ p, fav: favs.some(x => x.id === p.id), saved: saved.some(x => x.id === p.id), onFav: () => tog(favs, setFavs, p), onSave: () => tog(saved, setSaved, p), onFicha: () => setFicha(p) })
  const go = (t: Tab) => {
    setTab(t); if (t !== 'explorar') setApplied('')
    try { if (window.location.pathname !== TAB_RUTA[t]) window.history.pushState(null, '', TAB_RUTA[t]) } catch { /* sin history */ }
  }
  return (
    <div className="shell">
      <aside>
        <a className="logo" href="/" aria-label="Volver al inicio de GastronomIA">Gastronom<span className="logo-i">I</span><span className="logo-a">A</span></a>
        {TABS.map(([k, i, l]) => <button key={k} className={tab === k ? 'on' : ''} onClick={() => go(k)}><span>{i}</span>{l}</button>)}
      </aside>
      <main className={tab === 'chat' ? 'chat-mode' : ''}>
        <header>
          <input value={q} placeholder="¿Qué estás buscando hoy?" onChange={e => setQ(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { setApplied(q.trim()); setTab('explorar') } }} />
          <img src={bot} alt="Perfil" onClick={() => go('perfil')} />
        </header>
        <Chat cp={cp} prof={prof} on={tab === 'chat'} />
        {tab === 'premium' && <Premium />}
        {tab === 'explorar' && <Explore cp={cp} prof={prof} provs={provs} q={applied} />}
        {tab === 'lugares' && <Saved list={saved} cp={cp} t="Tus lugares guardados" s="Acá tenés todos los lugares que guardaste para visitar en el futuro." />}
        {tab === 'favoritos' && <Saved list={favs} cp={cp} route t="Tus lugares favoritos" s="Guardá tus lugares preferidos y creá rutas para no perderte ninguna experiencia gastronómica." />}
        {ficha && <Ficha p={ficha} prof={prof} onClose={() => setFicha(null)} />}
        {tab === 'perfil' && <Profile prof={prof} set={setProf} provs={provs} out={salir} cuenta={!!getUser()} tieneComercio={!!getUser()?.comercio} esAdmin={!!getUser()?.admin} onRol={r => { guardarRol(r); setRol(r) }} />}
      </main>
    </div>
  )
}
