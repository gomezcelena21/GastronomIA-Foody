"""
GastronomIA - Comercios y emprendimientos.

Quien tiene un comercio o un emprendimiento (incluso online, sin local físico) inicia sesión con Google,
elige "Tengo un comercio" y completa el formulario. Queda en la tabla `comercios` como "pendiente".
Cuando se aprueba (un administrador, o automáticamente si COMERCIOS_AUTOAPROBADOS=1 para pruebas) se
PUBLICA en el catálogo `restaurants`, que es lo que consulta Foody: desde ese momento, quien pregunte por
una pastelería de su zona lo puede recibir como recomendación (siempre marcado como dato cargado por el comercio).

Importante: Google no le informa a las aplicaciones cuándo se creó una cuenta, así que la regla de
"6 meses de antigüedad" no se puede verificar automáticamente. Se cubre con la declaración jurada del
formulario, el link de presencia online y la revisión manual de un administrador.
"""
import logging
import os
import re
from datetime import date, datetime
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import diseno
from database import get_db
from geografia import PROVINCIAS
from models import Restaurant, RestaurantFeature, Source
from models_diseno import Comercio, Usuario
from seguridad import usuario_actual

log = logging.getLogger("gastronomia")
router = APIRouter(prefix="/api", tags=["comercios"])

FUENTE = "Registro de comercios GastronomIA"
_limitador = diseno.LimitadorTasa(max_eventos=30, ventana_seg=60)
_TELEFONO = re.compile(r"^[0-9+()\-\s]{6,40}$")
_INSTAGRAM = re.compile(r"^@?[A-Za-z0-9._]{1,30}$")

# Zonas que puede declarar un comercio: todo el país (CABA y las 23 provincias). Se mantienen los nombres
# que ya usaba el formulario para no invalidar los comercios registrados.
ZONAS_COMERCIO = ("CABA", "Provincia de Buenos Aires") + tuple(
    p for p in PROVINCIAS if p not in ("CABA", "Buenos Aires")
)
_PROVINCIA_POR_ZONA = {"CABA": "CABA", "Provincia de Buenos Aires": "Buenos Aires"}


def _ubicacion(zona: str):
    """(provincia, región, zona) del catálogo para la zona declarada por el comercio."""
    if zona == "CABA":
        return "CABA", "CABA", "CABA"
    if zona == "Provincia de Buenos Aires":      # sin el partido no se sabe si es GBA o interior
        return "Buenos Aires", None, None
    return _PROVINCIA_POR_ZONA.get(zona, zona), "Interior", zona


def limitar_comercio(request: Request) -> None:
    ip = request.client.host if request.client else "desconocida"
    if not _limitador.permitir(ip):
        raise HTTPException(status_code=429, detail="Demasiados pedidos. Esperá un minuto.")


# ---------------------------------------------------------------- administradores
def es_admin(email: str) -> bool:
    admins = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}
    return (email or "").strip().lower() in admins


def exigir_admin(usuario: dict = Depends(usuario_actual)) -> dict:
    if not es_admin(usuario.get("email", "")):
        raise HTTPException(status_code=403, detail="Solo para administradores.")
    return usuario


def _autoaprobar() -> bool:
    return os.getenv("COMERCIOS_AUTOAPROBADOS", "0") == "1"


# -------------------------------------------------------------------- esquemas
class ComercioIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    rubros: List[str] = Field(min_length=1, max_length=3)       # códigos de diseno.RUBROS
    modalidad: Literal["local", "online", "ambos"] = "local"
    zona: str = Field(min_length=2, max_length=40)               # CABA, Buenos Aires o cualquier provincia
    localidad: str = Field(min_length=2, max_length=80)         # barrio o localidad donde atiende o entrega
    direccion: str = Field(default="", max_length=200)          # solo si tiene local físico
    telefono: str = Field(default="", max_length=40)            # teléfono DEL COMERCIO
    instagram: str = Field(default="", max_length=31)
    sitio_web: str = Field(default="", max_length=300)
    descripcion: str = Field(default="", max_length=500)
    sin_tacc: Literal["todo", "opciones", "no"] = "no"          # declarado por el comercio
    vegetariano: bool = False
    vegano: bool = False
    declaracion: bool = False   # "soy responsable de este comercio y tiene al menos 6 meses de actividad"

    @field_validator("zona")
    @classmethod
    def _zona_del_pais(cls, valor: str) -> str:
        if valor not in ZONAS_COMERCIO:
            raise ValueError("elegí CABA o una provincia de la lista")
        return valor


class RevisionIn(BaseModel):
    estado: Literal["aprobado", "rechazado", "suspendido"]
    nota: str = Field(default="", max_length=300)


# ------------------------------------------------------------------ auxiliares
def tiene_comercio(db: Session, id_usuario: int) -> bool:
    return db.query(Comercio.id_comercio).filter(Comercio.id_usuario == id_usuario).first() is not None


