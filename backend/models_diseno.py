"""
GastronomIA - Modelo de datos del diseño (Sección 5, diagrama ER / clases).

Correspondencia con el PDF "Diseño del sistema":
  Establecimiento              -> tabla existente `restaurants`   (models.Restaurant)
  Fuente                       -> tabla existente `sources`       (models.Source)
  Usuario                      -> usuarios
  RestriccionAlimentaria       -> restricciones_alimentarias
  UsuarioRestriccion           -> usuario_restriccion
  EstablecimientoRestriccion   -> establecimiento_restriccion   (con nivel_informacion)
  EstablecimientoFuente        -> establecimiento_fuente
  Preferencia                  -> preferencias
  HistorialPreferencia         -> historial_preferencias
  Conversacion / Mensaje       -> conversaciones / mensajes
  Recomendacion                -> recomendaciones
  Resena / Valoracion          -> resenas / valoraciones

Las tablas nuevas se crean solas al iniciar el backend (create_all solo crea
las que faltan; no toca `restaurants` ni `sources`).
"""

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, PrimaryKeyConstraint, String, Text,
)
from sqlalchemy.sql import func

from database import Base
import models  # noqa: F401  (registra restaurants / sources en el mismo metadata)


class Usuario(Base):
    __tablename__ = "usuarios"
    id_usuario = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(200), nullable=False, unique=True, index=True)
    fecha_registro = Column(DateTime, server_default=func.now())


class RestriccionAlimentaria(Base):
    __tablename__ = "restricciones_alimentarias"
    id_restriccion = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text)


class UsuarioRestriccion(Base):
    __tablename__ = "usuario_restriccion"
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    id_restriccion = Column(Integer, ForeignKey("restricciones_alimentarias.id_restriccion"), nullable=False)
    __table_args__ = (PrimaryKeyConstraint("id_usuario", "id_restriccion"),)


class EstablecimientoRestriccion(Base):
    """Una característica alimentaria nunca es una certificación absoluta:
    `nivel_informacion` indica qué tan confiable es el dato."""
    __tablename__ = "establecimiento_restriccion"
    id_establecimiento = Column(Integer, ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), nullable=False)
    id_restriccion = Column(Integer, ForeignKey("restricciones_alimentarias.id_restriccion"), nullable=False)
    nivel_informacion = Column(String(30), nullable=False, default="no_verificado")  # declarado | inferido | no_verificado
    __table_args__ = (PrimaryKeyConstraint("id_establecimiento", "id_restriccion"),)


class EstablecimientoFuente(Base):
    __tablename__ = "establecimiento_fuente"
    id_establecimiento = Column(Integer, ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), nullable=False)
    id_fuente = Column(Integer, ForeignKey("sources.source_id"), nullable=False)
    identificador_origen = Column(String(200))
    __table_args__ = (PrimaryKeyConstraint("id_establecimiento", "id_fuente"),)


class Preferencia(Base):
    __tablename__ = "preferencias"
    id_preferencia = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(50), nullable=False)    # presupuesto | ambiente | cocina | zona
    valor = Column(String(200), nullable=False)


class HistorialPreferencia(Base):
    __tablename__ = "historial_preferencias"
    id_historial = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False, index=True)
    datos_interaccion = Column(Text, nullable=False)
    fecha = Column(DateTime, server_default=func.now())


class Conversacion(Base):
    __tablename__ = "conversaciones"
    id_conversacion = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), index=True)
    session_key = Column(String(64), index=True)   # id de sesión que manda el frontend
    activa = Column(Boolean, default=True)
    fecha_inicio = Column(DateTime, server_default=func.now())
    fecha_ultima_actividad = Column(DateTime, server_default=func.now())


class Mensaje(Base):
    __tablename__ = "mensajes"
    id_mensaje = Column(Integer, primary_key=True, index=True)
    id_conversacion = Column(Integer, ForeignKey("conversaciones.id_conversacion", ondelete="CASCADE"), nullable=False, index=True)
    rol = Column(String(20), nullable=False)       # usuario | asistente
    contenido = Column(Text, nullable=False)
    fecha_hora = Column(DateTime, server_default=func.now())


