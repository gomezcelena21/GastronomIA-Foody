import './Extra.css'

// Pantalla «¿usuario o comercio?». YA NO forma parte del flujo principal: quien inicia sesión entra directo al chat y
// maneja su comercio desde Perfil → Mi comercio. Se conserva por si se quiere volver a ofrecer esa elección.
export default function ElegirRol({ nombre, tieneComercio, esAdmin, onElegir, onSalir }: {
  nombre?: string; tieneComercio: boolean; esAdmin: boolean
  onElegir: (rol: 'usuario' | 'comercio' | 'admin') => void; onSalir: () => void
}) {
  return (
    <div className="ex-wrap" style={{ maxWidth: 560, paddingTop: 70 }}>
      <h2>¡Hola{nombre ? `, ${nombre.split(' ')[0]}` : ''}!</h2>
      <p className="ex-sub">¿Cómo querés usar GastronomIA?</p>
      <div className="ex-card">
        <h3>👤 Soy usuario</h3>
        <p className="ex-note">Quiero que Foody me recomiende dónde comer. Se guarda tu historial.</p>
        <button className="ex-btn" onClick={() => onElegir('usuario')}>Entrar como usuario</button>
      </div>
      <div className="ex-card">
        <h3>🏪 Tengo un comercio o emprendimiento</h3>
        <p className="ex-note">Tengo un local o un emprendimiento online (por ejemplo, pastelería) y quiero que aparezca en Foody.</p>
        <button className="ex-btn" onClick={() => onElegir('comercio')}>{tieneComercio ? 'Ir a mi comercio' : 'Registrar mi comercio'}</button>
      </div>
      {esAdmin && (
        <div className="ex-card">
          <h3>🛠 Administración</h3>
          <p className="ex-note">Revisar y aprobar comercios.</p>
          <button className="ex-btn ex-ghost" onClick={() => onElegir('admin')}>Revisar comercios</button>
        </div>
      )}
      <button className="ex-btn ex-ghost" onClick={onSalir}>Cerrar sesión</button>
    </div>
  )
}
