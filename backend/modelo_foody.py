"""
GastronomIA - Red neuronal propia de Foody (sin Gemini, sin costo, sin dependencias).

Qué hace: lee la consulta y estima qué TIPO DE COMIDA, qué RESTRICCIÓN ALIMENTARIA y qué PRECIO pide, y
qué INTENCIÓN tiene (saludar, agradecer, preguntar qué es algo, contar otra restricción, opinar...), aunque
tenga errores de tipeo («pizeria», «sin tak», «begano») o use palabras que las reglas no conocen
(«pastas», «ceviche», «libre de gluten»). La zona la siguen resolviendo las reglas de diseno.py.

Cómo es la red (perceptrón multicapa, clasificación multietiqueta):
  texto -> rasgos (palabras, pares de palabras y trozos de 2 a 4 letras, «hashing» a DIM posiciones)
        -> capa oculta (ReLU) -> una salida sigmoide por etiqueta (probabilidad 0..1)

Se entrena aparte con `python scripts/entrenar_modelo_foody.py` (usa numpy) y los pesos quedan en
`modelo_foody.json`. Acá solo se hace la inferencia, en Python puro: el servidor gratis de Render
no necesita numpy ni scikit-learn y el modelo pesa unos cientos de KB.

Seguridad: la red solo AGREGA lo que entendió; nunca quita una restricción que detectaron las reglas.
Si el archivo de pesos falta o está dañado, devuelve vacío y Foody sigue funcionando con reglas.
Se puede apagar con la variable de entorno FOODY_MODELO=off.
"""

import base64
import json
import math
import os
import re
import threading
import unicodedata
import zlib
from array import array
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set

RUTA_PESOS = Path(__file__).with_name("modelo_foody.json")
DIM = 4096            # posiciones del «hashing» de rasgos
UMBRAL = 0.65         # probabilidad mínima para aceptar una etiqueta (prioriza no inventar)

RESTRICCIONES = ("sin_tacc", "vegano", "vegetariano")
COCINAS = ("pizzeria", "italiana", "hamburguesa", "japonesa", "asiatica", "china", "parrilla", "cafe",
           "mexicana", "peruana", "sandwicheria", "comida_rapida", "pasteleria", "panaderia", "heladeria",
           "empanadas", "comida_casera")
PRECIOS = ("precio_bajo", "precio_alto")
# Qué quiere hacer la persona además de (o en vez de) buscar
INTENCIONES = ("saludo", "gracias", "despedida", "ayuda", "pregunta_que_es", "otra_restriccion", "opinion",
               "fuera_de_tema")
ETIQUETAS = RESTRICCIONES + COCINAS + PRECIOS + INTENCIONES


def normalizar(texto) -> str:
    """Minúsculas, sin tildes y con espacios simples (igual que diseno.normalizar)."""
    if texto is None:
        return ""
    t = unicodedata.normalize("NFD", str(texto))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t.lower()).strip()


def rasgos(texto) -> Dict[int, float]:
    """Texto -> {posición: valor}. Lo usan igual el entrenamiento y la inferencia."""
    palabras = re.findall(r"[a-z0-9]+", normalizar(texto))
    claves: Set[str] = set()
    for p in palabras:
        claves.add("w:" + p)
        b = "<" + p + ">"
        for k in (2, 3, 4):
            for i in range(len(b) - k + 1):
                claves.add("c%d:%s" % (k, b[i:i + k]))
    for a, b in zip(palabras, palabras[1:]):
        claves.add("b:%s_%s" % (a, b))
    if not claves:
        return {}
    pos: Dict[int, float] = {}
    for c in claves:
        i = zlib.crc32(c.encode("utf-8")) % DIM
        pos[i] = pos.get(i, 0.0) + 1.0
    norma = math.sqrt(sum(v * v for v in pos.values()))
    return {i: v / norma for i, v in pos.items()}


class _Red:
    def __init__(self, datos: dict):
        if datos.get("dim") != DIM or tuple(datos.get("etiquetas", ())) != ETIQUETAS:
            raise ValueError("pesos incompatibles con esta versión del modelo")
        self.oculta = int(datos["oculta"])
        self.w1 = array("b", base64.b64decode(datos["w1"]))       # DIM x oculta, int8
        if len(self.w1) != DIM * self.oculta:
            raise ValueError("tamaño de w1 incorrecto")
        self.s1 = [float(x) for x in datos["s1"]]                  # escala por neurona oculta
        self.b1 = [float(x) for x in datos["b1"]]
        self.w2 = [[float(x) for x in fila] for fila in datos["w2"]]  # oculta x etiquetas
        self.b2 = [float(x) for x in datos["b2"]]
        self.umbral = float(datos.get("umbral", UMBRAL))
        self.version = datos.get("version", "?")

    def probabilidades(self, texto) -> Dict[str, float]:
        x = rasgos(texto)
        if not x:
            return {e: 0.0 for e in ETIQUETAS}
        H = self.oculta
        acum = [0.0] * H
        w1 = self.w1
        for i, v in x.items():
            base = i * H
            for j in range(H):
                acum[j] += w1[base + j] * v
        h = [max(0.0, self.b1[j] + self.s1[j] * acum[j]) for j in range(H)]
        salida = {}
        for k, e in enumerate(ETIQUETAS):
            z = self.b2[k] + sum(h[j] * self.w2[j][k] for j in range(H) if h[j])
            salida[e] = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))
        return salida


_red: Optional[_Red] = None
_cargada = False
_candado = threading.Lock()


def activo() -> bool:
    return os.getenv("FOODY_MODELO", "on").strip().lower() not in ("off", "0", "no", "false")


def _cargar() -> Optional[_Red]:
    global _red, _cargada
    if not _cargada:
        with _candado:
            if not _cargada:
                try:
                    _red = _Red(json.loads(RUTA_PESOS.read_text(encoding="utf-8")))
                except Exception:      # sin pesos o pesos dañados: Foody sigue con reglas
                    _red = None
                _cargada = True
    return _red


def disponible() -> bool:
    return activo() and _cargar() is not None


def probabilidades(texto) -> Dict[str, float]:
    """Probabilidad de cada etiqueta; vacío si el modelo está apagado o no hay pesos."""
    if not activo():
        return {}
    red = _cargar()
    clave = normalizar(texto)
    if red is None or not clave:
        return {}
    return dict(_calcular(red, clave))


@lru_cache(maxsize=4096)
def _calcular(red: "_Red", clave: str):
    """Misma frase, mismo resultado: se recuerda (el historial se reinterpreta en cada mensaje)."""
    return tuple(red.probabilidades(clave).items())


def predecir(texto) -> Dict[str, List[str]]:
    """Etiquetas que superan el umbral, por grupo: restricciones, cocinas, precio e intenciones."""
    probs = probabilidades(texto)
    umbral = _red.umbral if _red is not None else UMBRAL
    elegidas = [e for e in ETIQUETAS if probs.get(e, 0.0) >= umbral]
    return {"restricciones": [e for e in elegidas if e in RESTRICCIONES],
            "cocinas": [e for e in elegidas if e in COCINAS],
            "precio": [e for e in elegidas if e in PRECIOS],
            "intenciones": [e for e in elegidas if e in INTENCIONES]}