def _dict(c: Comercio) -> dict:
    codigos = [r for r in (c.rubros or "").split(",") if r]
    return {"nombre": c.nombre, "rubros": codigos, "modalidad": c.modalidad, "zona": c.zona,
            "localidad": c.localidad, "direccion": c.direccion or "", "telefono": c.telefono or "",
            "instagram": c.instagram or "", "sitio_web": c.sitio_web or "", "descripcion": c.descripcion or "",
            "sin_tacc": c.sin_tacc, "vegetariano": bool(c.vegetariano), "vegano": bool(c.vegano),
            "declaracion": bool(c.declaracion), "estado": c.estado, "nota_revision": c.nota_revision or ""}


def _texto(valor: str, maximo: int, campo: str) -> str:
    limpio = diseno.sanitizar_mensaje(valor, maximo)
    if diseno.detectar_datos_personales(limpio):
        raise HTTPException(status_code=422, detail="No incluyas datos personales en «%s»: solo información del comercio." % campo)
    if diseno.parece_instruccion_ia(limpio):
        raise HTTPException(status_code=422, detail="«%s» no puede contener instrucciones ni órdenes: escribí solo información del comercio." % campo)
    return limpio


# Clave fija del bloqueo que serializa la creación de IDs del catálogo (cualquier número sirve, mientras sea único).
_BLOQUEO_CATALOGO = 20261126


def _bloquear_catalogo(db: Session) -> None:
    """Toma un bloqueo de PostgreSQL que dura hasta el commit/rollback de esta transacción.
    Sin él, dos aprobaciones al mismo tiempo calculaban el mismo MAX+1 y una fallaba por ID repetido."""
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _BLOQUEO_CATALOGO})


def _proximo_id(db: Session, columna) -> int:
    # MAX+1 y no la secuencia: el ETL carga IDs explícitos y la secuencia puede quedar atrasada.
    # Es seguro porque publicar_en_catalogo() toma antes _bloquear_catalogo().
    return (db.query(func.max(columna)).scalar() or 0) + 1


def publicar_en_catalogo(db: Session, c: Comercio) -> None:
    """Crea o actualiza la fila del comercio en `restaurants` (lo que consulta Foody)."""
    hoy = date.today()
    _bloquear_catalogo(db)
    fuente = db.query(Source).filter(Source.name == FUENTE).first()
    if fuente is None:
        fuente = Source(source_id=_proximo_id(db, Source.source_id), name=FUENTE, source_type="registro_comercio",
                        license="Declarado por cada comercio", update_frequency="continua", last_updated=hoy,
                        reliability="declarado", fetched_date=hoy,
                        notes="Comercios y emprendimientos que se registraron en GastronomIA. Datos declarados por el propio comercio.")
        db.add(fuente)
        db.flush()
    web = c.sitio_web or ("https://www.instagram.com/%s" % c.instagram if c.instagram else None)
    provincia, region, zona = _ubicacion(c.zona)
    valores = dict(
        name=c.nombre, province=provincia, city=c.localidad, neighborhood=c.localidad,
        region=region, zone_macro=zona,
        address=(c.direccion or None) if c.modalidad in ("local", "ambos") else None,
        cuisine_type=diseno.cocinas_para([r for r in (c.rubros or "").split(",") if r]),
        category="emprendimiento_online" if c.modalidad == "online" else "restaurant",
        phone=c.telefono or None, website=web, social_media=({"instagram": c.instagram} if c.instagram else None),
        source_id=fuente.source_id, source_type="registro_comercio", confidence_level="declarado_comercio",
        data_date=hoy, fetched_date=hoy, is_active=True,
    )
    r = db.get(Restaurant, c.id_restaurante) if c.id_restaurante else None
    if r is None:
        r = Restaurant(restaurant_id=_proximo_id(db, Restaurant.restaurant_id), **valores)
        db.add(r)
        db.flush()
        c.id_restaurante = r.restaurant_id
    else:
        for k, v in valores.items():
            setattr(r, k, v)
    marcas = dict(has_gluten_free_options=c.sin_tacc in ("todo", "opciones"),
                  has_vegetarian_options=bool(c.vegetariano or c.vegano), has_vegan_options=bool(c.vegano),
                  celiac_certified=False, source_id=fuente.source_id, confidence_level="declarado_comercio")
    f = db.query(RestaurantFeature).filter(RestaurantFeature.restaurant_id == r.restaurant_id).first()
    if f is None:
        db.add(RestaurantFeature(id=_proximo_id(db, RestaurantFeature.id), restaurant_id=r.restaurant_id, **marcas))
    else:
        for k, v in marcas.items():
            setattr(f, k, v)


def retirar_del_catalogo(db: Session, c: Comercio) -> None:
    if c.id_restaurante:
        r = db.get(Restaurant, c.id_restaurante)
        if r is not None:
            r.is_active = False


def _falla_bd(db: Session) -> HTTPException:
    db.rollback()
    log.exception("Error de base de datos en comercios")
    return HTTPException(status_code=503, detail="La base de datos no está disponible o falta inicializarla.")


