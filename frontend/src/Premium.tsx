import './Extra.css'

// Pestaña Premium: solo un vistazo. Todavía no existe (no se cobra ni se activa nada).
export default function Premium() {
  return (
    <div className="ex-wrap">
      <div className="ex-row"><h2>Premium</h2><span className="ex-pill ex-prem">Próximamente</span></div>
      <p className="ex-sub">Un vistazo de lo que viene. Por ahora no hay nada que contratar ni pagar.</p>
      <div className="ex-grid">
        <div className="ex-card">
          <h3>Gratis (hoy)</h3>
          <ul className="ex-list">
            <li>Conversar con Foody y recibir recomendaciones reales.</li>
            <li>Explorar lugares, mapa y filtros (sin TACC, vegetariano, vegano).</li>
            <li>Sin registrarte, con un cupo diario de consultas.</li>
            <li>Con tu cuenta de Google: historial de la conversación y perfil con tus restricciones.</li>
          </ul>
        </div>
        <div className="ex-card">
          <h3>Premium (próximamente)</h3>
          <ul className="ex-list">
            <li>Descuentos exclusivos en comercios adheridos.</li>
            <li>Puntos y recompensas por tus visitas.</li>
            <li>Promociones especiales de comercios participantes.</li>
          </ul>
        </div>
      </div>
      <p className="ex-note">Lo esencial de Foody (buscar y recibir recomendaciones) seguirá siendo gratuito: Premium sumará beneficios, no bloqueará la búsqueda.</p>
    </div>
  )
}
