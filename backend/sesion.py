"""
GastronomIA - Sesiones: login con Google + token de sesión firmado + tope diario por usuario.
Código puro (sin FastAPI): se prueba en tests/test_sesion.py.

Flujo: el navegador obtiene un ID token de Google -> POST /api/auth/google -> verificar_google() lo valida
(firma, vencimiento, audiencia = nuestro GOOGLE_CLIENT_ID, correo verificado) -> firmar_sesion() entrega un token
propio que vence a las SESION_HORAS horas. No se guardan contraseñas: la identidad la prueba Google.
"""

import base64
import hashlib
import hmac
import json
import threading
import time
from datetime import date, datetime
from typing import Callable, Optional

SESION_HORAS = 12
LARGO_MIN_SECRETO = 32


class SesionInvalida(Exception):
    pass


def hoy_argentina() -> date:
    """Día en hora de Argentina (el servidor puede estar en UTC)."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()
    except Exception:
        return date.today()


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def _unb64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _firma(cuerpo: str, secreto: str) -> str:
    return _b64(hmac.new(secreto.encode(), cuerpo.encode(), hashlib.sha256).digest())


def _exigir_secreto(secreto: str) -> None:
    if len(secreto or "") < LARGO_MIN_SECRETO:
        raise SesionInvalida("SESSION_SECRET falta o es demasiado corto (mínimo %d caracteres)." % LARGO_MIN_SECRETO)


def firmar_sesion(datos: dict, secreto: str, ahora: Optional[float] = None, horas: float = SESION_HORAS) -> str:
    _exigir_secreto(secreto)
    cuerpo = dict(datos)
    cuerpo["exp"] = int((time.time() if ahora is None else ahora) + horas * 3600)
    p = _b64(json.dumps(cuerpo, separators=(",", ":"), ensure_ascii=False).encode())
    return p + "." + _firma(p, secreto)


def verificar_sesion(token: str, secreto: str, ahora: Optional[float] = None) -> dict:
    _exigir_secreto(secreto)
    try:
        p, firma = token.split(".")
    except (ValueError, AttributeError):
        raise SesionInvalida("Token mal formado.")
    if not hmac.compare_digest(firma.encode(), _firma(p, secreto).encode()):
        raise SesionInvalida("Firma inválida.")
    try:
        datos = json.loads(_unb64(p))
    except Exception:
        raise SesionInvalida("Token mal formado.")
    if not isinstance(datos, dict) or datos.get("exp", 0) < (time.time() if ahora is None else ahora):
        raise SesionInvalida("La sesión venció.")
    return datos


def verificar_google(credential: str, client_id: str) -> dict:
    """Valida el ID token de Google con la librería oficial (firma, vencimiento y audiencia)."""
    if not client_id:
        raise SesionInvalida("Falta GOOGLE_CLIENT_ID en backend/.env.")
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    try:
        info = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
    except ValueError as e:
        raise SesionInvalida("Token de Google inválido.") from e
    if info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise SesionInvalida("Emisor inválido.")
    if not info.get("email_verified") or not info.get("email"):
        raise SesionInvalida("El correo de Google no está verificado.")
    return {"sub": str(info["sub"]), "email": info["email"],
            "nombre": (info.get("name") or info["email"].split("@")[0])[:100]}


class ContadorDiario:
    """Máximo de consultas por usuario y por día.

    Si se le pasa `almacen` (persistencia.AlmacenCuotas), el conteo se guarda en
    PostgreSQL y lo comparten todos los workers. Si la base falla, vuelve solo
    al contador en memoria, así el chat nunca deja de responder.
    """

    def __init__(self, maximo: int = 10, hoy: Callable[[], date] = hoy_argentina,
                 almacen=None, ambito: str = "general"):
        self.maximo = max(1, int(maximo))
        self._hoy = hoy
        self._dia = None
        self._usos: dict = {}
        self._lock = threading.Lock()
        self.almacen = almacen
        self.ambito = ambito

    def _rotar(self) -> None:
        h = self._hoy()
        if h != self._dia:
            self._dia, self._usos = h, {}

    def _consumir_memoria(self, clave: str) -> bool:
        with self._lock:
            self._rotar()
            if self._usos.get(clave, 0) >= self.maximo:
                return False
            self._usos[clave] = self._usos.get(clave, 0) + 1
            return True

    def _restantes_memoria(self, clave: str) -> int:
        with self._lock:
            self._rotar()
            return max(0, self.maximo - self._usos.get(clave, 0))

    def consumir(self, clave: str) -> bool:
        if self.almacen is not None:
            resultado = self.almacen.consumir(self.ambito, clave, self.maximo, self._hoy())
            if resultado is not None:
                return resultado
        return self._consumir_memoria(clave)

    def restantes(self, clave: str) -> int:
        if self.almacen is not None:
            resultado = self.almacen.restantes(self.ambito, clave, self.maximo, self._hoy())
            if resultado is not None:
                return resultado
        return self._restantes_memoria(clave)
