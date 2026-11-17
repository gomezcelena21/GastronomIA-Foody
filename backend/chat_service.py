"""
Gastro IA - Chat Service
Orchestrates conversation, tool execution, and recommendations.
"""

import json
import logging
import math
import os
import threading
from typing import Dict, List, Optional, Callable
from sqlalchemy.orm import Session
from sqlalchemy import text
from google.genai import types

import cuota
import diseno
import persistencia
from database import engine
from gemini_service import GeminiService, historial_desde_texto
from recommendation import RecommendationEngine

log = logging.getLogger("gastronomia")
MAX_SESIONES = 200
ERROR_GENERICO = {"error": "No pude consultar la base de datos en este momento."}

# ---------------------------------------------------------------------------
# Estado compartido entre pedidos.
#
# Antes el ChatService era UNO solo para todo el servidor y main.py lo protegía
# con un threading.Lock() global: mientras un usuario esperaba a Gemini, todos
# los demás esperaban. Ahora cada pedido tiene su propio ChatService (con su
# sesión de base de datos y su last_restaurants) y solo se serializa por
# session_id, que es lo único que realmente no se puede compartir.
# ---------------------------------------------------------------------------
_SESIONES: Dict[str, object] = {}          # session_id -> chat de Gemini
_LOCKS_SESION: Dict[str, threading.Lock] = {}
_SESIONES_LOCK = threading.Lock()

# Historial persistente (sobrevive reinicios y lo comparten los workers).
# Si la base no está disponible, devuelve [] y todo funciona como antes.
_SESIONES_BD = persistencia.AlmacenSesiones(engine)

_CUOTA = None                              # ControlCuota único para TODO el backend
_CUOTA_LOCK = threading.Lock()


def _control_cuota() -> cuota.ControlCuota:
    """La cuota de Gemini es global: si se reiniciara por pedido no limitaría nada."""
    global _CUOTA
    if _CUOTA is None:
        with _CUOTA_LOCK:
            if _CUOTA is None:
                _CUOTA = cuota.ControlCuota(
                    rpm=int(os.getenv("GEMINI_RPM", "10") or 10),
                    max_espera=float(os.getenv("GEMINI_MAX_ESPERA", "20") or 20),
                )
    return _CUOTA


def reiniciar_estado_compartido() -> None:
    """Limpia sesiones y cuota. Pensado para pruebas y para reiniciar el servicio."""
    global _CUOTA
    with _SESIONES_LOCK:
        _SESIONES.clear()
        _LOCKS_SESION.clear()
    with _CUOTA_LOCK:
        _CUOTA = None


def _es_timeout(error: Exception) -> bool:
    texto = str(error).lower()
    return any(x in texto for x in ("timeout", "timed out", "deadline", "504", "no respondió", "no respondio"))


