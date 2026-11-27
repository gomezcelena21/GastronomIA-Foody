"""
GastronomIA - Proveedor de IA de respaldo (cuando Gemini no tiene cuota, se cuelga o falla).

Orden en que responde Foody:
  1. Gemini (principal)
  2. Proveedor de respaldo (este módulo): Groq gratis por defecto, o cualquier servicio compatible
     con la API de OpenAI (OpenRouter, Mistral, etc.), configurable por variables de entorno.
  3. Modo sin IA: reglas + red neuronal propia (diseno.py + modelo_foody.py). Nunca falla.

Usa las MISMAS reglas (SYSTEM_PROMPT) y las MISMAS herramientas que Gemini: el modelo de respaldo
tampoco accede a la base, solo recibe lo que devuelve el backend, y su respuesta pasa por la misma
validación (orquestador.validar_respuesta_ia). Solo usa `requests`, que ya estaba instalado.

Variables de entorno:
  RESPALDO_API_KEY   clave del proveedor (sin clave, el respaldo está apagado)
  RESPALDO_URL       por defecto https://api.groq.com/openai/v1/chat/completions
  RESPALDO_MODELO    por defecto openai/gpt-oss-120b
  RESPALDO_TIMEOUT   segundos por pedido (por defecto 15)
"""

import json
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from gemini_service import GEMINI_TOOLS, SYSTEM_PROMPT, _clave_utilizable

log = logging.getLogger("gastronomia")

URL_POR_DEFECTO = "https://api.groq.com/openai/v1/chat/completions"
MODELO_POR_DEFECTO = "openai/gpt-oss-120b"
MAX_VUELTAS = 5

# Herramientas en el formato de la API de OpenAI, a partir de las de Gemini (una sola fuente de verdad).
HERRAMIENTAS = [{"type": "function", "function": f} for f in GEMINI_TOOLS[0]["function_declarations"]]


class RespaldoNoDisponible(Exception):
    """El respaldo no pudo responder: se pasa al modo sin IA."""


_pausa_hasta = 0.0              # si el proveedor dijo «429», no se le insiste hasta esta hora
_pausa_lock = threading.Lock()


def _config() -> Dict[str, Any]:
    return {
        "clave": _clave_utilizable(os.getenv("RESPALDO_API_KEY", "")),
        "url": (os.getenv("RESPALDO_URL") or URL_POR_DEFECTO).strip(),
        "modelo": (os.getenv("RESPALDO_MODELO") or MODELO_POR_DEFECTO).strip(),
        "timeout": float(os.getenv("RESPALDO_TIMEOUT", "15") or 15),
    }


def configurado() -> bool:
    c = _config()
    return bool(c["clave"]) and c["url"].startswith("https://")


def disponible() -> bool:
    return configurado() and time.time() >= _pausa_hasta


def _pausar(segundos: float) -> None:
    global _pausa_hasta
    with _pausa_lock:
        _pausa_hasta = max(_pausa_hasta, time.time() + max(5.0, min(segundos, 3600.0)))


def reiniciar() -> None:
    """Para pruebas: olvida una pausa por cuota."""
    global _pausa_hasta
    with _pausa_lock:
        _pausa_hasta = 0.0


def _pedir(c: Dict[str, Any], mensajes: List[dict]) -> dict:
    try:
        r = requests.post(
            c["url"],
            headers={"Authorization": "Bearer " + c["clave"], "Content-Type": "application/json"},
            json={"model": c["modelo"], "messages": mensajes, "tools": HERRAMIENTAS,
                  "tool_choice": "auto", "temperature": 0.3, "max_tokens": 900},
            timeout=c["timeout"],
        )
    except requests.RequestException as e:
        raise RespaldoNoDisponible("sin conexión con el respaldo: %s" % type(e).__name__) from None
    if r.status_code == 429:
        try:
            espera = float(r.headers.get("retry-after", "60"))
        except ValueError:
            espera = 60.0
        _pausar(espera)
        raise RespaldoNoDisponible("el respaldo también se quedó sin cuota (429)")
    if r.status_code in (401, 403):
        _pausar(3600)                       # clave mala: no tiene sentido reintentar enseguida
        raise RespaldoNoDisponible("clave del respaldo rechazada (%d)" % r.status_code)
    if r.status_code >= 400:
        raise RespaldoNoDisponible("el respaldo respondió %d" % r.status_code)
    try:
        return r.json()["choices"][0]["message"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise RespaldoNoDisponible("respuesta del respaldo con formato inesperado") from None


def conversar(mensaje: str, turnos: Optional[List[dict]],
              ejecutar: Callable[[str, dict], Any]) -> str:
    """Responde un mensaje con el proveedor de respaldo.

    `turnos` es el historial guardado ([{role: user|model, text}]) y `ejecutar(nombre, args)` corre una
    herramienta contra la base y devuelve lo que se le pasa al modelo. Lanza RespaldoNoDisponible si falla.
    """
    if not disponible():
        raise RespaldoNoDisponible("respaldo apagado o en pausa")
    c = _config()
    mensajes: List[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for t in (turnos or [])[-20:]:
        texto = (t or {}).get("text")
        if texto:
            mensajes.append({"role": "user" if t.get("role") == "user" else "assistant", "content": str(texto)})
    mensajes.append({"role": "user", "content": mensaje})

    for _ in range(MAX_VUELTAS):
        respuesta = _pedir(c, mensajes)
        llamadas = respuesta.get("tool_calls") or []
        if not llamadas:
            texto = (respuesta.get("content") or "").strip()
            if not texto:
                raise RespaldoNoDisponible("el respaldo no devolvió texto")
            return texto
        mensajes.append({"role": "assistant", "content": respuesta.get("content") or "",
                         "tool_calls": llamadas})
        for ll in llamadas:
            funcion = ll.get("function") or {}
            try:
                args = json.loads(funcion.get("arguments") or "{}")
                if not isinstance(args, dict):
                    args = {}
            except ValueError:
                args = {}
            try:
                resultado = ejecutar(str(funcion.get("name", "")), args)
            except Exception:  # noqa: BLE001 - un error de una herramienta no debe cortar la charla
                log.warning("Falló una herramienta pedida por el respaldo", exc_info=True)
                resultado = {"error": "No pude ejecutar esa consulta."}
            mensajes.append({"role": "tool", "tool_call_id": ll.get("id", ""),
                             "content": json.dumps(resultado, ensure_ascii=False, default=str)})
    raise RespaldoNoDisponible("el respaldo pidió demasiadas herramientas seguidas")
