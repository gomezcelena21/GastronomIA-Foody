"""
Gastro IA Backend - FastAPI Application
Main application with routes for restaurant search and recommendations.
"""

import hashlib
import math
import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from backend directory
backend_dir = Path(__file__).parent
load_dotenv(backend_dir / ".env")

from typing import List, Optional
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func, or_
from geoalchemy2 import Geography

from database import get_db, engine
from models import Restaurant, RestaurantFeature, Source
from schemas import (
    RestaurantResponse, SearchParams, SearchResponse,
    SourceResponse, RecommendationScore
)
import diseno
import persistencia
import sesion
import seguridad
from seguridad import usuario_actual, usuario_opcional
import comercios
from comercios import router as router_comercios
from models_diseno import Conversacion, Mensaje, Usuario, crear_tablas_diseno
from sqlalchemy.exc import SQLAlchemyError
from rutas_diseno import router as router_diseno
from orquestador import OrquestadorBackend

log = logging.getLogger("gastronomia")

# Login con Google + sesión propia (ver sesion.py y docs/despliegue_y_login.md)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
FRONTEND_ORIGINS = [o.strip() for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

# Los cupos diarios se guardan en PostgreSQL para sobrevivir reinicios y para
# que varios workers compartan el mismo límite. Si la base falla, se usa memoria.
_almacen_cuotas = persistencia.AlmacenCuotas(engine)
_contador_diario = sesion.ContadorDiario(
    int(os.getenv("CONSULTAS_POR_DIA", "10")), almacen=_almacen_cuotas, ambito="usuario")
# Usuario gratuito sin registro: límite por IP y tope general por día (protege la cuota de Gemini)
_contador_anonimo = sesion.ContadorDiario(
    int(os.getenv("ANONIMOS_POR_DIA", "5")), almacen=_almacen_cuotas, ambito="anonimo_ip")
_contador_anonimo_global = sesion.ContadorDiario(
    int(os.getenv("ANONIMOS_POR_DIA_GLOBAL", "300")), almacen=_almacen_cuotas, ambito="anonimo_global")
if len(SESSION_SECRET) < sesion.LARGO_MIN_SECRETO or not GOOGLE_CLIENT_ID:
    log.warning("Login con Google sin configurar: completá GOOGLE_CLIENT_ID y SESSION_SECRET (32+ caracteres) en backend/.env")

# En producción (ENTORNO=produccion) se ocultan /docs, /redoc y /openapi.json.
_PROD = os.getenv("ENTORNO", "desarrollo").lower().startswith("prod")


def _iniciar_sentry() -> None:
    """Sentry es opcional: sin SENTRY_DSN no se instala nada ni se envía nada."""
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("SENTRY_ENVIRONMENT", "produccion" if _PROD else "desarrollo"),
            release=os.getenv("SENTRY_RELEASE") or None,
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0") or 0),
            send_default_pii=False,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        )
        log.info("Sentry configurado (los errores se envían al panel).")
    except Exception:
        log.warning("SENTRY_DSN está definido pero Sentry no pudo iniciarse", exc_info=True)


_iniciar_sentry()