class Recomendacion(Base):
    __tablename__ = "recomendaciones"
    id_recomendacion = Column(Integer, primary_key=True, index=True)
    id_conversacion = Column(Integer, ForeignKey("conversaciones.id_conversacion", ondelete="CASCADE"), nullable=False, index=True)
    id_establecimiento = Column(Integer, ForeignKey("restaurants.restaurant_id"), nullable=False)
    motivo = Column(Text)
    fecha_hora = Column(DateTime, server_default=func.now())


class Resena(Base):
    __tablename__ = "resenas"
    id_resena = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"))
    id_establecimiento = Column(Integer, ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), nullable=False, index=True)
    texto_original = Column(Text, nullable=False)
    fecha = Column(DateTime, server_default=func.now())


class Valoracion(Base):
    __tablename__ = "valoraciones"
    id_valoracion = Column(Integer, primary_key=True, index=True)
    id_resena = Column(Integer, ForeignKey("resenas.id_resena", ondelete="CASCADE"), nullable=False, index=True)
    aspecto = Column(String(50), nullable=False)
    sentimiento = Column(String(20), nullable=False)
    detalle = Column(Text)


class Comercio(Base):
    """Comercio o emprendimiento (con o sin local físico) que registra su dueño con su cuenta de Google.
    Queda 'pendiente'; al aprobarse se publica en el catálogo `restaurants` y Foody empieza a recomendarlo."""
    __tablename__ = "comercios"
    id_comercio = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False, unique=True)
    nombre = Column(String(120), nullable=False)
    rubros = Column(String(200), nullable=False)         # códigos separados por coma: pasteleria,cafe
    modalidad = Column(String(10), nullable=False, default="local")   # local | online | ambos
    zona = Column(String(40), nullable=False)            # CABA | Provincia de Buenos Aires
    localidad = Column(String(80), nullable=False)       # barrio o localidad donde atiende o entrega
    direccion = Column(String(200))                      # solo si tiene local físico
    telefono = Column(String(40))
    instagram = Column(String(31))
    sitio_web = Column(String(300))
    descripcion = Column(Text)
    sin_tacc = Column(String(10), nullable=False, default="no")   # todo | opciones | no (declarado por el comercio)
    vegetariano = Column(Boolean, default=False)
    vegano = Column(Boolean, default=False)
    declaracion = Column(Boolean, nullable=False, default=False)  # declara ser el responsable y tener 6+ meses de actividad
    estado = Column(String(20), nullable=False, default="pendiente")   # pendiente | aprobado | rechazado | suspendido
    nota_revision = Column(Text)
    id_restaurante = Column(Integer)                     # fila publicada en `restaurants` (cuando está aprobado)
    fecha_alta = Column(DateTime, server_default=func.now())
    fecha_actualizacion = Column(DateTime, server_default=func.now(), onupdate=func.now())
    fecha_revision = Column(DateTime)


TABLAS_NEGOCIO = [Comercio.__table__]

TABLAS_DISENO = [
    Usuario.__table__, RestriccionAlimentaria.__table__, UsuarioRestriccion.__table__,
    EstablecimientoRestriccion.__table__, EstablecimientoFuente.__table__,
    Preferencia.__table__, HistorialPreferencia.__table__, Conversacion.__table__,
    Mensaje.__table__, Recomendacion.__table__, Resena.__table__, Valoracion.__table__,
]

RESTRICCIONES_BASE = [
    ("Vegano", "No consume productos de origen animal."),
    ("Vegetariano", "No consume carne."),
    ("Celíaco (sin TACC)", "Necesita alimentos sin gluten (sin TACC)."),
    ("Sin lactosa", "Necesita alimentos sin lactosa."),
]


def crear_tablas_diseno(engine) -> None:
    """Crea solo las tablas que faltan."""
    Base.metadata.create_all(bind=engine, tables=TABLAS_DISENO + TABLAS_NEGOCIO)


def sembrar_restricciones(db) -> None:
    """Carga las restricciones base si la tabla está vacía."""
    if db.query(RestriccionAlimentaria).count() == 0:
        for nombre, desc in RESTRICCIONES_BASE:
            db.add(RestriccionAlimentaria(nombre=nombre, descripcion=desc))
        db.commit()
