import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'

// Cada pantalla se carga por separado: la página principal no arrastra el CSS del chat y viceversa.
const App = lazy(() => import('./App'))
const Landing = lazy(() => import('./Landing'))
const Legal = lazy(() => import('./Legal'))

// Rutas de la aplicación (cada pestaña tiene su propia URL).
const RUTAS_APP = ['/chat', '/explorar', '/lugares', '/favoritos', '/premium', '/perfil']
const RUTAS_LEGALES: Record<string, 'privacidad' | 'terminos'> = {
  '/privacidad': 'privacidad',
  '/terminos': 'terminos',
}
const ruta = window.location.pathname.replace(/\/+$/, '') || '/'
const enApp = RUTAS_APP.includes(ruta)
const legal = RUTAS_LEGALES[ruta]

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Suspense fallback={null}>
      {legal ? <Legal pagina={legal} /> : enApp ? <App /> : <Landing />}
    </Suspense>
  </StrictMode>,
)
