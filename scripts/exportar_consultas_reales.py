"""
Extrae las consultas que la gente le escribió a Foody para evaluar y entrenar la red neuronal propia.

    python scripts/exportar_consultas_reales.py                 # base de backend/.env (local)
    python scripts/exportar_consultas_reales.py --env neon.env  # otra base (archivo con DATABASE_URL=...)

Privacidad (ver docs/seguridad_ciberseguridad.md):
  - Solo se leen los mensajes de la PERSONA, nunca usuarios, emails ni identificadores de sesión.
  - Se borran emails, teléfonos, links y números largos (documentos, tarjetas) antes de guardar.
  - Se descartan frases muy largas (pueden traer datos personales o texto pegado) y duplicadas.
  - El resultado (data/consultas_reales.csv) queda fuera de Git (.gitignore): no se publica.
  - La URL de la base nunca se imprime.
"""
import csv
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
SALIDA = RAIZ / "data" / "consultas_reales.csv"
MAX_LARGO = 200

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_URL = re.compile(r"(?:https?://|www\.)\S+", re.I)
_NUMERO_LARGO = re.compile(r"\+?\d[\d\s().\-]{6,}\d")


_CONTEXTO_APP = re.compile(r"\s*\[(?:Perfil del usuario|Filtros activos)[^\]]*\]")


def anonimizar(texto: str) -> str:
    t = _CONTEXTO_APP.sub("", texto)          # contexto que agrega la app, no lo escribió la persona
    t = _EMAIL.sub("[email]", t)
    t = _URL.sub("[link]", t)
    t = _NUMERO_LARGO.sub("[numero]", t)
    return re.sub(r"\s+", " ", t).strip()


def leer_env(ruta: Path) -> str:
    for linea in ruta.read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if linea.startswith("DATABASE_URL="):
            return linea.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("No encontré DATABASE_URL en %s" % ruta.name)


def main():
    global SALIDA
    if "--env" in sys.argv:
        archivo = RAIZ / sys.argv[sys.argv.index("--env") + 1]
        os.environ["DATABASE_URL"] = leer_env(archivo)
        SALIDA = SALIDA.with_name("consultas_reales_%s.csv" % archivo.stem)     # p. ej. consultas_reales_neon.csv
    else:
        from dotenv import load_dotenv
        load_dotenv(RAIZ / "backend" / ".env")
    import json

    import sqlalchemy as sa
    from database import engine

    frases = []
    with engine.connect() as c:
        frases += [r[0] for r in c.execute(sa.text("SELECT contenido FROM mensajes WHERE rol = 'usuario'"))]
        for (historial,) in c.execute(sa.text("SELECT historial FROM sesiones_gemini")):
            turnos = json.loads(historial) if isinstance(historial, str) else (historial or [])
            frases += [t.get("text", "") for t in turnos if isinstance(t, dict) and t.get("role") == "user"]

    vistas, salida = set(), []
    for f in frases:
        f = anonimizar(str(f or ""))
        clave = f.lower()
        if not f or len(f) > MAX_LARGO or clave in vistas:
            continue
        vistas.add(clave)
        salida.append(f)

    SALIDA.parent.mkdir(exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["frase"])
        w.writerows([f] for f in salida)
    print("Mensajes leídos: %d | frases únicas guardadas: %d -> %s" % (len(frases), len(salida), SALIDA.relative_to(RAIZ)))


if __name__ == "__main__":
    main()
