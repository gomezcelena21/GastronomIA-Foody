"""
GastronomIA - Endpoints del diseño (Sección 5, tabla "Endpoints del backend").

  POST /api/chat                          -> main.py   (HU-01, 06, 08, 09, 16)
  GET  /api/establecimientos              -> main.py   (alias de /api/restaurants)
  GET  /api/establecimientos/{id}         -> main.py   (alias de /api/restaurants/{id})
  GET  /api/restricciones                 -> acá       (HU-02, 09)
  POST /api/usuarios                      -> acá       (HU-11)
  GET  /api/usuarios/{id}                 -> acá       (HU-11, 12)
  PUT  /api/usuarios/{id}                 -> acá       (HU-10, 11, 12, 14)
  GET  /api/conversaciones/{id}/mensajes  -> acá       (HU-06, 16)
  POST /api/resenas                       -> acá       (HU-13)

OJO: el diseño no incluye autenticación. Con este backend escuchando solo en
127.0.0.1 alcanza; si algún día se publica, hay que agregar login antes de
exponer /api/usuarios (devuelve el email).
"""

import json
import logging
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import diseno
from database import get_db
from models import Restaurant
from models_diseno import (
    Conversacion, HistorialPreferencia, Mensaje, Preferencia, RestriccionAlimentaria,
    Resena, Usuario, UsuarioRestriccion, Valoracion, sembrar_restricciones,
)
from orquestador import ComponenteIA
from seguridad import usuario_actual

log = logging.getLogger("gastronomia")
router = APIRouter(prefix="/api", tags=["diseño"])

_limitador_escritura = diseno.LimitadorTasa(max_eventos=30, ventana_seg=60)
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
_TIPOS_PREFERENCIA = {"presupuesto", "ambiente", "cocina", "zona"}
_ia = ComponenteIA()


def limitar_escrituras(request: Request) -> None:
    ip = request.client.host if request.client else "desconocida"
    if not _limitador_escritura.permitir(ip):
        raise HTTPException(status_code=429, detail="Demasiados pedidos. Esperá un minuto.")


def _falla_bd(db: Session, e: Exception) -> HTTPException:
    db.rollback()
    log.exception("Error de base de datos")
    return HTTPException(status_code=503, detail="La base de datos no está disponible o falta inicializarla.")


# ----------------------------------------------------------- esquemas

class PreferenciaIn(BaseModel):
    tipo: str = Field(min_length=1, max_length=50)
    valor: str = Field(min_length=1, max_length=200)


class UsuarioIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=200)
    restricciones: List[str] = Field(default_factory=list, max_length=10)
    preferencias: List[PreferenciaIn] = Field(default_factory=list, max_length=20)


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[str] = Field(default=None, min_length=3, max_length=200)
    restricciones: Optional[List[str]] = Field(default=None, max_length=10)
    preferencias: Optional[List[PreferenciaIn]] = Field(default=None, max_length=20)


class ResenaIn(BaseModel):
    id_establecimiento: int
    id_usuario: Optional[int] = None
    texto: str = Field(min_length=5, max_length=2000)


# ---------------------------------------------------------- auxiliares

def _usuario_dict(db: Session, u: Usuario) -> dict:
    restr = [r.nombre for r in db.query(RestriccionAlimentaria)
             .join(UsuarioRestriccion, UsuarioRestriccion.id_restriccion == RestriccionAlimentaria.id_restriccion)
             .filter(UsuarioRestriccion.id_usuario == u.id_usuario).all()]
    prefs = [{"tipo": p.tipo, "valor": p.valor}
             for p in db.query(Preferencia).filter(Preferencia.id_usuario == u.id_usuario).all()]
    return {"id_usuario": u.id_usuario, "nombre": u.nombre, "email": u.email,
            "fecha_registro": str(u.fecha_registro) if u.fecha_registro else None,
            "restricciones": restr, "preferencias": prefs}