# ------------------------------------------------------------- el dueño
@router.get("/comercio/mio")
def ver_mi_comercio(db: Session = Depends(get_db), usuario: dict = Depends(usuario_actual)):
    try:
        c = db.query(Comercio).filter(Comercio.id_usuario == usuario["uid"]).first()
        return {"comercio": _dict(c) if c else None}
    except SQLAlchemyError:
        raise _falla_bd(db)


@router.put("/comercio/mio", dependencies=[Depends(limitar_comercio)])
def guardar_mi_comercio(datos: ComercioIn, db: Session = Depends(get_db), usuario: dict = Depends(usuario_actual)):
    """Crea o actualiza el comercio de esta cuenta. Cada cuenta solo toca el suyo."""
    if not datos.declaracion:
        raise HTTPException(status_code=422, detail="Tenés que declarar que sos responsable del comercio y que tiene al menos 6 meses de actividad.")
    if not diseno.rubros_validos(datos.rubros):
        raise HTTPException(status_code=422, detail="Elegí entre 1 y 3 rubros de la lista.")
    telefono = datos.telefono.strip()
    if telefono and not _TELEFONO.match(telefono):
        raise HTTPException(status_code=422, detail="El teléfono del comercio no es válido.")
    instagram = datos.instagram.strip()
    if instagram and not _INSTAGRAM.match(instagram):
        raise HTTPException(status_code=422, detail="El usuario de Instagram no es válido (letras, números, punto y guion bajo).")
    web = datos.sitio_web.strip()
    if web and not diseno.web_valida(web):
        raise HTTPException(status_code=422, detail="El sitio web tiene que empezar con http:// o https://")
    falta = diseno.validar_presencia(datos.modalidad, datos.direccion, instagram, web)
    if falta:
        raise HTTPException(status_code=422, detail=falta)
    campos = {
        "nombre": _texto(datos.nombre, 120, "nombre"), "localidad": _texto(datos.localidad, 80, "barrio o localidad"),
        "direccion": _texto(datos.direccion, 200, "dirección"), "descripcion": _texto(datos.descripcion, 500, "descripción"),
        "telefono": telefono, "instagram": instagram.lstrip("@"), "sitio_web": web, "rubros": ",".join(datos.rubros),
        "modalidad": datos.modalidad, "zona": datos.zona, "sin_tacc": datos.sin_tacc,
        "vegetariano": datos.vegetariano, "vegano": datos.vegano, "declaracion": True,
    }
    if len(campos["nombre"]) < 2 or len(campos["localidad"]) < 2:
        raise HTTPException(status_code=422, detail="Completá el nombre del comercio y el barrio o localidad.")
    try:
        c = db.query(Comercio).filter(Comercio.id_usuario == usuario["uid"]).first()
        if c is not None and c.estado == "suspendido":
            raise HTTPException(status_code=403, detail="Tu comercio está suspendido. Contactá a GastronomIA.")
        estado = "aprobado" if _autoaprobar() else "pendiente"   # toda modificación se vuelve a revisar
        if c is None:
            c = Comercio(id_usuario=usuario["uid"], estado=estado, **campos)
            db.add(c)
            db.flush()
        else:
            for k, v in campos.items():
                setattr(c, k, v)
            c.estado, c.nota_revision = estado, None
        if estado == "aprobado":
            publicar_en_catalogo(db, c)
        else:
            retirar_del_catalogo(db, c)
        db.commit()
        db.refresh(c)
        return {"comercio": _dict(c)}
    except SQLAlchemyError:
        raise _falla_bd(db)


# ------------------------------------------------------ administración
@router.get("/admin/comercios")
def admin_listar(estado: Literal["pendiente", "aprobado", "rechazado", "suspendido"] = "pendiente",
                 db: Session = Depends(get_db), _admin: dict = Depends(exigir_admin)):
    try:
        filas = (db.query(Comercio, Usuario.email).join(Usuario, Usuario.id_usuario == Comercio.id_usuario)
                 .filter(Comercio.estado == estado).order_by(Comercio.id_comercio.desc()).limit(100).all())
        return {"comercios": [{"id_comercio": c.id_comercio, "email_dueno": email, **_dict(c)} for c, email in filas]}
    except SQLAlchemyError:
        raise _falla_bd(db)


@router.post("/admin/comercios/{id_comercio}/estado", dependencies=[Depends(limitar_comercio)])
def admin_revisar(id_comercio: int, datos: RevisionIn, db: Session = Depends(get_db), _admin: dict = Depends(exigir_admin)):
    nota = diseno.sanitizar_mensaje(datos.nota, 300)
    try:
        c = db.get(Comercio, id_comercio)
        if c is None:
            raise HTTPException(status_code=404, detail="Comercio no encontrado.")
        c.estado, c.nota_revision, c.fecha_revision = datos.estado, nota or None, datetime.utcnow()
        if datos.estado == "aprobado":
            publicar_en_catalogo(db, c)
        else:
            retirar_del_catalogo(db, c)
        db.commit()
        return {"id_comercio": c.id_comercio, "estado": c.estado}
    except SQLAlchemyError:
        raise _falla_bd(db)
