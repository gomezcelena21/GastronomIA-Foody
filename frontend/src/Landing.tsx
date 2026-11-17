import { useRef, useState } from 'react'
import './Landing.css'
import foody from './assets/foody-recorte.webp'

// Página de inicio de GastronomIA (la plataforma). Foody es su asistente: aparece como personaje, nunca como marca.
const ORDEN = ['b', 'r', 'y', 'b', 'g', 'r']   // colores en el orden del logo de Google
const Colores = ({ texto }: { texto: string }) => (
  <>{texto.split('').map((c, i) => <span key={i} className={'lp-c-' + ORDEN[i % ORDEN.length]}>{c}</span>)}</>
)

export default function Landing() {
  const [q, setQ] = useState('')
  const entrada = useRef<HTMLInputElement>(null)

  // Cada sección de la app tiene su propia URL; si hay búsqueda, queda escrita para Foody.
  const RUTAS: Record<string, string> = { chat: '/chat', explorar: '/explorar', lugares: '/lugares', favoritos: '/favoritos', premium: '/premium', perfil: '/perfil' }
  const ir = (pestana: string, consulta?: string) => {
    try {
      sessionStorage.setItem('foody_tab', pestana)
      if (consulta) sessionStorage.setItem('foody_q', consulta)
    } catch { /* sin storage */ }
    window.location.assign(RUTAS[pestana] || '/chat')
  }

  return (
    <div className="lp" id="inicio">
      <header className="lp-nav">
        <a className="lp-logo" href="#inicio" aria-label="GastronomIA, inicio">
          <svg viewBox="0 0 64 64" width="46" height="46" fill="none" stroke="#1a2238" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M17 44V37C10 36 6 31 7 25C8 19 14 17 19 19C20 12 27 9 33 11C38 8 46 10 47 17C54 16 58 22 56 28C55 33 51 36 47 37V44Z" /><path d="M17 44H47V52Q47 55 44 55H20Q17 55 17 52Z" /><path d="M26 44V52M38 44V52" /></svg>
          <span className="lp-marca">Gastronom<span className="lp-c-b">I</span><span className="lp-c-r">A</span></span>
        </a>
        <nav className="lp-links" aria-label="Secciones">
          <a href="#que-es">Qué es</a>
          <a href="#como">Cómo funciona</a>
          <a href="#comercios">Para comercios</a>
          <a href="#privacidad">Tus datos</a>
        </nav>
        <div className="lp-acciones">
          <a className="lp-nav-cta" href="/chat" target="_blank" rel="noopener">Hablar con Foody</a>
        </div>
      </header>

      <section className="lp-hero">
        <span className="lp-deco lp-deco-az" aria-hidden="true" />
        <span className="lp-deco lp-deco-ro" aria-hidden="true" />
        <div className="lp-texto">
          <h1>Descubrí, disfrutá y viví la gastronomía con <span className="lp-wm"><Colores texto="GastronomIA" /></span></h1>
          <p>Encontrá los mejores lugares, recibí recomendaciones personalizadas y disfrutá experiencias únicas, con opciones sin TACC, vegetarianas y veganas.</p>
          <form className="lp-buscador" onSubmit={e => { e.preventDefault(); ir('chat', q.trim()) }}>
            <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="#7a8aa6" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="M15.5 15.5 21 21" /></svg>
            <input ref={entrada} value={q} onChange={e => setQ(e.target.value)} placeholder="¿Qué estás buscando hoy?" maxLength={200} aria-label="¿Qué estás buscando hoy?" />
            <button type="submit" aria-label="Buscar con Foody"><svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg></button>
          </form>
        </div>
        <div className="lp-visual">
          <span className="lp-disco" aria-hidden="true" />
          <span className="lp-mancha" aria-hidden="true" />
          <img className="lp-foody" src={foody} alt="Foody, el asistente de GastronomIA" />
          <span className="lp-chis lp-chis-1" aria-hidden="true" /><span className="lp-chis lp-chis-2" aria-hidden="true" /><span className="lp-chis lp-chis-3" aria-hidden="true" />
          <span className="lp-chis lp-chis-4" aria-hidden="true" /><span className="lp-chis lp-chis-5" aria-hidden="true" /><span className="lp-chis lp-chis-6" aria-hidden="true" />
          <div className="lp-globo">Hola, soy <b>Foody</b>, tu asistente de GastronomIA <svg viewBox="0 0 24 24" width="18" height="18" fill="#EA4335" aria-hidden="true"><path d="M12 21s-8.5-5.2-8.5-11.2C3.5 6.600 6 4.500 8.700 4.500c1.500 0 2.800.8 3.300 2 .5-1.200 1.800-2 3.300-2 2.700 0 5.200 2.100 5.200 5.300C20.500 15.800 12 21 12 21Z" /></svg></div>
        </div>
      </section>

      <section className="lp-stats" aria-label="Estadísticas y cobertura">
        <div className="lp-hacer-t">
          <h2>Estadísticas y cobertura</h2>
          <span className="lp-subraya" aria-hidden="true"><i /><i /><i /></span>
          <p>Los datos de la base actual de GastronomIA.</p>
        </div>
        <article className="lp-tarjeta"><h3>71.343</h3><p>Lugares en la base</p></article>
        <article className="lp-tarjeta"><h3>Todo el país</h3><p>Cobertura geográfica: las 23 provincias y la Ciudad de Buenos Aires.</p></article>
        <article className="lp-tarjeta"><h3>3</h3><p>Restricciones: sin TACC, vegetariano y vegano.</p></article>
        <article className="lp-tarjeta"><h3>3</h3><p>Fuentes abiertas: OpenStreetMap, BA Data y Overture Maps.</p></article>
      </section>

      <section className="lp-hacer" id="que-es">
        <div className="lp-hacer-t">
          <h2>¿Qué es GastronomIA?</h2>
          <span className="lp-subraya" aria-hidden="true"><i /><i /><i /></span>
          <p>Una plataforma que integra un asistente conversacional para ayudarte a elegir dónde comer según tus necesidades.</p>
        </div>
        <article className="lp-tarjeta">
          <h3>Datos reales, no inventados</h3>
          <p>Las recomendaciones se basan en una base de establecimientos y fuentes de información.</p>
        </article>
        <article className="lp-tarjeta">
          <h3>Pensado para restricciones</h3>
          <p>Contempla tres categorías: sin TACC, vegetariano y vegano.</p>
        </article>
        <article className="lp-tarjeta">
          <h3>Transparente y prudente</h3>
          <p>Informa de dónde provienen los datos y advierte que deben confirmarse con los establecimientos.</p>
        </article>
      </section>

      <section className="lp-hacer" id="sobre">
        <div className="lp-hacer-t">
          <h2>¿Qué podés hacer?</h2>
          <span className="lp-subraya" aria-hidden="true"><i /><i /><i /></span>
          <p>Con GastronomIA y Foody, encontrá justo lo que buscás.</p>
          <a className="lp-btn lp-btn-r" href="/explorar" onClick={e => { e.preventDefault(); ir('explorar') }}>Descubrí más <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg></a>
        </div>
        <article className="lp-tarjeta">
          <svg viewBox="0 0 48 48" width="54" height="54" fill="none" stroke="#4285F4" strokeWidth="5" strokeLinecap="round" aria-hidden="true"><circle cx="20" cy="20" r="13" /><path d="M30 30 42 42" /></svg>
          <h3>Encontrá lugares</h3>
          <p>Explorá restaurantes, cafeterías y mucho más.</p>
        </article>
        <article className="lp-tarjeta">
          <svg viewBox="0 0 48 48" width="54" height="54" aria-hidden="true"><path d="M24 4.500 29.600 16.800 43 18.400 33 27.600 35.700 41 24 34.200 12.300 41 15 27.600 5 18.400 18.400 16.800Z" fill="#FBBC05" stroke="#FBBC05" strokeWidth="4" strokeLinejoin="round" /></svg>
          <h3>Guardá tus favoritos</h3>
          <p>Armá tu lista de lugares preferidos.</p>
        </article>
        <article className="lp-tarjeta">
          <svg viewBox="0 0 24 34" width="40" height="54" aria-hidden="true"><defs><clipPath id="lp-pin"><path d="M12 0C5.400 0 0 5.400 0 12c0 9 12 22 12 22s12-13 12-22C24 5.400 18.600 0 12 0Z" /></clipPath></defs><g clipPath="url(#lp-pin)"><rect width="24" height="34" fill="#EA4335" /><rect x="12" width="12" height="14" fill="#4285F4" /><path d="M0 14H12V34H9Z" fill="#FBBC05" /><path d="M12 14H24V24L12 34Z" fill="#34A853" /></g><circle cx="12" cy="12" r="4.400" fill="#fff" /></svg>
          <h3>Recibí recomendaciones</h3>
          <p>Personalizadas según tus gustos.</p>
        </article>
      </section>

      <section className="lp-fila">
        <div className="lp-como" id="como">
          <h2>¿Cómo funciona?</h2>
          <p className="lp-facil">Es muy fácil, en solo 3 pasos:</p>
          <div className="lp-pasos">
            <div className="lp-paso">
              <div className="lp-pi"><span className="lp-num lp-num-b">1</span><svg viewBox="0 0 48 48" width="40" height="40" fill="none" stroke="#4285F4" strokeWidth="5" strokeLinecap="round" aria-hidden="true"><circle cx="20" cy="20" r="13" /><path d="M30 30 42 42" /></svg></div>
              <b>Buscá</b><span>qué querés comer</span>
            </div>
            <svg className="lp-flecha" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#9aa6bd" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 12h15M14 7l5 5-5 5" /></svg>
            <div className="lp-paso">
              <div className="lp-pi"><span className="lp-num lp-num-r">2</span><svg viewBox="0 0 48 48" width="40" height="40" aria-hidden="true"><path d="M24 4.500 29.600 16.800 43 18.400 33 27.600 35.700 41 24 34.200 12.300 41 15 27.600 5 18.400 18.400 16.800Z" fill="#FBBC05" stroke="#FBBC05" strokeWidth="4" strokeLinejoin="round" /></svg></div>
              <b>Recibí</b><span>recomendaciones</span>
            </div>
            <svg className="lp-flecha" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#9aa6bd" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 12h15M14 7l5 5-5 5" /></svg>
            <div className="lp-paso">
              <div className="lp-pi"><span className="lp-num lp-num-g">3</span><svg viewBox="0 0 24 24" width="40" height="40" fill="#EA4335" aria-hidden="true"><path d="M12 21s-8.500-5.200-8.500-11.200C3.500 6.600 6 4.500 8.700 4.500c1.500 0 2.800.8 3.300 2 .5-1.200 1.800-2 3.300-2 2.700 0 5.200 2.100 5.200 5.300C20.500 15.800 12 21 12 21Z" /></svg></div>
              <b>Guardá</b><span>tus favoritos</span>
            </div>
          </div>
        </div>

        <div className="lp-comercios" id="comercios">
          <div className="lp-com-t">
            <span className="lp-com-ico"><svg viewBox="0 0 120 110" width="40" height="37" aria-hidden="true"><rect x="14" y="44" width="92" height="58" rx="6" fill="#fff" stroke="#1a2238" strokeWidth="3.6" /><path d="M8 44 18 16H102L112 44Z" fill="#fff" /><path d="M18 16H28.5L21 44H8Z" fill="#4285F4" /><path d="M39 16H49.5L47 44H34Z" fill="#EA4335" /><path d="M60 16H70.5L73 44H60Z" fill="#FBBC05" /><path d="M81 16H91.5L99 44H86Z" fill="#34A853" /><path d="M8 44 18 16H102L112 44Z" fill="none" stroke="#1a2238" strokeWidth="3.6" strokeLinejoin="round" /><rect x="26" y="60" width="30" height="42" rx="3" fill="#E8F0FE" stroke="#1a2238" strokeWidth="3" /><rect x="66" y="60" width="28" height="22" rx="3" fill="#E8F0FE" stroke="#1a2238" strokeWidth="3" /></svg></span>
            <h2>Para comercios y emprendimientos</h2>
            <p>Sumate a GastronomIA y hacé que más personas te encuentren. Ingresá con Google, completá los datos de tu comercio, indicá qué ofrecés y en qué zona trabajás, y esperá la revisión para que Foody pueda recomendarte. También podés sumarte si vendés solo por Internet.</p>
            <a className="lp-btn lp-btn-a" href="/perfil" onClick={e => { e.preventDefault(); ir('perfil') }}>Quiero sumarme <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg></a>
          </div>
          <div className="lp-com-v">
                        <img className="lp-foody-s" src={foody} alt="" />
            <span className="lp-chis lp-chis-7" aria-hidden="true" /><span className="lp-chis lp-chis-8" aria-hidden="true" />
          </div>
        </div>
      </section>

      <section className="lp-hacer" id="premium">
        <div className="lp-hacer-t">
          <h2>Servicios para usuarios y comercios</h2>
          <span className="lp-subraya" aria-hidden="true"><i /><i /><i /></span>
          <p>La búsqueda con Foody es gratuita. Los planes Premium son opcionales y llegarán próximamente.</p>
        </div>
        <article className="lp-tarjeta">
          <h3>Foody gratis</h3>
          <p>Buscá y recibí recomendaciones sin costo, sin registrarte o con tu cuenta de Google.</p>
        </article>
        <article className="lp-tarjeta">
          <h3>Premium personas</h3>
          <p>Próximamente: descuentos, puntos y promociones en comercios adheridos.</p>
        </article>
        <article className="lp-tarjeta">
          <h3>Premium comercios</h3>
          <p>Próximamente: mayor visibilidad, comercios destacados, promociones y estadísticas.</p>
        </article>
      </section>

      <section className="lp-priv" id="privacidad">
        <div className="lp-como">
          <h2>Datos personales y privacidad</h2>
          <span className="lp-subraya" aria-hidden="true"><i /><i /><i /></span>
          <p className="lp-facil">Así cuidamos tus datos y tu experiencia.</p>
          <div className="lp-priv-lista">
            <div><b>Uso sin registro</b><span>Disponible</span></div>
            <div><b>Inicio de sesión</b><span>Mediante Google</span></div>
            <div><b>Historial</b><span>Se guarda al iniciar sesión</span></div>
            <div><b>Contraseñas</b><span>No se almacenan</span></div>
            <div><b>Consultas</b><span>Tienen límites diarios</span></div>
            <div><b>Datos personales</b><span>No se aceptan</span></div>
            <div><b>Temática</b><span>Solo consultas gastronómicas</span></div>
            <div><b>Datos sensibles</b><span>No compartas teléfonos, correos, documentos ni tarjetas</span></div>
          </div>
          <p className="lp-legal-link">
            Leé la <a href="/privacidad">política de privacidad completa</a> y los <a href="/terminos">términos y condiciones</a>.
          </p>
        </div>
      </section>

      <section className="lp-hacer" id="fuentes">
        <div className="lp-hacer-t">
          <h2>Fuentes de información y limitaciones</h2>
          <span className="lp-subraya" aria-hidden="true"><i /><i /><i /></span>
          <p>Los establecimientos provienen de fuentes abiertas y los datos pueden cambiar.</p>
        </div>
        <article className="lp-tarjeta">
          <h3>OpenStreetMap</h3>
          <p>5.431 registros de establecimientos. © OpenStreetMap contributors, licencia ODbL.</p>
        </article>
        <article className="lp-tarjeta">
          <h3>Overture Maps</h3>
          <p>62.880 lugares de comida y bebida. Datos de Overture Maps Foundation, licencia CDLA-Permissive-2.0. Sin verificar con el local.</p>
        </article>
        <article className="lp-tarjeta">
          <h3>BA Data</h3>
          <p>2.721 registros del Portal de Datos Abiertos de la Ciudad de Buenos Aires. Licencia CC-BY-2.5-AR.</p>
        </article>
        <article className="lp-tarjeta">
          <h3>Limitaciones</h3>
          <p>Los datos pueden estar desactualizados. Confirmá horarios y opciones alimentarias con el local. Cobertura de todo el país (solo Argentina). Prototipo académico en desarrollo.</p>
        </article>
      </section>

      <section className="lp-cierre" id="cierre">
        <div className="lp-comercios">
          <div className="lp-com-t">
            <h2>¿Listo para elegir mejor?</h2>
            <p>Contale a Foody qué buscás y recibí lugares reales, con su fuente y acceso a Google Maps. Confirmá siempre la información con el establecimiento.</p>
            <a className="lp-btn lp-btn-a" href="/chat" target="_blank" rel="noopener">
              Hablar con Foody
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
            </a>
          </div>
          <div className="lp-com-v">
            <img className="lp-foody-s" src={foody} alt="" />
          </div>
        </div>
      </section>

      <footer className="lp-pie">
        <svg className="lp-ola" viewBox="0 0 1200 120" preserveAspectRatio="none" aria-hidden="true"><path d="M0 76C150 24 310 34 450 74C540 100 620 112 720 120L0 120Z" fill="#4285F4" opacity=".18" /><path d="M250 120C320 88 430 80 560 96C690 112 810 70 950 78C1010 82 1050 100 1075 120Z" fill="#FBBC05" opacity=".88" /><path d="M830 120C890 72 1010 42 1200 62L1200 120Z" fill="#34A853" opacity=".92" /></svg>
        <div className="lp-pie-in">
          <a className="lp-logo lp-logo-s" href="#inicio" aria-label="GastronomIA, inicio">
            <svg viewBox="0 0 64 64" width="40" height="40" fill="none" stroke="#1a2238" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M17 44V37C10 36 6 31 7 25C8 19 14 17 19 19C20 12 27 9 33 11C38 8 46 10 47 17C54 16 58 22 56 28C55 33 51 36 47 37V44Z" /><path d="M17 44H47V52Q47 55 44 55H20Q17 55 17 52Z" /><path d="M26 44V52M38 44V52" /></svg>
            <span className="lp-marca">Gastronom<span className="lp-c-b">I</span><span className="lp-c-r">A</span></span>
          </a>
          <span className="lp-raya" aria-hidden="true" />
          <p>Una plataforma para descubrir, disfrutar y compartir la gastronomía.</p>
          <div className="lp-redes" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="#1a2238" strokeWidth="2.200"><rect x="3" y="3" width="18" height="18" rx="5" /><circle cx="12" cy="12" r="4.200" /><circle cx="17.300" cy="6.700" r="1" fill="#1a2238" stroke="none" /></svg>
            <svg viewBox="0 0 24 24" width="32" height="32"><rect x="2" y="5" width="20" height="14" rx="4.500" fill="#1a2238" /><path d="M10 9v6l5.200-3Z" fill="#fff" /></svg>
            <svg viewBox="0 0 24 24" width="28" height="28" fill="#1a2238"><path d="M12 2C8.100 2 5 5.100 5 9c0 5.200 7 13 7 13s7-7.800 7-13c0-3.900-3.100-7-7-7Zm0 9.500A2.500 2.500 0 1 1 12 6.500a2.500 2.500 0 0 1 0 5Z" /></svg>
          </div>
          <span className="lp-provecho">¡Buen provecho! <svg viewBox="0 0 24 24" width="18" height="18" fill="#EA4335" aria-hidden="true"><path d="M12 21s-8.500-5.200-8.500-11.200C3.500 6.600 6 4.500 8.700 4.500c1.500 0 2.800.8 3.300 2 .5-1.200 1.800-2 3.300-2 2.700 0 5.200 2.100 5.200 5.300C20.500 15.800 12 21 12 21Z" /></svg></span>
          <nav className="lp-legal" aria-label="Información legal">
            <a href="/privacidad">Política de privacidad</a>
            <a href="/terminos">Términos y condiciones</a>
            <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer noopener">© OpenStreetMap</a>
            <a href="https://overturemaps.org" target="_blank" rel="noreferrer noopener">Overture Maps Foundation</a>
          </nav>
        </div>
      </footer>
    </div>
  )
}