class ChatService:
    """Main chat service that handles user interactions."""

    def __init__(self, db: Session, gemini_api_key: str = None):
        self.db = db
        self.gemini = GeminiService(gemini_api_key)
        self.last_restaurants: list = []
        self.cuota = _control_cuota()

    # ------------------------------------------------------------- sesiones

    def _lock_sesion(self, session_id: str) -> threading.Lock:
        with _SESIONES_LOCK:
            lock = _LOCKS_SESION.get(session_id)
            if lock is None:
                lock = threading.Lock()
                _LOCKS_SESION[session_id] = lock
            return lock

    def _obtener_chat(self, session_id: str):
        """Chat de Gemini de ESTA sesión. El modelo se comparte; el historial no.

        Si la sesión no está en memoria (primer pedido, reinicio o segundo worker),
        se reconstruye desde PostgreSQL con los turnos guardados.
        """
        if self.gemini.model is None:
            return None
        with _SESIONES_LOCK:
            chat = _SESIONES.get(session_id)
            if chat is None:
                if len(_SESIONES) >= MAX_SESIONES:
                    viejo = next(iter(_SESIONES))
                    _SESIONES.pop(viejo, None)
                    _LOCKS_SESION.pop(viejo, None)
                turnos = _SESIONES_BD.cargar(session_id)
                chat = self.gemini.model.start_chat(history=historial_desde_texto(turnos))
                _SESIONES[session_id] = chat
            return chat

    def _guardar_turno(self, session_id: str, mensaje: str, respuesta: str) -> None:
        """Guarda el turno para poder retomar la conversación después."""
        if not respuesta:
            return
        turnos = _SESIONES_BD.cargar(session_id)
        turnos.extend([
            {"role": "user", "text": mensaje[:4000]},
            {"role": "model", "text": respuesta[:4000]},
        ])
        _SESIONES_BD.guardar(session_id, turnos)

    def _descartar_chat(self, session_id: str) -> None:
        """Olvida el historial de una sesión cuyo pedido quedó colgado.

        El hilo que quedó esperando a Gemini puede seguir vivo (es daemon), pero
        ya nadie más va a usar ese chat: el próximo mensaje crea uno nuevo.
        """
        with _SESIONES_LOCK:
            _SESIONES.pop(session_id, None)

    def reset_session(self, session_id: str = "default"):
        """Reset a chat session."""
        with self._lock_sesion(session_id):
            with _SESIONES_LOCK:
                _SESIONES.pop(session_id, None)
                _LOCKS_SESION.pop(session_id, None)
            _SESIONES_BD.borrar(session_id)

    # ------------------------------------------------------------- Gemini

    def _enviar(self, chat, contenido):
        """Un pedido a Gemini respetando la cuota y con timeout propio.

        Sin timeout, una llamada colgada podía dejar el pedido abierto más de
        90 segundos. Ahora, si Gemini no contesta a tiempo, se responde con la
        base de datos (modo sin IA).

        El timeout del SDK no alcanza: ante una clave inválida el SDK puede
        reintentar durante minutos. Por eso el pedido completo corre en un hilo
        daemon con un límite de tiempo duro (espera de cuota + respuesta).
        """
        timeout = float(os.getenv("GEMINI_TIMEOUT", "12") or 12)
        espera_cuota = float(os.getenv("GEMINI_MAX_ESPERA", "20") or 20)
        limite = timeout + espera_cuota + 3.0
        resultado: dict = {}
        error: dict = {}

        def _llamada():
            try:
                resultado["valor"] = cuota.enviar_con_cuota(
                    self.cuota,
                    lambda: chat.send_message(contenido),
                    log.warning,
                )
            except BaseException as exc:  # se re-lanza en el hilo principal
                error["valor"] = exc

        hilo = threading.Thread(target=_llamada, name="gemini-pedido", daemon=True)
        hilo.start()
        hilo.join(limite)
        if hilo.is_alive():
            raise TimeoutError("Gemini no respondió en %.0f segundos" % limite)
        if error:
            raise error["valor"]
        return resultado.get("valor")

    def _sin_ia(self, message: str, diaria: bool, session_id: Optional[str] = None) -> str:
        """Respuesta cuando Gemini no tiene cuota: búsqueda por reglas directo en la base.

        Con `session_id` recuerda lo que se venía hablando (para entender «¿y sin TACC?») y
        guarda el turno. Si la base de conversaciones falla, igual responde."""
        aviso = diseno.aviso_sin_ia_diaria() if diaria else diseno.AVISO_SIN_IA
        previos: List[str] = []
        ya_avisado = False
        if session_id:
            try:
                turnos = _SESIONES_BD.cargar(session_id)
                previos = [t.get("text", "") for t in turnos if t.get("role") == "user"]
                # Si el último mensaje de Foody ya explicó que está en modo simple, no se repite el aviso largo.
                ya_avisado = bool(turnos) and turnos[-1].get("role") == "model" and diseno.es_respuesta_sin_ia(turnos[-1].get("text"))
            except Exception:  # noqa: BLE001 - el historial es un extra, nunca debe romper la respuesta
                log.warning("No pude leer el historial para el modo sin IA", exc_info=True)
        texto, lista = diseno.armar_respuesta_sin_ia(message, self._search_restaurants, aviso,
                                                     historial=previos, ya_avisado=ya_avisado)
        self.last_restaurants = lista
        if session_id:
            try:
                self._guardar_turno(session_id, message, texto)
            except Exception:  # noqa: BLE001
                log.warning("No pude guardar el turno del modo sin IA", exc_info=True)
        return texto

    def _execute_tool(self, function_name: str, args: dict) -> dict:
        """Execute a tool call against the database."""

        if function_name == "buscar_restaurantes":
            return self._search_restaurants(args)
        elif function_name == "obtener_detalle_restaurante":
            return self._get_restaurant_detail(args)
        elif function_name == "buscar_por_cercania":
            return self._search_nearby(args)
        elif function_name == "obtener_fuentes":
            return self._get_source_info(args)
        else:
            return {"error": f"Función desconocida: {function_name}"}

    # ------------------------------------------------------------- búsquedas

    def _search_restaurants(self, args: dict) -> dict:
        """Search restaurants in database."""

        # Parámetros que devolvió la IA: se limpian y se valida la cobertura (toda la Argentina)
        args = diseno.normalizar_parametros_busqueda(args)
        ok, motivo = diseno.validar_parametros(args)
        if not ok:
            return {"error": motivo, "fuera_de_cobertura": True, "total": 0, "restaurants": []}

        limite = diseno.normalizar_limite(args.get("limite"))

        consulta = """
            SELECT r.restaurant_id, r.name, r.province, r.city, r.neighborhood,
                   r.address, r.latitude, r.longitude, r.cuisine_type, r.category,
                   r.phone, r.website, r.opening_hours, r.price_range, r.rating,
                   r.source_type, r.confidence_level,
                   rf.has_gluten_free_options, rf.has_vegetarian_options,
                   rf.has_vegan_options, rf.has_lactose_free_options,
                   s.name as source_name
            FROM restaurants r
            LEFT JOIN restaurant_features rf ON r.restaurant_id = rf.restaurant_id
            LEFT JOIN sources s ON r.source_id = s.source_id
            WHERE r.is_active = TRUE
        """

        params = {}

        if args.get("provincia"):
            consulta += " AND r.province ILIKE :provincia"
            params["provincia"] = f"%{args['provincia']}%"

        if args.get("ciudad"):
            consulta += " AND r.city ILIKE :ciudad"
            params["ciudad"] = f"%{args['ciudad']}%"

        if args.get("tipo_cocina"):
            cuisines = args["tipo_cocina"]
            if isinstance(cuisines, list):
                cuisine_conditions = " OR ".join([f":cuisine_{i} = ANY(r.cuisine_type)" for i in range(len(cuisines))])
                for i, c in enumerate(cuisines):
                    params[f"cuisine_{i}"] = c.lower()
                consulta += " AND (" + cuisine_conditions + ")"  # solo marcadores :cuisine_N, nunca texto del usuario

        if args.get("precio_maximo"):
            # los locales sin dato de precio se incluyen (casi ninguno lo tiene cargado)
            consulta += " AND (r.price_range IS NULL OR r.price_range <= :precio_max)"
            params["precio_max"] = args["precio_maximo"]

        if args.get("buscar_texto"):
            consulta += " AND r.name ILIKE :search"
            params["search"] = f"%{args['buscar_texto']}%"

        # Restricciones alimentarias. Se piden primero las que la fuente declara
        # (TRUE). Si no alcanzan, se completan con las que NO tienen dato (NULL),
        # marcadas como no confirmadas. Nunca se incluye un FALSE explícito.
        dietas = []
        if args.get("requiere_sin_tacc"):
            dietas.append(("rf.has_gluten_free_options", "sin TACC", 17))
        if args.get("requiere_vegetariano"):
            dietas.append(("rf.has_vegetarian_options", "vegetariano", 18))
        if args.get("requiere_vegano"):
            dietas.append(("rf.has_vegan_options", "vegano", 19))

        estricta = ""
        if dietas:
            estricta = " AND " + " AND ".join(f"{col} = TRUE" for col, _, _ in dietas)

        orden = " ORDER BY r.rating DESC NULLS LAST, r.name"
        params["limit"] = limite

        try:
            filas = list(self.db.execute(
                text(consulta + estricta + orden + " LIMIT :limit"), params
            ).fetchall())

            ampliado = False
            if dietas and len(filas) < limite:
                relajada = " AND " + " AND ".join(
                    f"({col} IS NULL OR {col} = TRUE)" for col, _, _ in dietas)
                excluir_estrictas = " AND (" + " OR ".join(
                    f"{col} IS DISTINCT FROM TRUE" for col, _, _ in dietas) + ")"
                params_ampliados = dict(params)
                params_ampliados["limit"] = limite - len(filas)
                extra = self.db.execute(
                    text(consulta + relajada + excluir_estrictas + orden + " LIMIT :limit"),
                    params_ampliados,
                ).fetchall()
                if extra:
                    filas.extend(extra)
                    ampliado = True

            restaurants = []
            for row in filas:
                item = {
                    "restaurant_id": row[0],
                    "name": row[1],
                    "province": row[2],
                    "city": row[3],
                    "neighborhood": row[4],
                    "address": row[5],
                    "latitude": float(row[6]) if row[6] else None,
                    "longitude": float(row[7]) if row[7] else None,
                    "cuisine_type": row[8] if row[8] else [],
                    "category": row[9],
                    "phone": row[10],
                    "website": row[11],
                    "opening_hours": row[12],
                    "price_range": row[13],
                    "rating": float(row[14]) if row[14] else None,
                    "source_type": row[15],
                    "confidence_level": row[16],
                    "features": {
                        "has_gluten_free_options": row[17],
                        "has_vegetarian_options": row[18],
                        "has_vegan_options": row[19],
                        "has_lactose_free_options": row[20],
                    },
                    "source_name": row[21],
                }
                if dietas:
                    sin_dato = [nombre for _, nombre, idx in dietas if row[idx] is not True]
                    item["dato_confirmado"] = not sin_dato
                    if sin_dato:
                        item["dietas_sin_dato"] = sin_dato
                restaurants.append(item)

            resultado = {
                "total": len(restaurants),
                "restaurants": restaurants,
            }
            if ampliado:
                resultado["aviso"] = (
                    "Algunas opciones no tienen el dato de la restricción confirmado en la fuente "
                    "(aparecen con dato_confirmado=false). No las presentes como seguras: "
                    "aclará que hay que confirmar con el local."
                )
            return resultado

        except Exception:
            log.exception("Error en _search_restaurants")
            self.db.rollback()
            return {**ERROR_GENERICO, "total": 0, "restaurants": []}

    def _get_restaurant_detail(self, args: dict) -> dict:
        """Get detailed restaurant information."""

        restaurant_id = args.get("restaurant_id")
        if not restaurant_id:
            return {"error": "Se requiere restaurant_id"}

        query = """
            SELECT r.*, 
                   rf.has_gluten_free_options, rf.has_vegetarian_options,
                   rf.has_vegan_options, rf.has_lactose_free_options,
                   rf.celiac_certified,
                   s.name as source_name, s.url as source_url,
                   s.reliability as source_reliability, s.license as source_license,
                   s.last_updated as source_last_updated
            FROM restaurants r
            LEFT JOIN restaurant_features rf ON r.restaurant_id = rf.restaurant_id
            LEFT JOIN sources s ON r.source_id = s.source_id
            WHERE r.restaurant_id = :id AND r.is_active = TRUE
        """

        try:
            result = self.db.execute(text(query), {"id": restaurant_id})
            row = result.fetchone()

            if not row:
                return {"error": "Restaurante no encontrado"}

            return {
                "advertencia_alimentaria": diseno.advertencia_alimentaria({
                    "has_gluten_free_options": row[25], "has_vegetarian_options": row[26],
                    "has_vegan_options": row[27], "has_lactose_free_options": row[28],
                    "celiac_certified": row[29]}),
                "restaurant_id": row[0],
                "name": row[1],
                "province": row[3],
                "city": row[4],
                "neighborhood": row[5],
                "address": row[6],
                "latitude": float(row[7]) if row[7] else None,
                "longitude": float(row[8]) if row[8] else None,
                "cuisine_type": row[9] if row[9] else [],
                "category": row[10],
                "phone": row[11],
                "email": row[12],
                "website": row[13],
                "opening_hours": row[15],
                "price_range": row[16],
                "rating": float(row[17]) if row[17] else None,
                "review_count": row[18],
                "source_type": row[20],
                "confidence_level": row[21],
                "data_date": str(row[22]) if row[22] else None,
                "features": {
                    "has_gluten_free_options": row[25],
                    "has_vegetarian_options": row[26],
                    "has_vegan_options": row[27],
                    "has_lactose_free_options": row[28],
                    "celiac_certified": row[29],
                },
                "source": {
                    "name": row[30],
                    "url": row[31],
                    "reliability": row[32],
                    "license": row[33],
                    "last_updated": str(row[34]) if row[34] else None,
                },
            }

        except Exception:
            log.exception("Error en herramienta de chat")
            self.db.rollback()
            return dict(ERROR_GENERICO)

    def _search_nearby(self, args: dict) -> dict:
        """Search restaurants near a location."""

        lat = args.get("latitud")
        lon = args.get("longitud")
        try:
            radius_km = max(0.1, min(float(args.get("radio_km", 2.0)), 20.0))
        except (TypeError, ValueError):
            radius_km = 2.0
        limit = diseno.normalizar_limite(args.get("limite"))

        if not lat or not lon:
            return {"error": "Se requieren latitud y longitud"}

        # ST_DWithin usa el índice GiST y descarta lo que está fuera del radio
        # ANTES de calcular distancias. El orden KNN (<->) también usa el índice.
        # Se agrega un pre-filtro con && y ST_Expand (en grados) para que el
        # índice GiST se use aunque la distancia exacta sea geográfica.
        radio_deg = radius_km / (111.32 * max(0.2, math.cos(math.radians(float(lat))))) * 1.1
        query = """
            WITH punto AS (
                SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS g
            )
            SELECT r.restaurant_id, r.name, r.province, r.city,
                   r.latitude, r.longitude, r.cuisine_type, r.category,
                   r.phone, r.price_range, r.rating, r.confidence_level,
                   rf.has_gluten_free_options,
                   ST_Distance(r.geom::geography, p.g::geography) as distance_meters
            FROM restaurants r
            CROSS JOIN punto p
            LEFT JOIN restaurant_features rf ON r.restaurant_id = rf.restaurant_id
            WHERE r.is_active = TRUE
              AND r.geom IS NOT NULL
              AND r.geom && ST_Expand(p.g, :radio_deg)
              AND ST_DWithin(r.geom::geography, p.g::geography, :radio_m)
            ORDER BY r.geom <-> p.g
            LIMIT :limit
        """

        try:
            result = self.db.execute(text(query), {
                "lat": lat,
                "lon": lon,
                "radio_m": radius_km * 1000.0,
                "radio_deg": radio_deg,
                "limit": limit,
            })
            rows = result.fetchall()

            restaurants = []
            for row in rows:
                restaurants.append({
                    "restaurant_id": row[0],
                    "name": row[1],
                    "province": row[2],
                    "city": row[3],
                    "latitude": float(row[4]) if row[4] else None,
                    "longitude": float(row[5]) if row[5] else None,
                    "cuisine_type": row[6] if row[6] else [],
                    "category": row[7],
                    "phone": row[8],
                    "price_range": row[9],
                    "rating": float(row[10]) if row[10] else None,
                    "confidence_level": row[11],
                    "features": {
                        "has_gluten_free_options": row[12],
                    },
                    "distance_meters": round(float(row[13])) if row[13] else None,
                })

            return {
                "total": len(restaurants),
                "center": {"lat": lat, "lon": lon},
                "radius_km": radius_km,
                "restaurants": restaurants
            }

        except Exception:
            log.exception("Error en herramienta de chat")
            self.db.rollback()
            return dict(ERROR_GENERICO)

    def _get_source_info(self, args: dict) -> dict:
        """Get source/tracking information for a restaurant."""

        restaurant_id = args.get("restaurant_id")
        if not restaurant_id:
            return {"error": "Se requiere restaurant_id"}

        query = """
            SELECT s.name, s.url, s.source_type, s.license,
                   s.reliability, s.last_updated, s.notes,
                   r.confidence_level, r.data_date, r.fetched_date
            FROM restaurants r
            JOIN sources s ON r.source_id = s.source_id
            WHERE r.restaurant_id = :id
        """

        try:
            result = self.db.execute(text(query), {"id": restaurant_id})
            row = result.fetchone()

            if not row:
                return {"error": "Fuente no encontrada"}

            return {
                "source_name": row[0],
                "source_url": row[1],
                "source_type": row[2],
                "license": row[3],
                "reliability": row[4],
                "last_updated": str(row[5]) if row[5] else None,
                "notes": row[6],
                "confidence_level": row[7],
                "data_date": str(row[8]) if row[8] else None,
                "fetched_date": str(row[9]) if row[9] else None,
            }

        except Exception:
            log.exception("Error en herramienta de chat")
            self.db.rollback()
            return dict(ERROR_GENERICO)

    # ------------------------------------------------------------- conversación

    def send_message(self, message: str, session_id: str = "default") -> str:
        """Process a user message and return response."""

        self.last_restaurants = []

        # Sin clave no hay a quién pedirle nada: búsqueda local directa.
        if not self.gemini.api_key:
            return self._sin_ia(message, False, session_id)

        # Solo se serializa la MISMA conversación. Distintos usuarios corren en paralelo.
        with self._lock_sesion(session_id):
            chat = self._obtener_chat(session_id)
            if chat is None:
                return self._sin_ia(message, False, session_id)

            try:
                response = self._enviar(chat, message)

                # Process function calls. El SDK devuelve la lista de llamadas en
                # `response.function_calls`; se responde con partes de función.
                max_iterations = 5
                iteration = 0

                while iteration < max_iterations:
                    llamadas = list(response.function_calls or [])
                    if not llamadas:
                        break
                    iteration += 1

                    partes = []
                    for llamada in llamadas:
                        func_name = llamada.name
                        func_args = dict(llamada.args or {})

                        # Execute function
                        result = self._execute_tool(func_name, func_args)
                        if isinstance(result, dict):
                            self.last_restaurants.extend(
                                r for r in result.get("restaurants", []) if r not in self.last_restaurants)

                        partes.append(types.Part.from_function_response(
                            name=func_name,
                            response={"result": diseno.compactar_para_ia(result)},
                        ))

                    response = self._enviar(chat, partes)

                # Get final text
                final_text = response.text or ""

                if final_text:
                    self._guardar_turno(session_id, message, final_text)
                return final_text or "No pude generar una respuesta."

            except cuota.CuotaAgotada as c:
                log.warning("Sin cuota de Gemini: se responde sin IA (%s)", c)
                return self._sin_ia(message, c.diaria, session_id)
            except Exception as e:
                if _es_timeout(e):
                    log.warning("Gemini no respondió a tiempo: se responde sin IA (%s)", e)
                    self._descartar_chat(session_id)
                    return self._sin_ia(message, False, session_id)
                log.exception("Error al hablar con Gemini")
                err = str(e)
                tipo, _ = cuota.clasificar_error(err)
                if tipo != "otro":
                    return self._sin_ia(message, tipo == "diaria", session_id)
                return "No pude procesar tu mensaje en este momento. Probá de nuevo en un rato."
