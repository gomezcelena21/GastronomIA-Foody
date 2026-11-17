import { useEffect } from 'react'
import './Legal.css'

// El correo es público y configurable por Vercel: VITE_CONTACT_EMAIL.
// No es un secreto, así que puede vivir en el frontend.
const CONTACTO = (import.meta.env.VITE_CONTACT_EMAIL as string | undefined)?.trim() || 'contacto@gastronomia.com.ar'

type Pagina = 'privacidad' | 'terminos'

export default function Legal({ pagina }: { pagina: Pagina }) {
  useEffect(() => {
    document.title = pagina === 'privacidad'
      ? 'Política de privacidad · GastronomIA'
      : 'Términos y condiciones · GastronomIA'
    window.scrollTo(0, 0)
  }, [pagina])

  return (
    <div className="legal">
      <header className="legal-nav">
        <a className="legal-logo" href="/" aria-label="Volver al inicio de GastronomIA">
          <span className="legal-marca">Gastronom<span className="legal-i">I</span><span className="legal-a">A</span></span>
        </a>
        <nav aria-label="Legal">
          <a href="/privacidad" className={pagina === 'privacidad' ? 'on' : ''}>Privacidad</a>
          <a href="/terminos" className={pagina === 'terminos' ? 'on' : ''}>Términos</a>
          <a className="legal-volver" href="/">Volver al inicio</a>
        </nav>
      </header>

      <main className="legal-main">
        {pagina === 'privacidad' ? <Privacidad /> : <Terminos />}
        <p className="legal-fecha">Última actualización: noviembre de 2026.</p>
      </main>

      <footer className="legal-pie">
        <a href="/privacidad">Política de privacidad</a>
        <a href="/terminos">Términos y condiciones</a>
        <a href={`mailto:${CONTACTO}`}>{CONTACTO}</a>
      </footer>
    </div>
  )
}