def _aplicar_restricciones(db: Session, id_usuario: int, nombres: List[str]) -> None:
    sembrar_restricciones(db)
    catalogo = {diseno.normalizar(r.nombre): r for r in db.query(RestriccionAlimentaria).all()}
    elegidas = set()
    for n in nombres:
        r = catalogo.get(diseno.normalizar(n))
        if r is None:
            raise HTTPException(status_code=422, detail="Restricción desconocida: %s" % n[:50])
        elegidas.add(r.id_restriccion)
    db.query(UsuarioRestriccion).filter(UsuarioRestriccion.id_usuario == id_usuario).delete()
    for id_r in elegidas:
        db.add(UsuarioRestriccion(id_usuario=id_usuario, id_restriccion=id_r))


def _aplicar_preferencias(db: Session, id_usuario: int, prefs: List[PreferenciaIn]) -> None:
    for p in prefs:
        if p.tipo.lower() not in _TIPOS_PREFERENCIA:
            raise HTTPException(status_code=422, detail="Tipo de preferencia inválido: %s" % p.tipo[:30])
    db.query(Preferencia).filter(Preferencia.id_usuario == id_usuario).delete()
    for p in prefs:
        db.add(Preferencia(id_usuario=id_usuario, tipo=p.tipo.lower(), valor=p.valor.strip()))


def _historial(db: Session, id_usuario: int, datos: dict) -> None:
    db.add(HistorialPreferencia(id_usuario=id_usuario, datos_interaccion=json.dumps(datos, ensure_ascii=False)))


def _propio(usuario: dict, id_usuario: int) -> None:
    """Cada persona solo puede ver y modificar SU propio perfil."""
    if usuario.get("uid") != id_usuario:
        raise HTTPException(status_code=403, detail="No tenés permiso para acceder a este perfil.")


def _validar_email(email: str) -> str:
    e = email.strip().lower()
    if not _EMAIL.match(e):
        raise HTTPException(status_code=422, detail="Email inválido.")
    return e


# ----------------------------------------------------------- endpoints

@router.get("/restricciones")
def listar_restricciones(db: Session = Depends(get_db)):
    try:
        sembrar_restricciones(db)
        filas = db.query(RestriccionAlimentaria).order_by(RestriccionAlimentaria.id_restriccion).all()
        return {"restricciones": [{"id_restriccion": r.id_restriccion, "nombre": r.nombre,
                                   "descripcion": r.descripcion} for r in filas]}
    except SQLAlchemyError as e:
        raise _falla_bd(db, e)


@router.post("/usuarios", dependencies=[Depends(limitar_escrituras)])
def crear_usuario(datos: UsuarioIn, db: Session = Depends(get_db), usuario: dict = Depends(usuario_actual)):
    """Perfil propio. El usuario es la cuenta de Google que inició sesión: no se crean usuarios con
    correos ajenos ni inventados. Si ya existe, devuelve ese usuario sin modificarlo."""
    email = _validar_email(datos.email)
    if email != str(usuario.get("email", "")).lower():
        raise HTTPException(status_code=403, detail="Solo podés crear tu propio perfil, con tu cuenta de Google.")
    try:
        u = db.query(Usuario).filter(Usuario.email == email).first()
        if u is not None:
            # Ya registrado: se devuelve tal cual, sin modificar sus datos (no hay login).
            return _usuario_dict(db, u)
        u = Usuario(nombre=datos.nombre.strip(), email=email)
        db.add(u)
        db.flush()
        _aplicar_restricciones(db, u.id_usuario, datos.restricciones)
        _aplicar_preferencias(db, u.id_usuario, datos.preferencias)
        _historial(db, u.id_usuario, {"evento": "registro", "restricciones": datos.restricciones})
        db.commit()
        return _usuario_dict(db, u)
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        raise _falla_bd(db, e)


