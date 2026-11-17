#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICACIÓN PREVIA AL DESPLIEGUE - correla en tu PC ANTES de subir a GitHub y de crear los servicios.

Comprueba lo que más seguido rompe un despliegue: estructura del proyecto, finales de línea del script de arranque,
dependencias que faltan en requirements.lock, claves o archivos .env en Git, variables de entorno mal cargadas y que
las pruebas pasen. NUNCA imprime el valor de una clave: solo el nombre y si está bien o no.

    python scripts\\verificar_despliegue.py
    python scripts\\verificar_despliegue.py --env render.env     # variables que vas a pegar en Render (un KEY=VALOR por línea)
    python scripts\\verificar_despliegue.py --sin-pruebas

Estados: OK = bien · AVISO = revisalo · FALTA = arreglalo antes de desplegar (el script termina con código 1).
"""
import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent.parent
EXTENSIONES_TEXTO = {".py", ".md", ".txt", ".yml", ".yaml", ".json", ".ts", ".tsx", ".js", ".html", ".css", ".sh", ".bat",
                     ".toml", ".sql", ".cfg", ".ini", ".example", ".lock"}
OMITIR = {".git", "node_modules", "dist", "__pycache__", ".venv", "venv", "test-results", "playwright-report"}
RE_CLAVE_GEMINI = re.compile(r"AIza[0-9A-Za-z_\-]{30,}")
PLACEHOLDERS = ("pega", "tu_clave", "tu-clave", "xxxx", "completar", "changeme", "cambiar", "ejemplo", "example")


def _con_placeholder(valor: str) -> bool:
    v = (valor or "").lower()
    return any(p in v for p in PLACEHOLDERS)


# ------------------------------------------------------------------ chequeos (devuelven [(estado, nombre, detalle)])
def chequear_estructura(raiz: Path):
    esperados = ["Dockerfile", "deploy/entrypoint.sh", "backend/requirements.lock", "backend/main.py", "database/schema.sql",
                 "data/dataset_unificado_CABA_GBA.csv", "frontend/package.json", "frontend/package-lock.json", "frontend/vercel.json",
                 "scripts/cargar_base_nube.py", ".gitignore"]
    faltan = [e for e in esperados if not (raiz / e).exists()]
    if faltan:
        return [("FALTA", "Estructura del proyecto", "no encuentro: " + ", ".join(faltan) + ". El Dockerfile tiene que estar en la raíz del repositorio.")]
    return [("OK", "Estructura del proyecto", "Dockerfile en la raíz, backend, frontend, base y scripts presentes")]


def chequear_finales_de_linea(raiz: Path):
    malos = []
    for ruta in [raiz / "deploy" / "entrypoint.sh", raiz / "Dockerfile", raiz / "docker-compose.yml"]:
        if ruta.exists() and b"\r\n" in ruta.read_bytes():
            malos.append(ruta.name)
    if malos:
        return [("FALTA", "Finales de línea (LF)", "tienen CRLF de Windows: %s. Abrilos en el editor y guardá con LF, o corré: git add --renormalize ." % ", ".join(malos))]
    ok = [("OK", "Finales de línea (LF)", "entrypoint.sh, Dockerfile y docker-compose.yml usan LF")]
    if not (raiz / ".gitattributes").exists():
        ok.append(("AVISO", ".gitattributes", "no existe: ayuda a que Git no cambie los finales de línea de los scripts"))
    return ok


def chequear_dependencias(raiz: Path):
    try:
        std = set(sys.stdlib_module_names)
        locales = {p.stem for p in (raiz / "backend").glob("*.py")}
        usados = set()
        for p in (raiz / "backend").glob("*.py"):
            for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                if isinstance(n, ast.Import):
                    usados |= {a.name.split(".")[0] for a in n.names}
                elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                    usados.add(n.module.split(".")[0])
        usados -= std | locales
        lock = (raiz / "backend" / "requirements.lock").read_text(encoding="utf-8")
    except OSError as e:
        return [("FALTA", "Dependencias del backend", "no pude leer backend/requirements.lock: %s" % e)]
    paquetes = {re.split(r"[=<>\[ ;]", l.strip())[0].lower().replace("_", "-") for l in lock.splitlines() if l.strip() and not l.startswith("#")}
    alias = {"dotenv": ["python-dotenv"], "google": ["google-genai", "google-auth"], "psycopg2": ["psycopg2-binary", "psycopg2"],
             "sentry_sdk": ["sentry-sdk"], "yaml": ["pyyaml"]}
    faltan = sorted(m for m in usados if not any(c in paquetes for c in [m.lower().replace("_", "-")] + alias.get(m, [])))
    if faltan:
        return [("FALTA", "Dependencias del backend", "se importan pero no están en requirements.lock: %s (el contenedor no arrancaría)" % ", ".join(faltan))]
    return [("OK", "Dependencias del backend", "los %d paquetes que importa el código están en requirements.lock" % len(usados))]


def _git(raiz: Path, *args):
    return subprocess.run(["git", *args], cwd=str(raiz), capture_output=True, text=True, timeout=60)


def chequear_git(raiz: Path):
    if not (raiz / ".git").exists():
        return [("AVISO", "Repositorio Git", "todavía no es un repositorio. Para publicar: git init, git add ., git commit, y subirlo a GitHub")]
    try:
        r = _git(raiz, "ls-files")
        if r.returncode != 0:
            return [("AVISO", "Repositorio Git", "no pude consultar Git (%s)" % r.stderr.strip()[:80])]
        resultados = []
        envs = [f for f in r.stdout.splitlines() if Path(f).name.startswith(".env") and not f.endswith(".example")]
        if envs:
            resultados.append(("FALTA", "Archivos .env en Git", "Git está rastreando: %s. Sacalos con: git rm --cached <archivo>, y rotá las claves que tenían" % ", ".join(envs)))
        else:
            resultados.append(("OK", "Archivos .env en Git", "ningún .env está rastreado"))
        h = _git(raiz, "log", "--all", "--diff-filter=A", "--name-only", "--pretty=format:")
        hist = sorted({f for f in h.stdout.splitlines() if f and Path(f).name.startswith(".env") and not f.endswith(".example")})
        if hist:
            resultados.append(("FALTA", ".env en el historial", "alguna vez se subió: %s. Rotá esas claves (Gemini y SESSION_SECRET) antes de poner el repositorio público" % ", ".join(hist)))
        n = int(_git(raiz, "rev-list", "--count", "HEAD").stdout.strip() or 0)
        if n < 5:
            resultados.append(("AVISO", "Commits", "hay %d. La consigna pide commits claros e incrementales: hacé commits separados por tema de acá en adelante" % n))
        else:
            resultados.append(("OK", "Commits", "%d commits en el historial" % n))
        if _git(raiz, "status", "--porcelain").stdout.strip():
            resultados.append(("AVISO", "Cambios sin guardar", "hay archivos modificados sin commit: git add . y git commit antes de subir"))
        return resultados
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        return [("AVISO", "Repositorio Git", "no pude revisar Git (¿está instalado?): %s" % e)]


def chequear_secretos(raiz: Path):
    encontrados = []
    for carpeta, dirs, archivos in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in OMITIR]
        for nombre in archivos:
            if nombre.startswith(".env") and not nombre.endswith(".example"):
                continue                                   # los .env locales no se suben (lo controla .gitignore)
            ruta = Path(carpeta) / nombre
            if ruta.suffix.lower() not in EXTENSIONES_TEXTO and nombre != "Dockerfile":
                continue
            try:
                if RE_CLAVE_GEMINI.search(ruta.read_text(encoding="utf-8", errors="ignore")):
                    encontrados.append(str(ruta.relative_to(raiz)))
            except OSError:
                continue
    if encontrados:
        return [("FALTA", "Claves en el código", "parece una clave de Gemini en: %s" % ", ".join(encontrados[:5]))]
    return [("OK", "Claves en el código", "no hay claves de Gemini escritas en archivos que se suban (los .env quedan fuera)")]


def chequear_variables(env: dict):
    """Valida las variables que se cargan en Render. No imprime valores."""
    r = []

    def hay(nombre):
        return bool((env.get(nombre) or "").strip())

    # DATABASE_URL
    if not hay("DATABASE_URL"):
        r.append(("FALTA", "DATABASE_URL", "no está cargada (es la cadena de conexión de Neon)"))
    else:
        u = urlparse(env["DATABASE_URL"].strip())
        if u.scheme not in ("postgres", "postgresql", "postgresql+psycopg2"):
            r.append(("FALTA", "DATABASE_URL", "tiene que empezar con postgresql://"))
        elif (u.hostname or "") in ("localhost", "127.0.0.1", "db", "host.docker.internal"):
            r.append(("FALTA", "DATABASE_URL", "apunta a tu PC o al contenedor local; en Render tiene que ser la cadena de Neon"))
        elif (u.hostname or "").endswith("neon.tech") and "sslmode=require" not in env["DATABASE_URL"]:
            r.append(("FALTA", "DATABASE_URL", "falta ?sslmode=require al final de la cadena de Neon"))
        else:
            r.append(("OK", "DATABASE_URL", "tiene formato de base en la nube"))
    # GEMINI_API_KEY
    k = (env.get("GEMINI_API_KEY") or "").strip()
    if len(k) < 20 or _con_placeholder(k):
        r.append(("FALTA", "GEMINI_API_KEY", "falta o es un texto de relleno: pegá tu clave NUEVA de Google AI Studio"))
    else:
        r.append(("OK", "GEMINI_API_KEY", "está cargada"))
    # SESSION_SECRET
    s = (env.get("SESSION_SECRET") or "").strip()
    if len(s) < 32 or _con_placeholder(s):
        r.append(("FALTA", "SESSION_SECRET", "tiene que ser largo (32 o más caracteres) y propio: python -c \"import secrets; print(secrets.token_urlsafe(48))\""))
    else:
        r.append(("OK", "SESSION_SECRET", "largo suficiente"))
    # GOOGLE_CLIENT_ID
    g = (env.get("GOOGLE_CLIENT_ID") or "").strip()
    if not g or _con_placeholder(g):
        r.append(("AVISO", "GOOGLE_CLIENT_ID", "falta: sin él no anda el login con Google (el chat como invitado sí)"))
    elif not g.endswith(".apps.googleusercontent.com"):
        r.append(("AVISO", "GOOGLE_CLIENT_ID", "no termina en .apps.googleusercontent.com: revisá que sea el ID de cliente OAuth"))
    else:
        r.append(("OK", "GOOGLE_CLIENT_ID", "tiene el formato esperado"))
    # FRONTEND_ORIGINS
    origenes = [o.strip() for o in (env.get("FRONTEND_ORIGINS") or "").split(",") if o.strip()]
    if not origenes:
        r.append(("FALTA", "FRONTEND_ORIGINS", "falta: es la dirección de tu página en Vercel (sin esto el navegador bloquea al chat)"))
    else:
        con_barra = [o for o in origenes if o.endswith("/")]
        sin_https = [o for o in origenes if not o.startswith("https://") and "localhost" not in o and "127.0.0.1" not in o]
        solo_local = all("localhost" in o or "127.0.0.1" in o for o in origenes)
        if con_barra:
            r.append(("FALTA", "FRONTEND_ORIGINS", "no puede terminar en «/»: %s" % ", ".join(con_barra)))
        elif sin_https:
            r.append(("FALTA", "FRONTEND_ORIGINS", "tiene que usar https://: %s" % ", ".join(sin_https)))
        elif solo_local:
            r.append(("AVISO", "FRONTEND_ORIGINS", "todavía apunta a tu PC: cuando tengas la dirección de Vercel, cambiala (Fase 4 de la guía)"))
        else:
            r.append(("OK", "FRONTEND_ORIGINS", "direcciones con https y sin barra final"))
    # opcionales
    if not re.search(r"@", env.get("ADMIN_EMAILS") or ""):
        r.append(("AVISO", "ADMIN_EMAILS", "falta tu correo: sin él no vas a ver el panel para aprobar comercios"))
    if (env.get("COMERCIOS_AUTOAPROBADOS") or "0").strip() == "1":
        r.append(("AVISO", "COMERCIOS_AUTOAPROBADOS", "está en 1: cualquier comercio aparece sin que lo apruebes (recomendado 0 al empezar)"))
    if (env.get("ENTORNO") or "").strip().lower() != "produccion":
        r.append(("AVISO", "ENTORNO", "recomendado: produccion"))
    if hay("PORT"):
        r.append(("AVISO", "PORT", "en Render no la pongas: la define la plataforma"))
    return r


def correr_pruebas(raiz: Path):
    try:
        p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=str(raiz), capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as e:
        return [("AVISO", "Pruebas automáticas", "no pude correrlas: %s" % e)]
    ultimas = [l for l in (p.stderr + p.stdout).splitlines() if l.strip()][-2:]
    if p.returncode == 0:
        return [("OK", "Pruebas automáticas", " ".join(ultimas))]
    return [("FALTA", "Pruebas automáticas", "fallan: corré python -m unittest discover -s tests -v para ver cuáles")]


def cargar_env(ruta: Path) -> dict:
    datos = {}
    for linea in ruta.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*(.*)", linea)
        if m and not linea.strip().startswith("#"):
            datos[m.group(1)] = m.group(2).strip().strip("\"'")
    return datos


def redactar_texto_log(texto: str) -> str:
    if not isinstance(texto, str):
        return texto
    t = texto
    t = re.sub(
        r"(?i)\b([A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASS|API[_-]?KEY|PRIVATE[_-]?KEY)[A-Z0-9_]*)\s*=\s*([^\s,;]+)",
        r"\1=[REDACTED]",
        t,
    )
    t = re.sub(r"(?i)(https?://[^/\s:@]+:)([^@\s/]+)@", r"\1[REDACTED]@", t)
    return t


def main(argv):
    sin_pruebas = "--sin-pruebas" in argv
    resultados = []
    resultados += chequear_estructura(RAIZ)
    resultados += chequear_finales_de_linea(RAIZ)
    resultados += chequear_dependencias(RAIZ)
    resultados += chequear_secretos(RAIZ)
    resultados += chequear_git(RAIZ)
    if "--env" in argv:
        ruta = Path(argv[argv.index("--env") + 1])
        resultados += chequear_variables(cargar_env(ruta))
    else:
        resultados.append(("AVISO", "Variables de Render", "no se revisaron: armá un archivo render.env con las variables y corré --env render.env (NO lo subas a Git)"))
    if not sin_pruebas:
        resultados += correr_pruebas(RAIZ)
    simbolo = {"OK": "[  OK  ]", "AVISO": "[AVISO ]", "FALTA": "[FALTA ]"}
    print("VERIFICACIÓN PREVIA AL DESPLIEGUE\n" + "=" * 36)
    for estado, nombre, detalle in resultados:
        nombre_seguro = redactar_texto_log(nombre)
        detalle_seguro = redactar_texto_log(detalle)
        print("%s %-26s %s" % (simbolo[estado], nombre_seguro, detalle_seguro))
    faltas = sum(1 for r in resultados if r[0] == "FALTA")
    avisos = sum(1 for r in resultados if r[0] == "AVISO")
    print("\nResultado: %d FALTA, %d AVISO, %d OK" % (faltas, avisos, len(resultados) - faltas - avisos))
    if faltas:
        print("Arreglá lo que dice FALTA antes de desplegar.")
        return 1
    print("Sin faltas. Seguí con la guía de despliegue (Neon, Render, Vercel). Los AVISO son para que los mires.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
