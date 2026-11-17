"""
GastronomIA - Persistencia opcional en PostgreSQL.

Dos cosas que antes vivían solo en memoria (y se perdían al reiniciar o al
repartir pedidos entre varios workers):

  * cupos diarios por usuario/IP (`cuotas_diarias`);
  * historial de cada conversación con Foody (`sesiones_gemini`).

Si la base no está disponible, todo sigue funcionando con el contador en
memoria de `sesion.ContadorDiario`. La persistencia es una mejora, no un
requisito para arrancar la API.
"""

import json
import logging
import threading
import time
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import text

log = logging.getLogger("gastronomia")

_DDL = (
    """
    CREATE TABLE IF NOT EXISTS cuotas_diarias (
        dia        DATE        NOT NULL,
        ambito     VARCHAR(40) NOT NULL,
        clave      VARCHAR(200) NOT NULL,
        usos       INTEGER     NOT NULL DEFAULT 0,
        actualizado TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (dia, ambito, clave)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_cuotas_diarias_dia ON cuotas_diarias (dia)",
    """
    CREATE TABLE IF NOT EXISTS sesiones_gemini (
        session_id VARCHAR(80) PRIMARY KEY,
        historial  JSONB       NOT NULL DEFAULT '[]'::jsonb,
        actualizado TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
)

# Si la base no responde, no se reintenta en cada pedido: se espera un rato.
_REINTENTO_SEG = 60.0


class _BaseAlmacen:
    def __init__(self, engine):
        self.engine = engine
        self._tablas_ok = False
        self._proximo_intento = 0.0
        self._lock = threading.Lock()

    def _preparar(self) -> bool:
        """Crea las tablas una vez (con reintentos espaciados si la base falla)."""
        if self._tablas_ok:
            return True
        ahora = time.monotonic()
        with self._lock:
            if self._tablas_ok:
                return True
            if ahora < self._proximo_intento:
                return False
            try:
                with self.engine.begin() as conn:
                    for sql in _DDL:
                        conn.exec_driver_sql(sql)
                    # Limpieza barata: los cupos de hace más de 60 días no se usan.
                    conn.execute(
                        text("DELETE FROM cuotas_diarias WHERE dia < :limite"),
                        {"limite": date.today() - timedelta(days=60)},
                    )
                    conn.execute(
                        text("DELETE FROM sesiones_gemini WHERE actualizado < NOW() - INTERVAL '30 days'")
                    )
                self._tablas_ok = True
                return True
            except Exception:
                self._proximo_intento = time.monotonic() + _REINTENTO_SEG
                log.warning(
                    "Persistencia no disponible; se usan cupos/sesiones en memoria",
                    exc_info=True,
                )
                return False


class AlmacenCuotas(_BaseAlmacen):
    """Contador diario compartido por todos los workers del backend."""

    def consumir(self, ambito: str, clave: str, maximo: int, dia: Optional[date] = None) -> Optional[bool]:
        """True si se consumió un uso; False si ya se agotó; None si no hay base.

        El INSERT ... ON CONFLICT ... WHERE usos < maximo es atómico: dos pedidos
        simultáneos no pueden pasarse del límite.
        """
        if not self._preparar():
            return None
        dia = dia or date.today()
        try:
            with self.engine.begin() as conn:
                fila = conn.execute(
                    text(
                        """
                        INSERT INTO cuotas_diarias (dia, ambito, clave, usos)
                        VALUES (:dia, :ambito, :clave, 1)
                        ON CONFLICT (dia, ambito, clave) DO UPDATE
                        SET usos = cuotas_diarias.usos + 1,
                            actualizado = NOW()
                        WHERE cuotas_diarias.usos < :maximo
                        RETURNING usos
                        """
                    ),
                    {"dia": dia, "ambito": ambito, "clave": clave, "maximo": max(1, int(maximo))},
                ).fetchone()
                return fila is not None
        except Exception:
            log.warning("No se pudo consumir el cupo en la base; se usa memoria", exc_info=True)
            return None

    def restantes(self, ambito: str, clave: str, maximo: int, dia: Optional[date] = None) -> Optional[int]:
        if not self._preparar():
            return None
        dia = dia or date.today()
        try:
            with self.engine.connect() as conn:
                usos = conn.execute(
                    text(
                        "SELECT usos FROM cuotas_diarias "
                        "WHERE dia = :dia AND ambito = :ambito AND clave = :clave"
                    ),
                    {"dia": dia, "ambito": ambito, "clave": clave},
                ).scalar()
            return max(0, int(maximo) - int(usos or 0))
        except Exception:
            log.warning("No se pudo leer el cupo de la base; se usa memoria", exc_info=True)
            return None


class AlmacenSesiones(_BaseAlmacen):
    """Historial de conversación (texto) por session_id.

    El objeto Chat del SDK no se puede guardar en la base: se guardan los turnos
    (usuario/asistente) y se reconstruye el chat al volver a entrar. Así, un
    reinicio del backend o un segundo worker no borran el contexto.
    """

    MAX_TURNOS = 40

    def cargar(self, session_id: str) -> List[dict]:
        if not self._preparar():
            return []
        try:
            with self.engine.connect() as conn:
                valor = conn.execute(
                    text("SELECT historial FROM sesiones_gemini WHERE session_id = :sid"),
                    {"sid": session_id},
                ).scalar()
            if isinstance(valor, str):
                valor = json.loads(valor)
            return [t for t in (valor or []) if isinstance(t, dict) and t.get("text")]
        except Exception:
            log.warning("No se pudo cargar la sesión %s de la base", session_id, exc_info=True)
            return []

    def guardar(self, session_id: str, historial: List[dict]) -> None:
        if not self._preparar():
            return
        recortado = [
            {"role": "user" if t.get("role") == "user" else "model", "text": str(t.get("text", ""))[:4000]}
            for t in (historial or []) if t.get("text")
        ][-self.MAX_TURNOS:]
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO sesiones_gemini (session_id, historial)
                        VALUES (:sid, CAST(:historial AS JSONB))
                        ON CONFLICT (session_id) DO UPDATE
                        SET historial = EXCLUDED.historial, actualizado = NOW()
                        """
                    ),
                    {"sid": session_id, "historial": json.dumps(recortado, ensure_ascii=False)},
                )
        except Exception:
            log.warning("No se pudo guardar la sesión %s en la base", session_id, exc_info=True)

    def borrar(self, session_id: str) -> None:
        if not self._preparar():
            return
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM sesiones_gemini WHERE session_id = :sid"),
                    {"sid": session_id},
                )
        except Exception:
            log.warning("No se pudo borrar la sesión %s de la base", session_id, exc_info=True)
