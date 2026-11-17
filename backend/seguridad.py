"""
GastronomIA - Seguridad de la API: quién es el usuario que hace el pedido.
usuario_actual lo exigen el chat, el historial y todo lo que toca datos de una persona.
La identidad sale SIEMPRE del token firmado por el servidor, nunca de lo que mande el navegador.
"""
import os
from typing import Optional

from fastapi import Header, HTTPException

import sesion


def secreto() -> str:
    return os.getenv("SESSION_SECRET", "")


def usuario_actual(authorization: Optional[str] = Header(default=None)) -> dict:
    """Exige 'Authorization: Bearer <token de sesión>' y devuelve {sub, uid, email, nombre}."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Iniciá sesión para usar el chat.")
    try:
        datos = sesion.verificar_sesion(authorization[7:].strip(), secreto())
    except sesion.SesionInvalida:
        raise HTTPException(status_code=401, detail="Tu sesión no es válida o venció. Volvé a iniciar sesión.")
    if not isinstance(datos.get("uid"), int) or not datos.get("email"):
        raise HTTPException(status_code=401, detail="Sesión incompleta. Volvé a iniciar sesión.")
    return datos


def usuario_opcional(authorization: Optional[str] = Header(default=None)) -> Optional[dict]:
    """Sin cabecera: invitado (None). Con token: debe ser válido, si no es 401."""
    if not authorization:
        return None
    return usuario_actual(authorization)
