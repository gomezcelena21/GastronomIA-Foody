"""
GastronomIA - Control de la cuota de Gemini (plan gratuito).

Por qué se "moría" a las pocas consultas: el límite del plan gratis es de PEDIDOS por minuto
(y por día), no de tokens. Cada mensaje del chat usa como mínimo 2 pedidos a Gemini (la pregunta
+ el resultado de la búsqueda) y hasta 6 si la IA encadena herramientas. Con ~5 pedidos por minuto
alcanzan 2 o 3 consultas. Este módulo:
  - espera un rato (en vez de fallar) cuando se llenó el minuto;
  - lee cuánto hay que esperar del error 429 de Google;
  - distingue límite por minuto de límite diario;
  - avisa con CuotaAgotada para que el chat responda igual con la base de datos.
Es código puro (sin Gemini ni FastAPI): se prueba en tests/test_cuota.py.
"""

import re
import threading
import time
from collections import deque
from typing import Callable, Optional, Tuple


class CuotaAgotada(Exception):
    def __init__(self, segundos: float = 60.0, diaria: bool = False):
        super().__init__("Cuota de Gemini agotada (reintentar en %.0f s)" % segundos)
        self.segundos = segundos
        self.diaria = diaria


class ControlCuota:
    """Ventana deslizante de 60 s: nunca manda más de `rpm` pedidos por minuto."""

    def __init__(self, rpm: int = 4, max_espera: float = 20.0,
                 reloj: Callable[[], float] = time.monotonic,
                 dormir: Callable[[float], None] = time.sleep):
        self.rpm = max(1, int(rpm))
        self.max_espera = float(max_espera)
        self._reloj, self._dormir = reloj, dormir
        self._envios: deque = deque()
        self._bloqueado_hasta = 0.0
        self._diaria = False
        self._lock = threading.Lock()

    def bloquear_por(self, segundos: float, diaria: bool = False) -> None:
        """Después de un 429: no mandar nada durante `segundos`."""
        with self._lock:
            self._bloqueado_hasta = max(self._bloqueado_hasta, self._reloj() + max(0.0, segundos))
            self._diaria = diaria

    def reservar(self) -> float:
        """Bloquea hasta que haya un lugar libre. Devuelve los segundos esperados.
        Si habría que esperar más de `max_espera`, lanza CuotaAgotada."""
        esperado = 0.0
        while True:
            with self._lock:
                ahora = self._reloj()
                while self._envios and ahora - self._envios[0] >= 60.0:
                    self._envios.popleft()
                espera = 0.0
                if self._bloqueado_hasta > ahora:
                    espera = self._bloqueado_hasta - ahora
                elif len(self._envios) >= self.rpm:
                    espera = 60.0 - (ahora - self._envios[0])
                if espera <= 0:
                    self._envios.append(ahora)
                    self._diaria = False
                    return esperado
                if espera > self.max_espera:
                    raise CuotaAgotada(espera, diaria=self._diaria)
            self._dormir(espera + 0.05)
            esperado += espera


_RE_TIEMPO = re.compile(r"retry in ((?:\d+h)?(?:\d+m)?\d+(?:\.\d+)?s)", re.I)
_RE_DELAY = re.compile(r"retry_?delay\W+(?:seconds\W+)?(\d+(?:\.\d+)?)", re.I)


def _a_segundos(texto: str) -> float:
    total = 0.0
    for valor, unidad in re.findall(r"(\d+(?:\.\d+)?)([hms])", texto):
        total += float(valor) * {"h": 3600, "m": 60, "s": 1}[unidad]
    return total


def clasificar_error(mensaje: str) -> Tuple[str, Optional[float]]:
    """('otro'|'rpm'|'diaria', segundos_a_esperar) a partir del texto del error de Gemini."""
    m = mensaje or ""
    bajo = m.lower()
    if not ("429" in m or "resource_exhausted" in bajo or "quota" in bajo or "rate limit" in bajo):
        return "otro", None
    espera = None
    t = _RE_TIEMPO.search(m)
    if t:
        espera = _a_segundos(t.group(1))
    else:
        d = _RE_DELAY.search(m)
        if d:
            espera = float(d.group(1))
    compacto = re.sub(r"[^a-z]", "", bajo)
    if "perday" in compacto or "requestsperday" in compacto or (espera is not None and espera >= 600):
        return "diaria", espera
    return "rpm", espera


def enviar_con_cuota(control: ControlCuota, enviar: Callable[[], object], registrar: Callable[[str], None] = lambda m: None):
    """Hace UN pedido a Gemini (`enviar()`) respetando la cuota: espera si el minuto está lleno y,
    ante un 429, espera lo que Google indique y reintenta una vez. Si no se puede, lanza CuotaAgotada."""
    for intento in range(2):
        control.reservar()                              # puede lanzar CuotaAgotada
        try:
            return enviar()
        except CuotaAgotada:
            raise
        except Exception as e:
            tipo, espera = clasificar_error(str(e))
            if tipo == "otro":
                raise
            registrar("Gemini devolvió 429 (%s), espera sugerida: %s" % (tipo, espera))
            if tipo == "diaria":
                control.bloquear_por(espera or 3600, diaria=True)
                raise CuotaAgotada(espera or 3600, diaria=True)
            control.bloquear_por(espera or 15)
            if intento == 1:
                raise CuotaAgotada(espera or 15)