@router.get("/usuarios/{id_usuario}")
def obtener_usuario(id_usuario: int, db: Session = Depends(get_db), usuario: dict = Depends(usuario_actual)):
    _propio(usuario, id_usuario)
    try:
        u = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
        if u is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        return _usuario_dict(db, u)
    except SQLAlchemyError as e:
        raise _falla_bd(db, e)


@router.put("/usuarios/{id_usuario}", dependencies=[Depends(limitar_escrituras)])
def actualizar_usuario(id_usuario: int, datos: UsuarioUpdate, db: Session = Depends(get_db),
                       usuario: dict = Depends(usuario_actual)):
    _propio(usuario, id_usuario)
    try:
        u = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
        if u is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        cambios = {}
        if datos.nombre is not None:
            u.nombre = datos.nombre.strip()
            cambios["nombre"] = True
        if datos.email is not None:
            if _validar_email(datos.email) != u.email:
                raise HTTPException(status_code=403, detail="El correo es el de tu cuenta de Google y no se puede cambiar.")
        if datos.restricciones is not None:
            _aplicar_restricciones(db, id_usuario, datos.restricciones)
            cambios["restricciones"] = datos.restricciones
        if datos.preferencias is not None:
            _aplicar_preferencias(db, id_usuario, datos.preferencias)
            cambios["preferencias"] = [{"tipo": p.tipo, "valor": p.valor} for p in datos.preferencias]
        if cambios:
            _historial(db, id_usuario, {"evento": "actualizacion", **cambios})
        db.commit()
        return _usuario_dict(db, u)
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        raise _falla_bd(db, e)


@router.get("/conversaciones/{id_conversacion}/mensajes")
def mensajes_de_conversacion(id_conversacion: int, limit: int = Query(default=100, ge=1, le=200),
                             db: Session = Depends(get_db), usuario: dict = Depends(usuario_actual)):
    try:
        c = db.query(Conversacion).filter(Conversacion.id_conversacion == id_conversacion).first()
        if c is None or c.id_usuario != usuario.get("uid"):   # la de otra persona se trata como inexistente
            raise HTTPException(status_code=404, detail="Conversación no encontrada.")
        msgs = (db.query(Mensaje).filter(Mensaje.id_conversacion == id_conversacion)
                .order_by(Mensaje.id_mensaje).limit(limit).all())
        return {"id_conversacion": id_conversacion,
                "mensajes": [{"id_mensaje": m.id_mensaje, "rol": m.rol, "contenido": m.contenido,
                              "fecha_hora": str(m.fecha_hora) if m.fecha_hora else None} for m in msgs]}
    except SQLAlchemyError as e:
        raise _falla_bd(db, e)


@router.post("/resenas", dependencies=[Depends(limitar_escrituras)])
def crear_resena(datos: ResenaIn, db: Session = Depends(get_db), usuario: dict = Depends(usuario_actual)):
    """Guarda una reseña y extrae sus valoraciones por aspecto (HU-13)."""
    texto = diseno.sanitizar_mensaje(datos.texto, 2000)
    if len(texto) < 5:
        raise HTTPException(status_code=422, detail="La reseña es demasiado corta.")
    try:
        if not db.query(Restaurant).filter(Restaurant.restaurant_id == datos.id_establecimiento,
                                           Restaurant.is_active.is_(True)).first():
            raise HTTPException(status_code=404, detail="Establecimiento no encontrado.")
        r = Resena(id_usuario=usuario["uid"], id_establecimiento=datos.id_establecimiento, texto_original=texto)
        db.add(r)
        db.flush()
        vals = _ia.extraer_valoraciones(texto)
        for v in vals:
            db.add(Valoracion(id_resena=r.id_resena, aspecto=v["aspecto"],
                              sentimiento=v["sentimiento"], detalle=v["detalle"]))
        db.commit()
        return {"id_resena": r.id_resena, "id_establecimiento": r.id_establecimiento, "valoraciones": vals}
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        raise _falla_bd(db, e)