function Privacidad() {
  return (
    <>
      <h1>Política de privacidad</h1>
      <p className="legal-intro">
        GastronomIA es una plataforma para descubrir lugares donde comer en toda la Argentina.
        Foody es su asistente conversacional. Esta política explica qué datos usamos, para qué y
        cómo podés ejercer tus derechos.
      </p>

      <h2>1. Responsable del tratamiento</h2>
      <p>
        El responsable es el equipo de GastronomIA. Para cualquier consulta, pedido o reclamo sobre
        datos personales escribí a <a href={`mailto:${CONTACTO}`}>{CONTACTO}</a>.
      </p>

      <h2>2. Qué datos podemos tratar</h2>
      <ul>
        <li><b>Datos de tu cuenta de Google:</b> nombre, correo electrónico e identificador de la cuenta. No recibimos ni almacenamos tu contraseña.</li>
        <li><b>Preferencias:</b> tipos de comida, zona y restricciones alimentarias que elegís en tu perfil.</li>
        <li><b>Conversaciones:</b> los mensajes que enviás a Foody y las respuestas del asistente, para mantener el contexto y mostrarte tu historial.</li>
        <li><b>Reseñas y comercios:</b> el texto que publicás y los datos que cargás si registrás un comercio.</li>
        <li><b>Datos técnicos:</b> dirección IP, fecha y hora de las consultas y registros de errores, para seguridad y funcionamiento del servicio.</li>
      </ul>
      <p>
        No pedimos ni queremos datos sensibles: no compartas documentos, teléfonos personales,
        tarjetas, contraseñas ni información de salud. El chat detecta y rechaza ese tipo de datos.
      </p>

      <h2>3. Para qué los usamos</h2>
      <ul>
        <li>Prestar el servicio: buscar lugares y responder tus consultas.</li>
        <li>Guardar tu historial y tus preferencias cuando iniciás sesión.</li>
        <li>Moderar reseñas y revisar los comercios que se registran.</li>
        <li>Prevenir abusos, aplicar los límites diarios y mantener la seguridad.</li>
        <li>Mejorar la calidad del servicio a partir de datos agregados y anónimos.</li>
      </ul>

      <h2>4. Base legal</h2>
      <p>
        Tratamos los datos con tu consentimiento (al iniciar sesión y al usar el chat) y para ejecutar
        el servicio que solicitás. Los registros técnicos se usan por interés legítimo en la seguridad
        y el funcionamiento de la plataforma. Podés retirar tu consentimiento en cualquier momento.
      </p>

      <h2>5. Con quién se comparten</h2>
      <p>
        No vendemos datos personales. Para funcionar usamos proveedores tecnológicos que actúan como
        encargados del tratamiento:
      </p>
      <ul>
        <li><b>Google:</b> inicio de sesión con Google y proveedor del modelo de inteligencia artificial que redacta las respuestas de Foody.</li>
        <li><b>Hosting y base de datos:</b> servidores donde se aloja la aplicación y la base PostgreSQL.</li>
        <li><b>Monitoreo de errores:</b> si está configurado, un servicio que recibe reportes técnicos sin datos personales deliberados.</li>
      </ul>
      <p>
        Estos proveedores pueden procesar datos fuera de Argentina. Les exigimos medidas de seguridad
        razonables y un uso limitado a la prestación del servicio.
      </p>

      <h2>6. Cuánto tiempo los guardamos</h2>
      <ul>
        <li>La cuenta y el perfil: mientras la cuenta esté activa o hasta que pidas su eliminación.</li>
        <li>Las conversaciones: mientras la conversación esté activa y, luego, por un período limitado para el historial.</li>
        <li>Los cupos diarios: se reinician cada día; los registros antiguos se eliminan periódicamente.</li>
        <li>Los registros técnicos y de errores: el tiempo necesario para diagnosticar incidentes.</li>
      </ul>

      <h2>7. Tus derechos</h2>
      <p>
        Podés pedir acceso, rectificación, actualización, supresión y portabilidad de tus datos, y
        oponerte a determinados tratamientos. Escribinos a <a href={`mailto:${CONTACTO}`}>{CONTACTO}</a>
        {' '}indicando el correo con el que iniciaste sesión. También podés presentar un reclamo ante la
        autoridad de protección de datos de tu país.
      </p>

      <h2>8. Seguridad</h2>
      <p>
        Usamos conexiones cifradas (HTTPS), tokens de sesión firmados, límites de uso y acceso
        restringido a la base de datos. Ningún sistema es infalible: si detectamos un incidente que
        afecte tus datos, te lo informaremos por los medios disponibles.
      </p>

      <h2>9. Cookies y almacenamiento del navegador</h2>
      <p>
        No usamos cookies publicitarias. Guardamos en el almacenamiento de la sesión del navegador el
        token de sesión, tus preferencias y la pestaña abierta. Se borran al cerrar la sesión o el
        navegador, según el caso. El inicio de sesión con Google puede usar sus propias cookies.
      </p>

      <h2>10. Menores de edad</h2>
      <p>
        El servicio no está dirigido a menores de 13 años. Si sos menor, usalo con la autorización de
        tu madre, padre o tutor.
      </p>

      <h2>11. Cambios</h2>
      <p>
        Podemos actualizar esta política para reflejar cambios del servicio o de la normativa. La
        versión vigente es la publicada en esta página.
      </p>
    </>
  )
}

