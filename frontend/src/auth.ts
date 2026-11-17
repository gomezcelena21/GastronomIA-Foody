// Sesión del usuario (login con Google). El token lo emite el backend (/api/auth/google) y vence solo.
export const API: string = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001'
export const GOOGLE_CLIENT_ID: string = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

const KT = 'foody_token'
const KU = 'foody_user'
const KI = 'foody_invitado'
const KR = 'foody_rol'

export interface Sesion { nombre: string; email: string; id_usuario?: number; comercio?: boolean; admin?: boolean }

// La sesión con Google se guarda en el navegador (localStorage) hasta que vence el token (12 h) o hasta que se cierra
// la sesión: así, quien ya inició sesión entra directo al chat sin repetir el inicio ni elegir de nuevo. El token no
// contiene contraseñas y el backend lo vuelve a verificar en cada pedido. El invitado y el rol de la pestaña siguen
// en sessionStorage (se pierden al cerrar la pestaña).
export const getToken = (): string | null => { try { return localStorage.getItem(KT) } catch { return null } }

export const getUser = (): Sesion | null => {
  try { const u = localStorage.getItem(KU); return u ? (JSON.parse(u) as Sesion) : null } catch { return null }
}

export const guardarSesion = (token: string, u: Sesion) => {
  try { sessionStorage.removeItem(KR); localStorage.setItem(KT, token); localStorage.setItem(KU, JSON.stringify(u)) } catch { /* sin storage */ }
}

export const cerrarSesion = () => {
  try {
    // también se borran las claves de versiones anteriores, que guardaban la sesión en sessionStorage
    ;[KT, KU].forEach(k => { localStorage.removeItem(k); sessionStorage.removeItem(k) })
    ;[KI, KR].forEach(k => sessionStorage.removeItem(k))
  } catch { /* sin storage */ }
}

// Usuario gratuito: puede usar Foody sin registrarse (con un cupo diario menor).
export const entrarComoInvitado = () => { try { sessionStorage.setItem(KI, '1') } catch { /* sin storage */ } }
export const esInvitado = (): boolean => { try { return sessionStorage.getItem(KI) === '1' } catch { return false } }

// Rol elegido después de iniciar sesión: usuario, comercio o administración.
export type Rol = 'usuario' | 'comercio' | 'admin'
export const getRol = (): Rol | null => {
  try { const r = sessionStorage.getItem(KR); return r === 'usuario' || r === 'comercio' || r === 'admin' ? r : null } catch { return null }
}
export const guardarRol = (r: Rol | null) => {
  try { if (r) sessionStorage.setItem(KR, r); else sessionStorage.removeItem(KR) } catch { /* sin storage */ }
}

// ¿Hay un token guardado que todavía no venció? (el backend lo vuelve a verificar en cada pedido)
export const sesionVigente = (): boolean => {
  const t = getToken()
  if (!t) return false
  try {
    const p = JSON.parse(atob(t.split('.')[0].replace(/-/g, '+').replace(/_/g, '/')))
    return typeof p.exp === 'number' && p.exp * 1000 > Date.now()
  } catch { return false }
}

export const authHeaders = (): Record<string, string> => {
  const t = getToken()
  return t ? { 'Content-Type': 'application/json', Authorization: `Bearer ${t}` } : { 'Content-Type': 'application/json' }
}