# Índices que faltaban para las consultas reales del chat y de Explorar.
# Son idempotentes: si ya existen no hacen nada. Se aplican al iniciar (se puede
# desactivar con OPTIMIZAR_AL_INICIAR=0) y también están en database/maintenance.sql.
_INDICES_MANTENIMIENTO = (
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE INDEX IF NOT EXISTS idx_restaurants_city_trgm ON restaurants USING GIN (city gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS idx_restaurants_province_trgm ON restaurants USING GIN (province gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS idx_restaurants_rating_act ON restaurants (rating DESC NULLS LAST) WHERE is_active",
    "CREATE INDEX IF NOT EXISTS idx_features_gluten_act ON restaurant_features (restaurant_id) WHERE has_gluten_free_options IS TRUE",
    "CREATE INDEX IF NOT EXISTS idx_features_vegetariano_act ON restaurant_features (restaurant_id) WHERE has_vegetarian_options IS TRUE",
    "CREATE INDEX IF NOT EXISTS idx_features_vegano_act ON restaurant_features (restaurant_id) WHERE has_vegan_options IS TRUE",
)


def _optimizar_base() -> None:
    """Crea los índices que faltan y actualiza las estadísticas del planificador.

    Sin ANALYZE, PostgreSQL no sabe cuántas filas hay y puede elegir planes malos.
    Es barato (71.343 filas) y evita que el ETL deje la base 'sin datos' para el planner."""
    if os.getenv("OPTIMIZAR_AL_INICIAR", "1") != "1":
        return
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for sql in _INDICES_MANTENIMIENTO:
            try:
                conn.exec_driver_sql(sql)
            except Exception:
                log.warning("No se pudo aplicar al iniciar: %s", sql.splitlines()[0])
        for tabla in ("restaurants", "restaurant_features", "sources", "menus"):
            try:
                conn.exec_driver_sql("ANALYZE " + tabla)
            except Exception:
                log.warning("No se pudo analizar la tabla %s", tabla)


@asynccontextmanager
async def _ciclo_vida(_app):
    try:
        _optimizar_base()
    except Exception:
        log.exception("No se pudo optimizar la base al iniciar; la API sigue funcionando")
    try:
        # Crea cuotas_diarias y sesiones_gemini si faltan (idempotente).
        _almacen_cuotas._preparar()
    except Exception:
        log.exception("No se pudo preparar la persistencia de cupos; se usa memoria")
    yield


app = FastAPI(
    title="GastronomIA API",
    description="API para búsqueda y recomendación de restaurantes en Argentina",
    version="1.0.0",
    docs_url=None if _PROD else "/docs",
    redoc_url=None if _PROD else "/redoc",
    openapi_url=None if _PROD else "/openapi.json",
    lifespan=_ciclo_vida,
)

# CORS: solo los orígenes de FRONTEND_ORIGINS (en producción, el dominio del frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def cabeceras_seguras(request: Request, call_next):
    """Cabeceras de seguridad en todas las respuestas; lo personal nunca se guarda en caché."""
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith(("/api/auth", "/api/chat", "/api/usuarios", "/api/conversaciones", "/api/resenas", "/api/comercio", "/api/admin")):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


# Endpoints del diseño (usuarios, restricciones, reseñas, mensajes) y tablas nuevas
app.include_router(router_diseno)
app.include_router(router_comercios)
try:
    crear_tablas_diseno(engine)
except Exception:  # la API sigue funcionando; los endpoints nuevos avisan si falta la BD
    log.exception("No se pudieron crear las tablas del diseño")

_limitador_chat = diseno.LimitadorTasa(max_eventos=20, ventana_seg=60)


def limitar_chat(request: Request) -> None:
    ip = request.client.host if request.client else "desconocida"
    if not _limitador_chat.permitir(ip):
        raise HTTPException(status_code=429, detail="Demasiados mensajes. Esperá un minuto.")


@app.get("/")
def root():
    return {"message": "GastronomIA API", "version": "1.0.0"}


@app.api_route("/ping", methods=["GET", "HEAD"])
def ping():
    """Latido liviano: NO consulta la base de datos ni la IA.
    Sirve para que un monitor externo (UptimeRobot, etc.) mantenga despierto el servidor gratuito
    sin mantener encendida la base (Neon gratis tiene horas de cómputo limitadas)."""
    return {"ok": True}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        log.exception("Health check: la base de datos no responde")
        return {"status": "unhealthy", "database": "no disponible"}


@app.get("/api/establecimientos", response_model=SearchResponse)
@app.get("/api/restaurants", response_model=SearchResponse)
def search_restaurants(
    province: Optional[str] = None,
    city: Optional[str] = None,
    neighborhood: Optional[str] = None,
    region: Optional[str] = None,
    district: Optional[str] = None,
    zone: Optional[str] = None,
    cuisine: Optional[str] = None,
    price_max: Optional[int] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: float = 5.0,
    gluten_free: Optional[bool] = None,
    vegetarian: Optional[bool] = None,
    vegan: Optional[bool] = None,
    search: Optional[str] = None,
    # ge=1 evita la división por cero de `offset // limit`; offset negativo rompía la consulta (500)
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(get_db)
):
    """Search restaurants with various filters."""
    
    query = db.query(Restaurant).filter(Restaurant.is_active == True)
    
    # Province filter
    if province:
        query = query.filter(Restaurant.province.ilike(f"%{province}%"))
    
    # City filter
    if city:
        query = query.filter(Restaurant.city.ilike(f"%{city}%"))
    
    # Cuisine filter
    if cuisine:
        query = query.filter(Restaurant.cuisine_type.any(cuisine.lower()))
    
    # Price filter
    if price_max:
        query = query.filter(Restaurant.price_range <= price_max)
    
    # Neighborhood filter
    if neighborhood:
        query = query.filter(Restaurant.neighborhood.ilike(f"%{neighborhood}%"))

    # Región (CABA/GBA/Interior), partido de GBA y zona macro
    for valor, columna in ((region, Restaurant.region), (district, Restaurant.district),
                           (zone, Restaurant.zone_macro)):
        if valor:
            query = query.filter(columna.ilike(f"%{valor}%"))

    # Dietary filters (restricciones alimentarias)
    for flag, col in ((gluten_free, RestaurantFeature.has_gluten_free_options),
                      (vegetarian, RestaurantFeature.has_vegetarian_options),
                      (vegan, RestaurantFeature.has_vegan_options)):
        if flag:
            query = query.filter(Restaurant.restaurant_id.in_(
                db.query(RestaurantFeature.restaurant_id).filter(col == True)))

    # Text search
    if search:
        query = query.filter(Restaurant.name.ilike(f"%{search}%"))
    
    # Geospatial filter using PostGIS: primero descarta por radio (índice GiST)
    # y recién después ordena por cercanía con el operador KNN (<->).
    if lat is not None and lon is not None:
        # Mismo tope que /api/restaurants/nearby: un radio enorme recorría toda la tabla.
        radius_km = max(0.0, min(float(radius_km), 20.0))
        punto = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        radio_deg = max(0.0, radius_km) / (111.32 * max(0.2, math.cos(math.radians(lat)))) * 1.1
        query = query.filter(
            Restaurant.geom.isnot(None),
            Restaurant.geom.op("&&")(func.ST_Expand(punto, radio_deg)),
            func.ST_DWithin(
                func.cast(Restaurant.geom, Geography),
                func.cast(punto, Geography),
                max(0.0, radius_km) * 1000.0,
            ),
        ).order_by(Restaurant.geom.op("<->")(punto))
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    results = query.offset(offset).limit(limit).all()
    
    # Enrich with feature data in two batch queries (antes era 2 consultas POR
    # cada restaurante: con 30 fichas, 60 viajes a la base).
    enriched_results = []
    ids = [r.restaurant_id for r in results]
    features_por_id = {}
    sources_por_id = {}
    if ids:
        features_por_id = {
            f.restaurant_id: f
            for f in db.query(RestaurantFeature).filter(
                RestaurantFeature.restaurant_id.in_(ids)
            ).all()
        }
        source_ids = {r.source_id for r in results if r.source_id is not None}
        if source_ids:
            sources_por_id = {
                s.source_id: s
                for s in db.query(Source).filter(Source.source_id.in_(source_ids)).all()
            }

    for r in results:
        features = features_por_id.get(r.restaurant_id)
        source = sources_por_id.get(r.source_id)

        result_dict = {
            "restaurant_id": r.restaurant_id,
            "name": r.name,
            "province": r.province,
            "city": r.city,
            "neighborhood": r.neighborhood,
            "region": r.region,
            "district": r.district,
            "zone_macro": r.zone_macro,
            "address": r.address,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "cuisine_type": r.cuisine_type,
            "category": r.category,
            "phone": r.phone,
            "email": r.email,
            "website": r.website,
            "opening_hours": r.opening_hours,
            "price_range": r.price_range,
            "rating": r.rating,
            "review_count": r.review_count,
            "source_type": r.source_type,
            "confidence_level": r.confidence_level,
            "data_date": r.data_date,
            "has_gluten_free_options": features.has_gluten_free_options if features else None,
            "has_vegetarian_options": features.has_vegetarian_options if features else None,
            "has_vegan_options": features.has_vegan_options if features else None,
            "has_lactose_free_options": features.has_lactose_free_options if features else None,
            "celiac_certified": features.celiac_certified if features else None,
            "source_name": source.name if source else None,
            "source_url": source.url if source else None,
            "source_reliability": source.reliability if source else None,
        }
        enriched_results.append(result_dict)
    
    return SearchResponse(
        results=enriched_results,
        total=total,
        page=offset // limit + 1,
        page_size=limit,
        has_more=(offset + limit) < total
    )


@app.get("/api/establecimientos/{restaurant_id:int}")
@app.get("/api/restaurants/{restaurant_id:int}")
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific restaurant."""
    
    restaurant = db.query(Restaurant).filter(
        Restaurant.restaurant_id == restaurant_id,
        Restaurant.is_active == True
    ).first()
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado.")
    
    features = db.query(RestaurantFeature).filter(
        RestaurantFeature.restaurant_id == restaurant_id
    ).first()
    
    source = db.query(Source).filter(
        Source.source_id == restaurant.source_id
    ).first()
    
    features_dict = {
        "has_gluten_free_options": features.has_gluten_free_options if features else None,
        "has_vegetarian_options": features.has_vegetarian_options if features else None,
        "has_vegan_options": features.has_vegan_options if features else None,
        "has_lactose_free_options": features.has_lactose_free_options if features else None,
        "celiac_certified": features.celiac_certified if features else None,
    }
    return {
        "advertencia_alimentaria": diseno.advertencia_alimentaria(features_dict),
        "restaurant_id": restaurant.restaurant_id,
        "name": restaurant.name,
        "province": restaurant.province,
        "city": restaurant.city,
        "neighborhood": restaurant.neighborhood,
        "region": restaurant.region,
        "district": restaurant.district,
        "zone_macro": restaurant.zone_macro,
        "address": restaurant.address,
        "latitude": restaurant.latitude,
        "longitude": restaurant.longitude,
        "cuisine_type": restaurant.cuisine_type,
        "category": restaurant.category,
        "phone": restaurant.phone,
        "email": restaurant.email,
        "website": restaurant.website,
        "opening_hours": restaurant.opening_hours,
        "price_range": restaurant.price_range,
        "rating": restaurant.rating,
        "review_count": restaurant.review_count,
        "source_type": restaurant.source_type,
        "confidence_level": restaurant.confidence_level,
        "data_date": restaurant.data_date,
        "features": {
            "has_gluten_free_options": features.has_gluten_free_options if features else None,
            "has_vegetarian_options": features.has_vegetarian_options if features else None,
            "has_vegan_options": features.has_vegan_options if features else None,
            "has_lactose_free_options": features.has_lactose_free_options if features else None,
            "celiac_certified": features.celiac_certified if features else None,
        },
        "source": {
            "name": source.name if source else None,
            "url": source.url if source else None,
            "reliability": source.reliability if source else None,
            "license": source.license if source else None,
        } if source else None,
    }


@app.get("/api/restaurants/nearby")
def find_nearby(
    lat: float,
    lon: float,
    radius_km: float = 2.0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Find restaurants near a specific location."""
    limite = max(1, min(int(limit), 100))
    radio_m = max(0.1, min(float(radius_km), 20.0)) * 1000.0
    radio_deg = max(0.1, min(float(radius_km), 20.0)) / (
        111.32 * max(0.2, math.cos(math.radians(lat)))) * 1.1

    # ST_DWithin filtra por el índice GiST; <-> ordena por cercanía. La distancia
    # se calcula una sola vez en SQL (antes se hacía una consulta por resultado).
    filas = db.execute(text("""
        WITH punto AS (
            SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS g
        )
        SELECT r.restaurant_id, r.name, r.province, r.city,
               r.latitude, r.longitude, r.cuisine_type, r.category,
               ST_Distance(r.geom::geography, p.g::geography) AS distance_meters
        FROM restaurants r
        CROSS JOIN punto p
        WHERE r.is_active = TRUE
          AND r.geom IS NOT NULL
          AND r.geom && ST_Expand(p.g, :radio_deg)
          AND ST_DWithin(r.geom::geography, p.g::geography, :radio_m)
        ORDER BY r.geom <-> p.g
        LIMIT :limit
    """), {"lat": lat, "lon": lon, "radio_m": radio_m, "radio_deg": radio_deg,
           "limit": limite}).fetchall()

    return {
        "results": [
            {
                "restaurant_id": f[0],
                "name": f[1],
                "province": f[2],
                "city": f[3],
                "latitude": float(f[4]) if f[4] else None,
                "longitude": float(f[5]) if f[5] else None,
                "cuisine_type": f[6],
                "category": f[7],
                "distance_meters": round(float(f[8])) if f[8] is not None else None,
            }
            for f in filas
        ],
        "total": len(filas),
        "center": {"lat": lat, "lon": lon},
        "radius_km": float(radius_km),
    }


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get database statistics."""
    
    total = db.query(Restaurant).filter(Restaurant.is_active == True).count()
    with_coords = db.query(Restaurant).filter(
        Restaurant.is_active == True,
        Restaurant.geom.isnot(None)
    ).count()
    
    by_province = db.query(
        Restaurant.province,
        func.count(Restaurant.restaurant_id)
    ).filter(
        Restaurant.is_active == True
    ).group_by(Restaurant.province).all()
    
    by_source = db.query(
        Restaurant.source_type,
        func.count(Restaurant.restaurant_id)
    ).filter(
        Restaurant.is_active == True
    ).group_by(Restaurant.source_type).all()
    
    return {
        "total_restaurants": total,
        "with_coordinates": with_coords,
        "by_province": {p: c for p, c in by_province},
        "by_source": {s: c for s, c in by_source},
    }


@app.get("/api/sources", response_model=List[SourceResponse])
def get_sources(db: Session = Depends(get_db)):
    """Get all data sources."""
    sources = db.query(Source).all()
    return sources


# ============================================================
# CHAT ENDPOINTS
# ============================================================

from pydantic import BaseModel, Field
from chat_service import ChatService
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# El ChatService ahora dura lo que dura el pedido: su sesión de BD y su
# last_restaurants no se comparten entre usuarios. El historial de Gemini se
# guarda por session_id dentro de chat_service.py (con un lock por sesión).
def get_chat_service(db: Session) -> ChatService:
    return ChatService(db, GEMINI_API_KEY or None)


class ChatMessage(BaseModel):
    message: str = Field(min_length=1, max_length=1500)
    session_id: str = "default"
    # Con cuenta: qué conversación se está usando. Vacío = la de siempre ("principal").
    chat_id: str = ""
    id_usuario: Optional[int] = None


class ChatSessionReset(BaseModel):
    session_id: str = "default"
    chat_id: str = ""


# Una cuenta puede tener varias conversaciones (pestaña "Chat nuevo").
# El chat_id lo elige el navegador, pero SIEMPRE se le antepone el uid del token:
# así nadie puede pedir la conversación de otra persona cambiando un número.
MAX_CHAT_ID = 40


def _sesion_o_422(session_id: str) -> str:
    if not diseno.sesion_valida(session_id):
        raise HTTPException(status_code=422, detail="session_id inválido.")
    return session_id


def _chat_id_valido(chat_id: str) -> bool:
    return diseno.sesion_valida(chat_id) and len(chat_id) <= MAX_CHAT_ID


def _clave_chat(uid: int, chat_id: str) -> str:
    """session_key de una conversación: una por chat, todas de la misma cuenta.

    "principal" es la conversación histórica (antes había una sola por cuenta y
    se guardaba como "u<uid>"); se mantiene para no perder el historial ya guardado.
    """
    chat_id = chat_id or "principal"
    return "u%d" % uid if chat_id == "principal" else "u%d_%s" % (uid, chat_id)


def _chat_id_de(uid: int, session_key: str) -> Optional[str]:
    """Vuelve de session_key a chat_id, o None si la clave no es de esta cuenta."""
    base = "u%d" % uid
    clave = session_key or ""
    if clave == base:
        return "principal"
    if clave.startswith(base + "_"):
        resto = clave[len(base) + 1:]
        return resto if _chat_id_valido(resto) else None
    return None


class GoogleLogin(BaseModel):
    credential: str = Field(min_length=20, max_length=4096)


@app.post("/api/auth/google", dependencies=[Depends(limitar_chat)])
def login_google(payload: GoogleLogin, db: Session = Depends(get_db)):
    """Cambia el ID token de Google por un token de sesión propio (no se guardan contraseñas).
    La cuenta de Google es el usuario: se crea la primera vez y después se reutiliza (el historial es suyo)."""
    if not GOOGLE_CLIENT_ID or len(seguridad.secreto()) < sesion.LARGO_MIN_SECRETO:
        raise HTTPException(status_code=503, detail="El inicio de sesión no está configurado en el servidor.")
    try:
        u = sesion.verificar_google(payload.credential, GOOGLE_CLIENT_ID)
    except sesion.SesionInvalida:
        raise HTTPException(status_code=401, detail="No pudimos verificar tu cuenta de Google.")
    email = u["email"].strip().lower()
    try:
        fila = db.query(Usuario).filter(Usuario.email == email).first()
        if fila is None:
            fila = Usuario(nombre=u["nombre"], email=email)
            db.add(fila)
            db.commit()
            db.refresh(fila)
        uid, nombre = fila.id_usuario, fila.nombre
        es_comercio = comercios.tiene_comercio(db, uid)
    except SQLAlchemyError:
        db.rollback()
        log.exception("No se pudo registrar al usuario en el login")
        raise HTTPException(status_code=503, detail="La base de datos no está disponible. Probá más tarde.")
    token = sesion.firmar_sesion({"sub": u["sub"], "uid": uid, "email": email, "nombre": nombre}, seguridad.secreto())
    return {"token": token, "usuario": {"id_usuario": uid, "email": email, "nombre": nombre, "comercio": es_comercio,
                          "admin": comercios.es_admin(email)},
            "consultas_por_dia": _contador_diario.maximo}


@app.get("/api/auth/me")
def quien_soy(usuario: dict = Depends(usuario_actual)):
    return {"email": usuario["email"], "nombre": usuario["nombre"],
            "consultas_restantes": _contador_diario.restantes(usuario["sub"])}


def _identidad_chat(request: Request, session_id: str, usuario: Optional[dict],
                    chat_id: str = "") -> tuple:
    """(sid, uid, clave de cupo). Con cuenta: cada conversación tiene su propio
    historial y todas quedan atadas a la cuenta de Google. Invitado: sesión atada
    a su IP, sin historial guardado a su nombre."""
    if usuario:
        if chat_id and not _chat_id_valido(chat_id):
            raise HTTPException(status_code=422, detail="chat_id inválido.")
        return _clave_chat(usuario["uid"], chat_id), usuario["uid"], usuario["sub"]
    ip = request.client.host if request.client else "desconocida"
    sid = "a" + hashlib.sha256(("%s|%s" % (ip, session_id)).encode()).hexdigest()[:24]
    return sid, None, "ip:" + ip


@app.post("/api/chat", dependencies=[Depends(limitar_chat)])
def chat_endpoint(request: Request, payload: ChatMessage, db: Session = Depends(get_db),
                  usuario: Optional[dict] = Depends(usuario_opcional)):
    """Flujo de 8 etapas del diseño (ver orquestador.py). Se puede usar sin registrarse (con tope diario menor);
    con cuenta de Google se conserva el historial y el tope es mayor."""
    _sesion_o_422(payload.session_id)           # se valida el formato; la sesión real la fija el servidor
    sid, uid, clave = _identidad_chat(request, payload.session_id, usuario, payload.chat_id)
    if diseno.detectar_datos_personales(payload.message):
        return {"response": diseno.MENSAJE_DATOS_PERSONALES, "session_id": sid, "restaurants": [],
                "id_conversacion": None, "validada": True}
    if diseno.fuera_de_tema(payload.message):
        return {"response": diseno.MENSAJE_FUERA_DE_TEMA, "session_id": sid, "restaurants": [],
                "id_conversacion": None, "validada": True}
    if usuario is None:
        if not _contador_anonimo.consumir(clave):
            raise HTTPException(status_code=429, detail="Llegaste al máximo de consultas de hoy sin cuenta. Iniciá sesión con Google para seguir.")
        if not _contador_anonimo_global.consumir("global"):
            raise HTTPException(status_code=429, detail="Hoy se alcanzó el límite de consultas sin cuenta. Probá mañana o iniciá sesión con Google.")
    elif not _contador_diario.consumir(clave):
        raise HTTPException(status_code=429, detail="Llegaste al máximo de consultas de hoy. Volvé mañana.")
    service = get_chat_service(db)
    return OrquestadorBackend(db, service).procesar_consulta(payload.message, sid, uid)


def _texto_visible(texto: str) -> str:
    """Mensaje tal como lo escribió la persona, sin la anotación interna de filtros.

    El frontend agrega «[Filtros activos: …]» al enviar para que la IA los tenga en
    cuenta; en la lista de chats y al reabrir una conversación eso no se muestra.
    """
    return re.sub(r"\s*\[Filtros activos:[^\]]*\]\s*$", "", (texto or "").strip()).strip()


def _titulo_conversacion(db: Session, id_conversacion: int) -> str:
    """Primer mensaje de la persona, que es el mejor título para la lista de chats."""
    primero = (db.query(Mensaje)
               .filter(Mensaje.id_conversacion == id_conversacion, Mensaje.rol == "usuario")
               .order_by(Mensaje.id_mensaje).first())
    texto = _texto_visible(primero.contenido if primero else "").replace("\n", " ")
    return texto[:60] or "Chat sin título"


@app.get("/api/chat/conversaciones", dependencies=[Depends(limitar_chat)])
def chat_conversaciones(db: Session = Depends(get_db), usuario: dict = Depends(usuario_actual)):
    """Conversaciones de ESTA cuenta, de la más reciente a la más vieja (para el historial del chat)."""
    try:
        filas = (db.query(Conversacion)
                 .filter(Conversacion.id_usuario == usuario["uid"])
                 .order_by(Conversacion.fecha_ultima_actividad.desc())
                 .limit(120).all())
        vistas, salida = set(), []
        for conv in filas:
            chat_id = _chat_id_de(usuario["uid"], conv.session_key)
            if not chat_id or chat_id in vistas:
                continue
            vistas.add(chat_id)
            salida.append({
                "chat_id": chat_id,
                "titulo": _titulo_conversacion(db, conv.id_conversacion),
                "fecha": conv.fecha_ultima_actividad.isoformat() if conv.fecha_ultima_actividad else None,
                "mensajes": int(db.query(func.count(Mensaje.id_mensaje))
                                .filter(Mensaje.id_conversacion == conv.id_conversacion).scalar() or 0),
                "activa": bool(conv.activa),
            })
            if len(salida) >= 30:
                break
        return {"conversaciones": salida}
    except SQLAlchemyError:
        db.rollback()
        log.exception("No se pudieron listar las conversaciones")
        raise HTTPException(status_code=503, detail="No pudimos cargar tus conversaciones ahora.")


@app.get("/api/chat/historial", dependencies=[Depends(limitar_chat)])
def chat_historial(chat_id: str = Query(default=""), limit: int = Query(default=60, ge=1, le=200),
                   db: Session = Depends(get_db), usuario: dict = Depends(usuario_actual)):
    """Mensajes de una conversación de ESTA cuenta (sin chat_id, la más reciente)."""
    if chat_id and not _chat_id_valido(chat_id):
        raise HTTPException(status_code=422, detail="chat_id inválido.")
    sid = _clave_chat(usuario["uid"], chat_id) if chat_id else None
    try:
        consulta = (db.query(Conversacion)
                    .filter(Conversacion.id_usuario == usuario["uid"], Conversacion.activa.is_(True)))
        if sid:
            consulta = consulta.filter(Conversacion.session_key == sid)
        conv = consulta.order_by(Conversacion.id_conversacion.desc()).first()
        if conv is None:
            return {"mensajes": [], "chat_id": chat_id or "principal", "titulo": ""}
        filas = (db.query(Mensaje).filter(Mensaje.id_conversacion == conv.id_conversacion)
                 .order_by(Mensaje.id_mensaje.desc()).limit(limit).all())
        return {"mensajes": [{"rol": m.rol,
                              "contenido": _texto_visible(m.contenido) if m.rol == "usuario" else m.contenido}
                             for m in reversed(filas)],
                "chat_id": _chat_id_de(usuario["uid"], conv.session_key) or "principal",
                "titulo": _titulo_conversacion(db, conv.id_conversacion)}
    except SQLAlchemyError:
        db.rollback()
        log.exception("No se pudo leer el historial")
        raise HTTPException(status_code=503, detail="No pudimos cargar tu historial ahora.")


@app.post("/api/chat/reset", dependencies=[Depends(limitar_chat)])
def chat_reset(request: Request, payload: ChatSessionReset, db: Session = Depends(get_db),
               usuario: Optional[dict] = Depends(usuario_opcional)):
    """Cierra una conversación: sus mensajes quedan guardados, pero el próximo
    mensaje empieza un hilo nuevo (sin el contexto anterior)."""
    _sesion_o_422(payload.session_id)
    if payload.chat_id and not _chat_id_valido(payload.chat_id):
        raise HTTPException(status_code=422, detail="chat_id inválido.")
    sid, _, _ = _identidad_chat(request, payload.session_id, usuario, payload.chat_id)
    service = get_chat_service(db)
    service.reset_session(sid)
    OrquestadorBackend(db, service).cerrar_conversacion(sid)
    return {"status": "ok", "message": "Sesión reiniciada"}


@app.get("/api/cuisines")
def get_cuisine_types(db: Session = Depends(get_db)):
    """Get all distinct cuisine types in the database."""
    query = text("""
        SELECT DISTINCT unnest(cuisine_type) as cuisine
        FROM restaurants
        WHERE is_active = TRUE AND cuisine_type IS NOT NULL
        ORDER BY cuisine
    """)
    result = db.execute(query)
    cuisines = [row[0] for row in result.fetchall() if row[0]]
    return {"cuisines": cuisines}


@app.get("/api/provinces")
def get_provinces(db: Session = Depends(get_db)):
    """Get all distinct provinces in the database."""
    query = text("""
        SELECT DISTINCT province, COUNT(*) as count
        FROM restaurants
        WHERE is_active = TRUE AND province IS NOT NULL
        GROUP BY province
        ORDER BY province
    """)
    result = db.execute(query)
    provinces = [{"name": row[0], "count": row[1]} for row in result.fetchall()]
    return {"provinces": provinces}


@app.get("/api/analytics")
def get_analytics(db: Session = Depends(get_db)):
    """Get comprehensive analytics data for the dashboard."""
    
    # Total
    total = db.execute(text("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE")).scalar()
    
    # By province
    by_province = db.execute(text("""
        SELECT COALESCE(province, 'Sin especificar') as province, COUNT(*) as count
        FROM restaurants WHERE is_active = TRUE GROUP BY province ORDER BY count DESC
    """)).fetchall()
    
    # By city (top 15)
    by_city = db.execute(text("""
        SELECT COALESCE(city, 'Sin especificar') as city, COUNT(*) as count
        FROM restaurants WHERE is_active = TRUE GROUP BY city ORDER BY count DESC LIMIT 15
    """)).fetchall()
    
    # By cuisine (top 15)
    by_cuisine = db.execute(text("""
        SELECT COALESCE(cuisine, 'Sin especificar') as cuisine, COUNT(*) as count
        FROM restaurants, unnest(cuisine_type) as cuisine
        WHERE is_active = TRUE GROUP BY cuisine ORDER BY count DESC LIMIT 15
    """)).fetchall()
    
    # By category
    by_category = db.execute(text("""
        SELECT COALESCE(category, 'Sin especificar') as category, COUNT(*) as count
        FROM restaurants WHERE is_active = TRUE GROUP BY category ORDER BY count DESC
    """)).fetchall()
    
    # By source
    by_source = db.execute(text("""
        SELECT COALESCE(source_type, 'Sin especificar') as source_type, COUNT(*) as count
        FROM restaurants WHERE is_active = TRUE GROUP BY source_type ORDER BY count DESC
    """)).fetchall()
    
    # By confidence
    by_confidence = db.execute(text("""
        SELECT COALESCE(confidence_level, 'Sin especificar') as confidence_level, COUNT(*) as count
        FROM restaurants WHERE is_active = TRUE GROUP BY confidence_level ORDER BY count DESC
    """)).fetchall()
    
    # Completeness metrics
    with_coords = db.execute(text("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND geom IS NOT NULL")).scalar()
    with_phone = db.execute(text("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND phone IS NOT NULL")).scalar()
    with_rating = db.execute(text("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND rating IS NOT NULL")).scalar()
    with_address = db.execute(text("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND address IS NOT NULL")).scalar()
    
    # Dietary features
    gf_count = db.execute(text("SELECT COUNT(*) FROM restaurant_features WHERE has_gluten_free_options = TRUE")).scalar()
    veg_count = db.execute(text("SELECT COUNT(*) FROM restaurant_features WHERE has_vegetarian_options = TRUE")).scalar()
    vegan_count = db.execute(text("SELECT COUNT(*) FROM restaurant_features WHERE has_vegan_options = TRUE")).scalar()
    
    # Nulls
    null_name = db.execute(text("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND (name IS NULL OR name = '')")).scalar()
    null_province = db.execute(text("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND (province IS NULL OR province = '')")).scalar()
    null_city = db.execute(text("SELECT COUNT(*) FROM restaurants WHERE is_active = TRUE AND (city IS NULL OR city = '')")).scalar()
    
    return {
        "total": total,
        "by_province": [{"name": r[0], "count": r[1]} for r in by_province],
        "by_city": [{"name": r[0], "count": r[1]} for r in by_city],
        "by_cuisine": [{"name": r[0], "count": r[1]} for r in by_cuisine],
        "by_category": [{"name": r[0], "count": r[1]} for r in by_category],
        "by_source": [{"name": r[0], "count": r[1]} for r in by_source],
        "by_confidence": [{"name": r[0], "count": r[1]} for r in by_confidence],
        "with_coords": with_coords,
        "with_phone": with_phone,
        "with_rating": with_rating,
        "with_address": with_address,
        "gf_count": gf_count,
        "veg_count": veg_count,
        "vegan_count": vegan_count,
        "null_name": null_name,
        "null_province": null_province,
        "null_city": null_city,
    }


from fastapi.responses import FileResponse

@app.get("/api/downloads")
def list_downloads():
    """List all downloadable files."""
    analytics_dir = Path(__file__).parent.parent / "analytics"
    files = []
    
    # CSV files
    csv_dir = analytics_dir / "csv"
    if csv_dir.exists():
        for f in csv_dir.glob("*.csv"):
            files.append({
                "name": f.name,
                "path": f"csv/{f.name}",
                "type": "csv",
                "size": f.stat().st_size,
            })
    
    # Excel file
    xlsx = analytics_dir / "GastroIA_PowerBI.xlsx"
    if xlsx.exists():
        files.append({
            "name": xlsx.name,
            "path": xlsx.name,
            "type": "xlsx",
            "size": xlsx.stat().st_size,
        })
    
    # PDF file
    pdf = analytics_dir / "GASTRO_IA_Documentacion.pdf"
    if pdf.exists():
        files.append({
            "name": pdf.name,
            "path": pdf.name,
            "type": "pdf",
            "size": pdf.stat().st_size,
        })
    
    # Documentation MD
    md = analytics_dir / "GASTRO_IA_Documentacion.md"
    if md.exists():
        files.append({
            "name": md.name,
            "path": md.name,
            "type": "markdown",
            "size": md.stat().st_size,
        })
    
    # Analysis report
    report = analytics_dir / "ANALISIS_EJECUTIVO.md"
    if report.exists():
        files.append({
            "name": report.name,
            "path": report.name,
            "type": "markdown",
            "size": report.stat().st_size,
        })
    
    return {"files": files}


@app.get("/api/downloads/{file_path:path}")
def download_file(file_path: str):
    """Descarga un archivo de la carpeta analytics (y solo de esa carpeta)."""
    analytics_dir = Path(__file__).parent.parent / "analytics"
    full_path = diseno.resolver_descarga(analytics_dir, file_path)
    if full_path is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    media_types = {
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pdf": "application/pdf",
        ".md": "text/markdown",
    }
    return FileResponse(
        path=str(full_path),
        filename=full_path.name,
        media_type=media_types[full_path.suffix.lower()],
    )