function Terminos() {
  return (
    <>
      <h1>Términos y condiciones</h1>
      <p className="legal-intro">
        Al usar GastronomIA aceptás estos términos. Si no estás de acuerdo, no uses el servicio.
        GastronomIA es un proyecto en desarrollo y parte de su contenido es académico.
      </p>

      <h2>1. Qué es GastronomIA</h2>
      <p>
        GastronomIA reúne información de establecimientos gastronómicos de toda la Argentina y ofrece un
        asistente, Foody, que ayuda a buscar lugares según zona, tipo de comida y restricciones
        alimentarias. La búsqueda básica es gratuita. Algunas funciones pueden requerir una cuenta de
        Google y tienen límites diarios de uso.
      </p>

      <h2>2. Información de los establecimientos</h2>
      <p>
        Los datos provienen de fuentes abiertas (OpenStreetMap, BA Data y otras) y de comercios que se
        registran. Pueden estar desactualizados o incompletos. Verificá siempre horarios, dirección,
        precios y opciones alimentarias directamente con el local.
      </p>
      <p>
        <b>Seguridad alimentaria:</b> que un lugar figure con opciones sin TACC, vegetarianas o veganas
        no constituye una garantía de ausencia de contaminación cruzada ni una certificación. Foody
        puede no tener el dato confirmado. Si tenés celiaquía o una alergia, confirmá con el
        establecimiento antes de consumir.
      </p>

      <h2>3. Uso responsable</h2>
      <ul>
        <li>No uses el servicio para actividades ilegales, para acosar a otras personas ni para enviar contenido malicioso.</li>
        <li>No intentes vulnerar la seguridad, automatizar consultas masivas ni eludir los límites de uso.</li>
        <li>No publiques datos personales de terceros ni información falsa sobre un comercio.</li>
        <li>No presentes las respuestas de Foody como asesoramiento médico o nutricional.</li>
      </ul>

      <h2>4. Cuentas y sesiones</h2>
      <p>
        Podés usar el chat como invitado o iniciar sesión con Google. Con cuenta se guarda tu historial
        y tus preferencias. Sos responsable de la actividad realizada con tu cuenta y de mantener el
        acceso a tu correo seguro.
      </p>

      <h2>5. Comercios y emprendimientos</h2>
      <p>
        Si registrás un comercio, declarás que sos responsable de la información y que tenés al menos
        seis meses de actividad. Los datos quedan pendientes de revisión. Podemos rechazar, suspender o
        dar de baja un comercio si la información es falsa, si no podemos verificarla o si incumple
        estos términos. La publicación no implica una recomendación ni una certificación alimentaria.
      </p>

      <h2>6. Reseñas</h2>
      <p>
        Las reseñas deben basarse en experiencias reales y respetuosas. Podemos moderar, ocultar o
        eliminar contenido ofensivo, discriminatorio, spam o que revele datos personales.
      </p>

      <h2>7. Propiedad intelectual y licencias</h2>
      <p>
        La marca, el diseño y el código de GastronomIA pertenecen a sus autores. Los datos de
        OpenStreetMap se usan bajo la licencia ODbL y requieren atribución a © OpenStreetMap
        contributors. Los datos de BA Data se usan bajo la licencia CC-BY-2.5-AR. Los lugares de Overture Maps se usan bajo la
        licencia CDLA-Permissive-2.0 y requieren atribución a Overture Maps Foundation. Las imágenes y marcas
        de terceros pertenecen a sus titulares.
      </p>

      <h2>8. Disponibilidad y límites</h2>
      <p>
        El servicio se ofrece “tal como está” y puede interrumpirse por mantenimiento, fallas técnicas
        o límites de los proveedores. No garantizamos disponibilidad ininterrumpida ni que las
        respuestas estén libres de errores. Podemos cambiar o discontinuar funciones sin aviso previo.
      </p>

      <h2>9. Responsabilidad</h2>
      <p>
        En la medida permitida por la ley, no somos responsables por daños derivados del uso de la
        información, de decisiones tomadas a partir de las respuestas de Foody ni de la conducta de los
        establecimientos. Nada de esto limita los derechos que la ley reconoce a las personas
        consumidoras.
      </p>

      <h2>10. Baja y eliminación</h2>
      <p>
        Podés dejar de usar el servicio en cualquier momento. Para pedir la eliminación de tu cuenta y
        tus datos, escribí a <a href={`mailto:${CONTACTO}`}>{CONTACTO}</a> desde el correo con el que
        iniciaste sesión.
      </p>

      <h2>11. Ley aplicable</h2>
      <p>
        Estos términos se rigen por las leyes de la República Argentina. Cualquier controversia se
        someterá a los tribunales competentes de la Ciudad Autónoma de Buenos Aires, sin perjuicio de
        los derechos del consumidor.
      </p>

      <h2>12. Contacto</h2>
      <p>
        Por consultas sobre estos términos escribí a <a href={`mailto:${CONTACTO}`}>{CONTACTO}</a>.
      </p>
    </>
  )
}
