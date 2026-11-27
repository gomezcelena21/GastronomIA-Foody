"""
Entrena la red neuronal propia de Foody (backend/modelo_foody.py) y guarda los pesos en
backend/modelo_foody.json. Escribe además el informe docs/pruebas/modelo_propio.md.

    pip install numpy
    python scripts/entrenar_modelo_foody.py            # compara varias versiones y se queda con la mejor
    python scripts/entrenar_modelo_foody.py --rapido   # entrena una sola versión (para probar)

Qué aprende (30 salidas, multietiqueta): 3 restricciones, 17 tipos de comida, 2 de precio y 8 intenciones
(saludo, gracias, despedida, ayuda, pregunta «qué es», otra restricción, opinión, fuera de tema).

Datos de entrenamiento: SINTÉTICOS (no hay consultas reales etiquetadas en cantidad). Se generan con
plantillas de frases (formales y coloquiales), sinónimos, zonas reales de la base (backend/zonas_dataset.py)
y errores de tipeo simulados (letras que faltan, sobran, se cambian o suenan igual: c/k/qu, s/z, v/b, ll/y).
También hay ejemplos NEGATIVOS para que la red aprenda a no inventar etiquetas.

Evaluación honesta, con tres conjuntos que la red NUNCA ve al entrenar:
  1. Validación sintética: frases generadas con otra semilla. Se usa SOLO para elegir la mejor versión.
  2. Prueba escrita a mano (PRUEBA_MANUAL): ~150 frases con errores y giros reales.
  3. Consultas reales (data/consultas_reales_etiquetadas.csv, fuera de Git): lo que la gente escribió
     a Foody, etiquetado a mano. Ver scripts/exportar_consultas_reales.py.
"""

import base64
import csv
import json
import os
import random
import sys
import time
from datetime import date

import numpy as np

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(RAIZ, "backend"))
import modelo_foody as m  # noqa: E402
from zonas_dataset import ZONAS  # noqa: E402

SEMILLA = 2026
N_EJEMPLOS = 60000
N_VALIDACION = 6000
# Versiones que se comparan: (neuronas ocultas, épocas)
VERSIONES = [(32, 12), (48, 14), (64, 14), (96, 14), (64, 20), (128, 16)]
RUTA_REALES = os.path.join(RAIZ, "data", "consultas_reales_etiquetadas.csv")

# ------------------------------------------------------------------ vocabulario por etiqueta
FORMAS = {
    "sin_tacc": ["sin tacc", "sin gluten", "apto celiacos", "apto celiaco", "para celiacos", "libre de gluten",
                 "gluten free", "sin t.a.c.c.", "apta celiacos", "sin trigo ni avena", "sintacc", "apto para celiacos"],
    "vegano": ["vegano", "vegana", "veganos", "veganas", "vegan", "plant based", "a base de plantas",
               "100% vegetal", "sin nada de origen animal", "opciones veganas", "comida vegana"],
    "vegetariano": ["vegetariano", "vegetariana", "vegetarianos", "vegetarianas", "veggie", "sin carne",
                    "comida vegetariana", "opciones vegetarianas", "ovolacto"],
    "pizzeria": ["pizza", "pizzas", "pizzeria", "pizzería", "pizzerias", "pizza a la piedra", "fugazzeta",
                 "muzza", "una pizza", "porcion de pizza"],
    "italiana": ["comida italiana", "italiana", "italiano", "pastas", "pasta", "trattoria", "ravioles",
                 "ñoquis", "lasagna", "risotto", "sorrentinos"],
    "hamburguesa": ["hamburguesa", "hamburguesas", "burger", "burgers", "hamburgueseria", "hamburguesería",
                    "smash burger", "una hamburguesa"],
    "japonesa": ["sushi", "comida japonesa", "japonesa", "japones", "ramen", "rolls", "nigiri", "sashimi",
                 "sushi libre"],
    "asiatica": ["comida asiatica", "asiatica", "asiático", "thai", "tailandesa", "wok", "coreana",
                 "comida coreana", "vietnamita"],
    "china": ["comida china", "chino", "china", "restaurante chino", "dim sum", "chop suey", "cantonesa"],
    "parrilla": ["parrilla", "asado", "parrillada", "bife de chorizo", "vacio", "choripan", "carne asada",
                 "parrillas", "un buen asado", "achuras"],
    "cafe": ["cafe", "café", "cafeteria", "cafetería", "un cafecito", "brunch", "merienda", "desayuno",
             "coffee", "cafe de especialidad", "un cortado", "un lugar para desayunar", "algo para merendar",
             "tomar un cafe", "tomar algo a la tarde"],
    "mexicana": ["comida mexicana", "mexicana", "mexicano", "tacos", "burritos", "nachos", "quesadillas",
                 "fajitas"],
    "peruana": ["comida peruana", "peruana", "peruano", "ceviche", "lomo saltado", "arroz chaufa",
                "aji de gallina"],
    "sandwicheria": ["sandwich", "sándwich", "sandwiches", "sanguche", "sandwicheria", "lomito", "lomitos",
                     "sanguchito", "sandwich de miga"],
    "comida_rapida": ["comida rapida", "fast food", "panchos", "pancho", "papas fritas", "algo al paso",
                      "comida al paso"],
    "pasteleria": ["pasteleria", "pastelería", "tortas", "torta", "postres", "postre", "algo dulce", "dulces",
                   "cheesecake", "alfajores", "tarta de frutilla"],
    "panaderia": ["panaderia", "panadería", "pan", "medialunas", "facturas", "pan casero", "panaderias",
                  "pan de masa madre"],
    "heladeria": ["heladeria", "heladería", "helado", "helados", "un helado", "gelato", "heladerias",
                  "un cucurucho"],
    "empanadas": ["empanadas", "empanada", "empanadas salteñas", "empanadas de carne", "empanadas fritas",
                  "docena de empanadas"],
    "comida_casera": ["comida casera", "casera", "viandas", "vianda", "bodegon", "bodegón", "comida de olla",
                      "guiso", "comida como en casa", "comida de bodegon"],
    "precio_bajo": ["barato", "barata", "baratos", "economico", "economica", "accesible", "baratito",
                    "que no sea caro", "que no sea muy caro", "sin gastar mucho", "con poca plata", "a buen precio",
                    "precio bajo", "low cost", "bien de precio", "que salga poco", "para el bolsillo", "el mas barato",
                    "lo mas barato", "economicos"],
    "precio_alto": ["caro", "de lujo", "elegante", "alta cocina", "fino", "un lugar top", "gourmet",
                    "para una ocasion especial", "de categoria", "exclusivo", "premium", "paquete", "cheto"],
}
PERSONA = {"sin_tacc": ["celiaco", "celiaca", "celíaco", "celiacos", "intolerante al gluten"],
           "vegano": ["vegano", "vegana", "veganos"], "vegetariano": ["vegetariano", "vegetariana"]}
# Lo que se pregunta en «¿qué es...?» (además de las FORMAS de cada tipo de comida)
TEMA_QUE_ES = {"sin_tacc": ["sin tacc", "tacc", "la celiaquia", "ser celiaco", "el gluten", "apto celiaco"],
               "vegano": ["vegano", "el veganismo", "ser vegano", "la comida vegana"],
               "vegetariano": ["vegetariano", "ser vegetariano", "ovolactovegetariano", "la comida vegetariana"]}
OTRAS = ["sin lactosa", "intolerante a la lactosa", "los lacteos me caen mal", "no puedo comer lacteos",
         "soy diabetico", "soy diabetica", "para diabeticos", "sin azucar", "alergico al mani", "alergia al mani",
         "alergia a los frutos secos", "alergico a los mariscos", "sin huevo", "alergia al huevo", "kosher", "halal",
         "bajo en sodio", "sin sal", "soy hipertenso", "la leche me hace mal", "no tolero la lactosa",
         "apto diabeticos", "sin fructosa", "alergia a la soja", "deslactosado", "la lactosa me hace mal"]
NEUTRAS = ["milanesas", "milanesa", "algo rico", "comida", "un restaurante", "restaurantes", "un lugar para cenar",
           "donde comer", "lugares", "un bar", "cerveza", "tragos", "vinos", "mariscos", "pescado",
           "ensaladas", "comida arabe", "shawarma", "comida armenia", "comida india", "algo sin cebolla",
           "un lugar tranquilo", "con patio", "pet friendly", "con estacionamiento", "algo para llevar", "delivery",
           "un lugar lindo", "buena musica", "picada", "tapas", "comida para el finde", "almorzar", "cenar", "comer",
           "algo abierto ahora", "un lugar con wifi", "comida colombiana", "comida venezolana", "comida griega",
           "kebab", "pollo", "pollo frito", "pescaderia", "rotiseria", "cerca de casa", "algo para comer en casa",
           "delivery a casa", "en casa", "cerca de mi trabajo", "para llevar a casa", "desde casa",
           "cerca de la facu", "algo cerca", "un lugar cerca"]
CHARLA = {
    "saludo": ["hola", "holi", "holis", "buenas", "buen dia", "buenas tardes", "buenas noches", "que tal",
               "como andas", "como estas", "hey", "que onda", "hola foody", "buenas foody", "hola que tal",
               "hola como estas", "holaa", "hola!", "que tal foody", "hola gastronomia", "que onda hermano",
               "que onda amigo", "ey", "buenas buenas", "hola hermano", "que haces", "como va", "que onda che"],
    "gracias": ["gracias", "muchas gracias", "mil gracias", "gracias foody", "genial gracias", "perfecto, gracias",
                "joya", "barbaro", "buenisimo", "te pasaste", "sos un genio", "gracias por la ayuda", "re util",
                "genial", "perfecto", "excelente"],
    "despedida": ["chau", "chao", "adios", "nos vemos", "hasta luego", "hasta mañana", "bye", "me voy",
                  "chau foody", "nos vemos foody", "hasta la proxima", "chau, gracias por todo"],
    "ayuda": ["ayuda", "que podes hacer", "como funciona", "como funcionas", "como funciona esto", "que sabes hacer", "quien sos", "para que servis",
              "como te uso", "que sos", "me ayudas?", "necesito ayuda", "que cosas podes buscar",
              "en que me podes ayudar", "foody ayudame"],
    None: ["tengo hambre", "no se que comer", "asdf qwerty", "jajaja", "ok", "dale", "si", "no", "mmm", "bueno",
           "lo que sea", "sorprendeme", "recomendame algo", "que me recomendas", "123", "?", "y ahora que",
           "otra cosa", "estoy aburrido", "cualquier cosa", "algo para hoy", "foody", "gastronomia"],
}
FUERA = ["cual es la capital de {pais}?", "quien gano el partido ayer", "haceme la tarea de matematica",
         "como programo en python", "contame un chiste", "que hora es", "como va a estar el clima mañana",
         "quien es el presidente de {pais}", "escribime un poema", "cuanto es 2+2", "resolve esta ecuacion",
         "que opinas de la politica", "recomendame una pelicula", "como arreglo mi computadora",
         "traduci esto al ingles", "dame un consejo de amor", "cuanto sale el dolar", "que me pongo hoy",
         "que remedio tomo para el dolor de cabeza", "me duele la panza, que hago", "pasame la clave",
         "hablame de futbol", "quien es messi", "como se hace un curriculum", "recomendame una serie",
         "cuantos habitantes tiene {pais}", "que idioma se habla en {pais}", "ayudame con mi tarea de historia",
         "escribime un mail para mi jefe", "como invierto mi plata", "que auto me compro",
         "va a llover hoy?", "que temperatura hace", "pronostico del fin de semana", "quien canta esa cancion",
         "cuando juega la seleccion", "explicame la fotosintesis", "me haces un resumen de este texto"]
PAISES = ["francia", "italia", "japon", "peru", "mexico", "brasil", "chile", "españa", "argentina", "uruguay"]
LUGARES = ["la esquina", "lo de pepe", "don carlos", "el rincon", "casa ana", "la farola", "el pobre luis",
           "la rambla", "el club", "green house", "la cocina de marta", "el gran local", "ese lugar", "ahi"]
ADJ_OPINION = ["re cheto", "horrible", "buenisimo", "re caro", "sucio", "espectacular", "un desastre", "muy rico",
               "carisimo", "feo", "malisimo", "genial", "frio", "lento", "re lindo", "caro", "barato", "lleno",
               "re rico", "un asco", "increible"]
OPINION = ["fui a {l} y estaba {a}", "el lugar estaba {a}", "comi en {l} y estuvo {a}", "{l} es {a}",
           "la {c} de {l} estaba {a}", "me atendieron mal en {l}", "la atencion fue pesima", "tardaron una hora",
           "la comida llego fria", "me encanto {l}", "no vuelvo mas a {l}", "estuvo increible la cena",
           "el mozo fue muy amable", "me cobraron de mas en {l}", "ayer fui a {l}, {a} mal", "{l} me parecio {a}",
           "fuimos a comer {c} a {l} y estaba {a}", "me gusto mucho el lugar de ayer", "el lugar que me pasaste estaba {a}",
           "fuimos al que me dijiste y nos encanto", "el que me recomendaste era {a}", "no me gusto la atencion",
           "nos trataron re bien", "la comida era poca y {a}", "estaba re cheto el lugar", "un lugar muy cheto y {a}"]

GARANTIAS = ["es 100% seguro para {p}?", "es 100 % seguro para {p} el primero?", "me garantizas que es {f}?",
             "el primero es {f}?", "es totalmente {f}?", "decime que el primero es 100 % seguro para {p}",
             "es apto para {p} de verdad?", "seguro que es {f}?", "me aseguras que no tiene tacc?",
             "es seguro para un {p}?", "puedo ir tranquilo siendo {p}?", "el segundo es {f}?"]
SEGUIMIENTO_PRECIO = {"precio_bajo": ["cual es el mas barato?", "cual de esos es el mas barato?", "y el mas economico?",
                                      "cual sale menos?", "cual es mas barato", "alguno mas barato?",
                                      "hay algo mas economico?", "cual me conviene por precio?", "el mas barato cual es"],
                      "precio_alto": ["cual es el mas elegante?", "alguno mas top?", "y algo mas fino?",
                                      "cual es el mas cheto?"]}

PLANTILLAS_BUSQUEDA = [
    "{c} en {z}", "{c} {d} en {z}", "busco {c} {d} por {z}", "quiero comer {c}", "donde hay {c} {d}?",
    "algo {d} en {z}", "soy {p} y busco {c}", "soy {p}, busco algo en {z}", "recomendame {c}", "{c} {d}",
    "lugares de {c} cerca de {z}", "me recomendas alguna {c} de {z}?", "{c}", "{d}", "hay {c} {d} en {z}?",
    "necesito {c} {d}", "un lugar de {c} en {z}", "conoces {c} por {z}", "{c} o {c2} en {z}", "{c} y {c2} {d}",
    "quiero {c} {d} cerca de {z}", "che, {c} por {z}?", "busco {d} {c}", "{z} {c}", "algo de {c} {d} para hoy",
    "{c} {d} y {d2}", "donde como {c} en {z}", "comer {c} en {z} {d}", "{c} en {z} que sea {d}",
    # coloquiales y largas
    "che, donde puedo morfar {c} {d} por {z}?", "estoy por {z} y tengo ganas de {c}",
    "conoces algun lugar de {c} {d}?", "mi novia es {p}, donde la llevo a comer en {z}?",
    "vamos con amigos a {z}, uno es {p}, que nos recomendas?", "quiero salir a comer {c} esta noche por {z}",
    "hay algun {c} {d} abierto en {z}?", "me pasas lugares de {c} {r} en {z}?", "busco un lugar {r} para comer {c}",
    "{c} {r} en {z}", "algo {r} por {z}", "que opciones {d} hay en {z}?", "que hay de {c} en {z}?",
    "que {c} me recomendas en {z}?", "mi hija es {p}, donde podemos ir?", "dame un local en {z} {d}",
    "quisiera {c} {r} en {z} por favor", "me antoje de {c}, alguno {d} en {z}?", "{c} {r}", "algo {r} y {d}",
    "donde puedo comer {c} {r} cerca de {z}", "el mas barato de {c} en {z}",
]
PLANTILLAS_NEUTRAS = ["{n} en {z}", "busco {n} por {z}", "{n}", "quiero {n}", "donde hay {n} en {z}?",
                      "{n} cerca de {z}", "algo en {z}", "restaurante en {z}", "que hay en {z}?", "{z}", "en {z}",
                      "y en {z}?", "por {z}", "{z}!", "estoy en {z}", "vivo en {z}",
                      "un restaurante en una esquina de {z}", "me recomendas lugares para comer en {z}",
                      "donde puedo comer en {z}", "donde podemos comer por {z}?", "que lugares hay para comer en {z}",
                      "decime un lugar para comer", "dame un lugar para comer en {z}"]
PLANTILLAS_QUE_ES = ["que es {x}?", "que significa {x}", "que quiere decir {x}", "{x} que es?", "me explicas que es {x}?",
                     "no se que es {x}", "que es eso de {x}", "que lleva {x}?", "contame que es {x}",
                     "de que se trata {x}", "que diferencia hay entre {x} y {y}", "{x} y {y} es lo mismo?",
                     "que come una persona {p}?", "que no puede comer alguien {p}?", "que es ser {p}?",
                     "que son los {x}?", "que son las {x}", "que tiene {x}?", "como es {x}?"]
PLANTILLAS_OTRA = ["{o}", "{o}, donde puedo comer en {z}?", "quiero comer algo, {o}", "busco {c} {o}",
                   "{c} en {z} pero {o}", "hay algo {o} por {z}?", "que me recomendas? {o}", "necesito un lugar {o}",
                   "quiero comer pero {o}, donde puedo ir?", "{o}, que puedo comer?"]

# ------------------------------------------------------------ errores de tipeo simulados
SONIDOS = [("c", "k"), ("qu", "k"), ("z", "s"), ("s", "z"), ("v", "b"), ("b", "v"), ("ll", "y"), ("y", "ll"),
           ("h", ""), ("zz", "z"), ("cc", "c"), ("cc", "k"), ("cc", "q"), ("c", "s"), ("g", "j"), ("j", "g"),
           ("rr", "r"), ("ñ", "n")]
TECLADO = "qwertyuiopasdfghjklzxcvbnm"


def tipeo(palabra, r):
    if len(palabra) < 3:
        return palabra
    op = r.random()
    if op < 0.3:
        for a, b in r.sample(SONIDOS, len(SONIDOS)):
            if a in palabra:
                return palabra.replace(a, b, 1)
    i = r.randrange(len(palabra))
    if op < 0.5:
        return palabra[:i] + palabra[i + 1:]                         # falta una letra
    if op < 0.65:
        return palabra[:i] + palabra[i] + palabra[i:]                # letra repetida
    if op < 0.8 and i < len(palabra) - 1:
        return palabra[:i] + palabra[i + 1] + palabra[i] + palabra[i + 2:]   # letras cambiadas
    return palabra[:i] + r.choice(TECLADO) + palabra[i + 1:]         # tecla equivocada


FILAS_TECLADO = ["qwertyuiop", "asdfghjkl", "zxcvbnm", "1234567890"]


def basura(r):
    """Teclazos o letras al azar («asdf», «jjjj», «xkq pwe»), para que la red aprenda a no ver comida ahí."""
    palabras = []
    for _ in range(r.randint(1, 3)):
        if r.random() < 0.5:
            fila = r.choice(FILAS_TECLADO)
            i = r.randrange(len(fila) - 2)
            palabras.append(fila[i:i + r.randint(3, 6)])
        elif r.random() < 0.3:
            palabras.append(r.choice("abcdefghijklmnopqrstuvwxyz") * r.randint(3, 6))
        else:
            palabras.append("".join(r.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(r.randint(2, 7))))
    return " ".join(palabras)


def ensuciar(frase, r, prob):
    return " ".join(tipeo(p, r) if r.random() < prob else p for p in frase.split(" "))


def _busqueda(r, zonas):
    plantilla = r.choice(PLANTILLAS_BUSQUEDA)
    et = set()
    c, c2 = r.sample(list(m.COCINAS), 2)
    d, d2 = r.sample(list(m.RESTRICCIONES), 2)
    v = {"z": r.choice(zonas), "c": "", "c2": "", "d": "", "d2": "", "p": "", "r": ""}
    if "{c}" in plantilla:
        v["c"] = ensuciar(r.choice(FORMAS[c]), r, 0.45)
        et.add(c)
    if "{c2}" in plantilla:
        v["c2"] = ensuciar(r.choice(FORMAS[c2]), r, 0.45)
        et.add(c2)
    if "{p}" in plantilla:
        v["p"] = ensuciar(r.choice(PERSONA[d]), r, 0.45)
        et.add(d)
    elif "{d}" in plantilla and r.random() > 0.3:            # a veces sin restricción
        v["d"] = ensuciar(r.choice(FORMAS[d]), r, 0.45)
        et.add(d)
    if "{d2}" in plantilla:
        v["d2"] = ensuciar(r.choice(FORMAS[d2]), r, 0.45)
        et.add(d2)
    if "{r}" in plantilla and (r.random() > 0.25 or plantilla in ("algo {r} por {z}", "{c} {r}")):
        precio = "precio_bajo" if r.random() < 0.7 else "precio_alto"
        v["r"] = ensuciar(r.choice(FORMAS[precio]), r, 0.3)
        et.add(precio)
    elif "{r}" not in plantilla and r.random() < 0.1:          # precio agregado al final
        precio = "precio_bajo" if r.random() < 0.7 else "precio_alto"
        plantilla += " " + r.choice(["{r}", "y {r}", "que sea {r}"])
        v["r"] = r.choice(FORMAS[precio])
        et.add(precio)
    return plantilla.format(**v), et


def generar(n, r):
    zonas = list(ZONAS)
    datos = []
    for _ in range(n):
        et = set()
        t = r.random()
        if t < 0.52:
            frase, et = _busqueda(r, zonas)
        elif t < 0.60:                                     # «¿qué es...?»
            plantilla = r.choice(PLANTILLAS_QUE_ES)
            a, b = r.sample(list(m.RESTRICCIONES + m.COCINAS), 2)
            if "{p}" in plantilla:
                a = r.choice(list(PERSONA))
                frase = plantilla.format(p=r.choice(PERSONA[a]))
                et = {a}
            else:
                if "{y}" in plantilla and r.random() < 0.5:
                    a, b = "vegano", "vegetariano"
                tema = lambda e: r.choice(TEMA_QUE_ES.get(e) or FORMAS[e])  # noqa: E731
                frase = plantilla.format(x=ensuciar(tema(a), r, 0.3), y=ensuciar(tema(b), r, 0.3))
                et = {a, b} if "{y}" in plantilla else {a}
            et.add("pregunta_que_es")
        elif t < 0.66:                                     # otra restricción (no está en la base)
            plantilla = r.choice(PLANTILLAS_OTRA)
            c = r.choice(list(m.COCINAS))
            frase = plantilla.format(o=ensuciar(r.choice(OTRAS), r, 0.3), z=r.choice(zonas),
                                     c=ensuciar(r.choice(FORMAS[c]), r, 0.3))
            et = {"otra_restriccion"} | ({c} if "{c}" in plantilla else set())
        elif t < 0.68:                                     # garantías y seguimientos sobre la lista anterior
            if r.random() < 0.55:
                d = r.choice(list(PERSONA))
                frase = r.choice(GARANTIAS).format(p=r.choice(PERSONA[d]), f=r.choice(FORMAS[d]))
                et = {d}
            else:
                precio = "precio_bajo" if r.random() < 0.8 else "precio_alto"
                frase = r.choice(SEGUIMIENTO_PRECIO[precio])
                et = {precio}
        elif t < 0.72:                                     # opinión sobre un local
            plantilla = r.choice(OPINION)
            c = r.choice(list(m.COCINAS))
            frase = plantilla.format(l=r.choice(LUGARES), a=r.choice(ADJ_OPINION), c=r.choice(FORMAS[c]))
            et = {"opinion"} | ({c} if "{c}" in plantilla else set())
        elif t < 0.76:                                     # fuera de tema
            frase = r.choice(FUERA).format(pais=r.choice(PAISES))
            et = {"fuera_de_tema"}
        elif t < 0.84:
            frase = r.choice(PLANTILLAS_NEUTRAS).format(n=r.choice(NEUTRAS), z=r.choice(zonas))
        elif t < 0.87:                                     # teclazos y texto sin sentido: no es nada
            frase = basura(r)
        else:
            intencion = r.choice(list(CHARLA))
            frase = r.choice(CHARLA[intencion])
            et = {intencion} if intencion else set()
        # Saludo al principio o «gracias» / «por favor» al final, como escribe la gente
        if r.random() < 0.08 and "saludo" not in et:
            frase = r.choice(["hola, ", "hola ", "buenas, ", "hola foody, ", "buen dia, "]) + frase
            et.add("saludo")
        elif r.random() < 0.06:
            frase = frase + r.choice([" por favor", ", porfa", " porfi"])
        elif r.random() < 0.04 and "gracias" not in et:
            frase = frase + r.choice([", gracias", " gracias!", " muchas gracias"])
            et.add("gracias")
        elif r.random() < 0.05:
            frase = r.choice(["foody, ", "che foody ", "che, "]) + frase
        frase = ensuciar(" ".join(frase.split()), r, 0.08)
        if r.random() < 0.25:
            frase = frase.upper() if r.random() < 0.3 else frase.capitalize()
        if r.random() < 0.15:
            frase = r.choice(["¿", ""]) + frase + r.choice(["?", "!", "...", "??"])
        datos.append((frase, et))
    return datos


# ---------------------------------------------------- prueba escrita a mano (no se entrena)
def _e(*a):
    return set(a)


PRUEBA_MANUAL = [
    # tipeo
    ("pizeria en palermo", _e("pizzeria")), ("sin tak en belgrano", _e("sin_tacc")),
    ("piza sin tacc", _e("pizzeria", "sin_tacc")), ("hamburgesas veganas", _e("hamburguesa", "vegano")),
    ("amburguesa en caballito", _e("hamburguesa")), ("susi en recoleta", _e("japonesa")),
    ("parila en villa urquiza", _e("parrilla")), ("heladria en nuñez", _e("heladeria")),
    ("enpanadas en almagro", _e("empanadas")), ("panaderia sin gluten en boedo", _e("panaderia", "sin_tacc")),
    ("selíaco busco algo en flores", _e("sin_tacc")), ("soy celiako", _e("sin_tacc")),
    ("algo begano en villa crespo", _e("vegano")), ("comida vejetariana", _e("vegetariano")),
    ("una tortta sin tacc", _e("pasteleria", "sin_tacc")), ("pizzeria vegana y sin tac", _e("pizzeria", "vegano", "sin_tacc")),
    ("eladeria vegana", _e("heladeria", "vegano")), ("asdo en mataderos", _e("parrilla")),
    ("busco algo apto selíacos", _e("sin_tacc")), ("sushii en belgrano", _e("japonesa")),
    ("cafeteria en palremo", _e("cafe")), ("hamburgueseria barata", _e("hamburguesa", "precio_bajo")),
    ("pasteleria vejana", _e("pasteleria", "vegano")), ("emapandas de carne", _e("empanadas")),
    ("comida mexicna en colegiales", _e("mexicana")), ("ceviche peruano", _e("peruana")),
    ("sanwich de miga", _e("sandwicheria")), ("vejetariano en caballito", _e("vegetariano")),
    # sinónimos y palabras que las reglas no conocen
    ("cafeteria vegetariana en san telmo", _e("cafe", "vegetariano")), ("pastas en palermo", _e("italiana")),
    ("ceviche en once", _e("peruana")), ("tacos en colegiales", _e("mexicana")),
    ("libre de gluten en belgrano", _e("sin_tacc")), ("sanguches en flores", _e("sandwicheria")),
    ("medialunas en caballito", _e("panaderia")), ("comida china en belgrano", _e("china")),
    ("comida rapida en retiro", _e("comida_rapida")), ("bodegon en boedo", _e("comida_casera")),
    ("ramen en palermo", _e("japonesa")), ("plant based en palermo", _e("vegano")),
    ("cafe o pasteleria sin gluten", _e("cafe", "pasteleria", "sin_tacc")), ("ravioles caseros", _e("italiana")),
    ("un buen bife de chorizo", _e("parrilla")), ("burritos en nuñez", _e("mexicana")),
    ("facturas y medialunas", _e("panaderia")), ("algo de wok", _e("asiatica")), ("comida thai", _e("asiatica")),
    ("guiso de lentejas", _e("comida_casera")), ("un pancho al paso", _e("comida_rapida")),
    ("sin carne en villa crespo", _e("vegetariano")), ("algo sin nada de origen animal", _e("vegano")),
    # coloquiales y largas
    ("che donde puedo morfar unas pizzas por palermo?", _e("pizzeria")),
    ("estoy en belgrano y me muero de ganas de un helado", _e("heladeria")),
    ("mi novia es celiaca, donde la llevo a cenar en recoleta?", _e("sin_tacc")),
    ("vamos con amigos a caballito y uno es vegano, que nos recomendas?", _e("vegano")),
    ("conoces alguna parrilla buena por mataderos?", _e("parrilla")),
    ("necesito un lugar para merendar en almagro", _e("cafe")),
    ("hay alguna pizzeria abierta en flores que tenga sin tacc?", _e("pizzeria", "sin_tacc")),
    ("me pasas hamburgueserias en palermo que tengan opciones veganas", _e("hamburguesa", "vegano")),
    ("que opciones vegetarianas hay en san telmo?", _e("vegetariano")),
    ("que hay de sushi por belgrano?", _e("japonesa")),
    # precio
    ("pizzeria barata en palermo", _e("pizzeria", "precio_bajo")), ("algo economico en caballito", _e("precio_bajo")),
    ("busco un lugar elegante para una cena especial", _e("precio_alto")),
    ("sushi que no sea muy caro", _e("japonesa", "precio_bajo")), ("parrilla de lujo en puerto madero", _e("parrilla", "precio_alto")),
    ("quiero comer bien sin gastar mucho", _e("precio_bajo")), ("cual es el mas barato?", _e("precio_bajo")),
    ("algo baratito sin tacc", _e("precio_bajo", "sin_tacc")), ("restaurante gourmet en recoleta", _e("precio_alto")),
    ("empanadas baratas", _e("empanadas", "precio_bajo")),
    # pregunta «qué es»
    ("que es sin tacc?", _e("pregunta_que_es", "sin_tacc")), ("que significa vegano", _e("pregunta_que_es", "vegano")),
    ("que diferencia hay entre vegano y vegetariano?", _e("pregunta_que_es", "vegano", "vegetariano")),
    ("que es el ceviche?", _e("pregunta_que_es", "peruana")), ("que es la celiaquia", _e("pregunta_que_es", "sin_tacc")),
    ("que come un vegetariano?", _e("pregunta_que_es", "vegetariano")), ("que es el tacc", _e("pregunta_que_es", "sin_tacc")),
    ("que son las achuras?", _e("pregunta_que_es", "parrilla")), ("que lleva una fugazzeta", _e("pregunta_que_es", "pizzeria")),
    ("me explicas que es el ramen?", _e("pregunta_que_es", "japonesa")),
    ("que no puede comer un celiaco?", _e("pregunta_que_es", "sin_tacc")), ("que es ser vegana?", _e("pregunta_que_es", "vegano")),
    # otra restricción
    ("soy intolerante a la lactosa", _e("otra_restriccion")), ("algo sin lactosa en palermo", _e("otra_restriccion")),
    ("soy diabetica, donde puedo comer?", _e("otra_restriccion")), ("tengo alergia al mani", _e("otra_restriccion")),
    ("los lacteos me caen mal", _e("otra_restriccion")), ("busco pizza pero sin lactosa", _e("pizzeria", "otra_restriccion")),
    ("comida kosher en once", _e("otra_restriccion")), ("algo sin azucar para mi papa que es diabetico", _e("otra_restriccion")),
    ("alergica a los frutos secos", _e("otra_restriccion")), ("la leche me hace mal, que puedo comer?", _e("otra_restriccion")),
    # opinión
    ("fui a la esquina y estaba re caro", _e("opinion")), ("me atendieron re mal en ese lugar", _e("opinion")),
    ("la comida estuvo buenisima ayer", _e("opinion")), ("el local estaba sucio", _e("opinion")),
    ("no vuelvo mas a ese bodegon", _e("opinion", "comida_casera")), ("me encanto el lugar que me recomendaste", _e("opinion")),
    ("tardaron mucho en atendernos", _e("opinion")),
    # fuera de tema
    ("cual es la capital de italia?", _e("fuera_de_tema")), ("haceme la tarea de quimica", _e("fuera_de_tema")),
    ("quien gano el partido de river?", _e("fuera_de_tema")), ("contame un chiste", _e("fuera_de_tema")),
    ("como hago una pagina web", _e("fuera_de_tema")), ("que tiempo va a hacer mañana", _e("fuera_de_tema")),
    ("recomendame una peli", _e("fuera_de_tema")), ("me duele la cabeza que tomo", _e("fuera_de_tema")),
    # charla
    ("hola", _e("saludo")), ("Hola Foody!", _e("saludo")), ("buenas tardes", _e("saludo")), ("que onda", _e("saludo")),
    ("holaa como andas", _e("saludo")), ("gracias!", _e("gracias")), ("muchisimas gracias", _e("gracias")),
    ("genial, gracias foody", _e("gracias")), ("chau", _e("despedida")), ("nos vemos!", _e("despedida")),
    ("hasta luego foody", _e("despedida")), ("que podes hacer?", _e("ayuda")), ("como funcionas?", _e("ayuda")),
    ("necesito ayuda", _e("ayuda")), ("hola, busco sushi en palermo", _e("saludo", "japonesa")),
    ("buenas! algo vegano en caballito?", _e("saludo", "vegano")), ("pizza en palermo, gracias", _e("pizzeria", "gracias")),
    # negativos: no debe inventar etiquetas
    ("tengo hambre", set()), ("asdf qwerty", set()), ("restaurantes en palermo", set()),
    ("milanesas en avellaneda", set()), ("restaurante en cordoba", set()), ("que me recomendas en mar del plata", set()),
    ("un bar con patio en palermo", set()), ("cafayate", set()), ("cerca de mi casa", set()),
    ("algo rico para cenar", set()), ("donde puedo comer en tigre", set()), ("un lugar tranquilo con wifi", set()),
    ("comida arabe", set()), ("dale", set()), ("lo que sea", set()), ("picada y cerveza", set()),
    ("asdf", set()), ("ñlkj", set()), ("xxxx", set()), ("qwe asd", set()),
]


def leer_reales():
    if not os.path.exists(RUTA_REALES):
        return []
    with open(RUTA_REALES, encoding="utf-8-sig", newline="") as fh:
        return [(f["frase"], {e for e in (f.get("etiquetas") or "").split(";") if e})
                for f in csv.DictReader(fh)]


def densa(lote):
    x = np.zeros((len(lote), m.DIM), dtype=np.float32)
    for k, rr in enumerate(lote):
        for i, v in rr.items():
            x[k, i] = v
    return x


EJEMPLOS_ANIMACION = ["pizeria en palermo", "sin tak en belgrano", "¿qué es sin TACC?", "hola foody!",
                      "algo begano y barato", "los lacteos me caen mal", "asdf",
                      "fui a la esquina y estaba re caro"]
CADA_PASOS = 100            # cada cuántos lotes se registra el progreso
RUTA_REGISTRO = os.path.join(RAIZ, "docs", "pruebas", "entrenamiento_foody.json")


class Registro:
    """Anota cómo va aprendiendo la red: pérdida, aciertos y qué responde a unas frases de ejemplo."""

    def __init__(self, conjuntos):
        # conjuntos: {nombre: [(texto, etiquetas)]}; se precalculan los rasgos y las respuestas correctas
        self.conjuntos = {}
        for nombre, datos in conjuntos.items():
            if datos:
                x = densa([m.rasgos(t) for t, _ in datos])
                y = np.zeros((len(datos), len(m.ETIQUETAS)), dtype=bool)
                for k, (_, et) in enumerate(datos):
                    for e in et:
                        y[k, m.ETIQUETAS.index(e)] = True
                self.conjuntos[nombre] = (x, y)
        self.x_ejemplos = densa([m.rasgos(t) for t in EJEMPLOS_ANIMACION])
        self.puntos = []

    @staticmethod
    def _prob(p, x):
        h = np.maximum(0, x @ p["w1"] + p["b1"])
        return 1 / (1 + np.exp(-(h @ p["w2"] + p["b2"])))

    def anotar(self, p, paso, epoca, perdida):
        punto = {"paso": paso, "epoca": round(epoca, 3), "perdida": None if perdida is None else round(perdida, 5)}
        for nombre, (x, y) in self.conjuntos.items():
            pred = self._prob(p, x) >= m.UMBRAL
            punto[nombre] = round(float((pred == y).all(axis=1).mean()), 4)
        prob = self._prob(p, self.x_ejemplos)
        punto["ejemplos"] = [{m.ETIQUETAS[j]: round(float(v), 3) for j, v in enumerate(fila) if v >= 0.05}
                             for fila in prob]
        self.puntos.append(punto)


def entrenar(idx, y, oculta, epocas, semilla, registro=None):
    rng = np.random.default_rng(semilla)
    r = random.Random(semilla)
    E = len(m.ETIQUETAS)
    p = {"w1": rng.normal(0, np.sqrt(2 / 60), (m.DIM, oculta)).astype(np.float32),
         "b1": np.zeros(oculta, np.float32),
         "w2": rng.normal(0, np.sqrt(1 / oculta), (oculta, E)).astype(np.float32),
         "b2": np.full(E, -2.0, np.float32)}
    mom = {k: np.zeros_like(v) for k, v in p.items()}
    vel = {k: np.zeros_like(v) for k, v in p.items()}
    lr, b1, b2, eps, l2, t = 0.004, 0.9, 0.999, 1e-8, 1e-6, 0
    orden = list(range(len(idx)))
    lotes_por_epoca = (len(orden) + 127) // 128
    acumulada, n_acum = 0.0, 0
    if registro:
        registro.anotar(p, 0, 0.0, None)           # antes de aprender nada
    for ep in range(epocas):
        r.shuffle(orden)
        for a in range(0, len(orden), 128):
            sel = orden[a:a + 128]
            x, yy = densa([idx[i] for i in sel]), y[sel]
            h = np.maximum(0, x @ p["w1"] + p["b1"])
            prob = 1 / (1 + np.exp(-(h @ p["w2"] + p["b2"])))
            if registro:
                acumulada += float(-np.mean(np.sum(yy * np.log(prob + 1e-7) + (1 - yy) * np.log(1 - prob + 1e-7), 1)))
                n_acum += 1
            dz = (prob - yy) / len(sel)
            g = {"w2": h.T @ dz, "b2": dz.sum(0)}
            dh = (dz @ p["w2"].T) * (h > 0)
            g["w1"], g["b1"] = x.T @ dh + l2 * p["w1"], dh.sum(0)
            t += 1
            for k in p:
                mom[k] = b1 * mom[k] + (1 - b1) * g[k]
                vel[k] = b2 * vel[k] + (1 - b2) * g[k] ** 2
                p[k] -= lr * (mom[k] / (1 - b1 ** t)) / (np.sqrt(vel[k] / (1 - b2 ** t)) + eps)
            if registro and (t % CADA_PASOS == 0 or t == lotes_por_epoca * epocas):
                registro.anotar(p, t, t / lotes_por_epoca, acumulada / max(1, n_acum))
                acumulada, n_acum = 0.0, 0
    return p


def a_json(p, oculta):
    escala = np.maximum(np.abs(p["w1"]).max(0), 1e-8) / 127.0        # int8 por neurona oculta
    q = np.clip(np.round(p["w1"] / escala), -127, 127).astype(np.int8)
    return {"version": str(date.today()), "dim": m.DIM, "oculta": oculta, "etiquetas": list(m.ETIQUETAS),
            "umbral": m.UMBRAL, "w1": base64.b64encode(q.tobytes()).decode("ascii"),
            "s1": [round(float(s), 8) for s in escala], "b1": [round(float(v), 6) for v in p["b1"]],
            "w2": [[round(float(v), 6) for v in fila] for fila in p["w2"]],
            "b2": [round(float(v), 6) for v in p["b2"]]}


GRUPOS = {"restricciones": m.RESTRICCIONES, "cocinas": m.COCINAS, "precio": m.PRECIOS, "intenciones": m.INTENCIONES}


def evaluar(red, datos):
    def pred(t):
        return {e for e, v in red.probabilidades(t).items() if v >= red.umbral}
    exactos, fallos = 0, []
    cuenta = {g: [0, 0, 0] for g in GRUPOS}            # tp, fp, fn por grupo
    for t, et in datos:
        pr = pred(t)
        exactos += pr == et
        if pr != et:
            fallos.append((t, sorted(et), sorted(pr)))
        for g, etiquetas in GRUPOS.items():
            a, b = pr & set(etiquetas), et & set(etiquetas)
            cuenta[g][0] += len(a & b)
            cuenta[g][1] += len(a - b)
            cuenta[g][2] += len(b - a)
    tp, fp, fn = (sum(c[i] for c in cuenta.values()) for i in range(3))
    f = lambda a, b: a / b if b else 1.0  # noqa: E731
    return {"exactos": exactos, "total": len(datos), "precision": f(tp, tp + fp), "recall": f(tp, tp + fn),
            "grupos": {g: (f(c[0], c[0] + c[1]), f(c[0], c[0] + c[2])) for g, c in cuenta.items()},
            "fallos": fallos}


def pct(r):
    return "%d de %d (%.0f %%)" % (r["exactos"], r["total"], 100 * r["exactos"] / max(1, r["total"]))


def main():
    reales = leer_reales()
    excluidas = {m.normalizar(t) for t, _ in PRUEBA_MANUAL + reales}
    datos = [d for d in generar(N_EJEMPLOS, random.Random(SEMILLA)) if m.normalizar(d[0]) not in excluidas]
    validacion = [d for d in generar(N_VALIDACION, random.Random(SEMILLA + 1)) if m.normalizar(d[0]) not in excluidas]
    print("Entrenamiento: %d | validación: %d | prueba manual: %d | reales: %d" %
          (len(datos), len(validacion), len(PRUEBA_MANUAL), len(reales)))
    idx = [m.rasgos(t) for t, _ in datos]
    y = np.zeros((len(datos), len(m.ETIQUETAS)), dtype=np.float32)
    for k, (_, et) in enumerate(datos):
        for e in et:
            y[k, m.ETIQUETAS.index(e)] = 1

    versiones = VERSIONES[1:2] if "--rapido" in sys.argv else VERSIONES
    resultados = []
    for oculta, epocas in versiones:
        t0 = time.time()
        registro = Registro({"validacion": validacion[:1500], "manual": PRUEBA_MANUAL, "reales": reales})
        pesos = a_json(entrenar(idx, y, oculta, epocas, SEMILLA, registro), oculta)
        red = m._Red(pesos)
        fila = {"oculta": oculta, "epocas": epocas, "pesos": pesos, "seg": time.time() - t0, "puntos": registro.puntos,
                "val": evaluar(red, validacion), "man": evaluar(red, PRUEBA_MANUAL),
                "reales": evaluar(red, reales) if reales else None}
        resultados.append(fila)
        print("  %3d neuronas, %2d épocas: validación %s | manual %s | reales %s  (%.0f s)" % (
            oculta, epocas, pct(fila["val"]), pct(fila["man"]),
            pct(fila["reales"]) if reales else "-", fila["seg"]))

    # Se elige SOLO con la validación sintética (la prueba manual y las reales no influyen en la elección).
    # A igual resultado, la más chica.
    mejor = max(resultados, key=lambda f: (f["val"]["exactos"], -f["oculta"], -f["epocas"]))
    destino = os.path.join(RAIZ, "backend", "modelo_foody.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(mejor["pesos"], fh, separators=(",", ":"))
    kb = os.path.getsize(destino) / 1024
    print("Elegida: %d neuronas, %d épocas -> %s (%.0f KB)" % (mejor["oculta"], mejor["epocas"],
                                                               os.path.normpath(destino), kb))
    for t, e, o in mejor["man"]["fallos"]:
        print("   FALLA manual:", t, e, o)
    for t, e, o in (mejor["reales"] or {"fallos": []})["fallos"]:
        print("   FALLA real:", t, e, o)
    escribir_informe(mejor, resultados, len(datos), kb, bool(reales))
    with open(RUTA_REGISTRO, "w", encoding="utf-8") as fh:
        json.dump({"fecha": str(date.today()), "etiquetas": list(m.ETIQUETAS), "umbral": m.UMBRAL,
                   "ejemplos": EJEMPLOS_ANIMACION, "n_entrenamiento": len(datos),
                   "elegida": {"oculta": mejor["oculta"], "epocas": mejor["epocas"]},
                   "versiones": [{"oculta": f["oculta"], "epocas": f["epocas"], "seg": round(f["seg"], 1),
                                  "final": {"validacion": f["val"]["exactos"] / f["val"]["total"],
                                            "manual": f["man"]["exactos"] / f["man"]["total"],
                                            "reales": (f["reales"]["exactos"] / f["reales"]["total"]) if f["reales"] else None},
                                  "puntos": f["puntos"]} for f in resultados]}, fh, ensure_ascii=False, separators=(",", ":"))
    print("Registro del entrenamiento:", os.path.normpath(RUTA_REGISTRO))


def escribir_informe(mejor, resultados, n_datos, kb, hay_reales):
    man, val, rea = mejor["man"], mejor["val"], mejor["reales"]
    inf = [
        "# Red neuronal propia de Foody", "",
        "Generado por `python scripts/entrenar_modelo_foody.py` el %s. Código: `backend/modelo_foody.py`. "
        "Pesos: `backend/modelo_foody.json` (%.0f KB). Textos de respuesta: `backend/conocimiento_foody.py`." % (date.today(), kb), "",
        "## Para qué sirve", "",
        "Cuando Gemini (y el proveedor de respaldo) no responden, Foody entiende la consulta sin IA externa. "
        "La red reconoce el tipo de comida, la restricción alimentaria y el precio aunque haya errores de tipeo "
        "o se usen otras palabras («pizeria», «sin tak», «pastas», «algo baratito»), y además la intención: si la "
        "persona saluda, agradece, se despide, pide ayuda, pregunta qué es algo («¿qué es sin TACC?»), cuenta una "
        "restricción que la base no cubre (lactosa, diabetes, alergias), opina sobre un local o pregunta algo que no "
        "es de comida.", "",
        "La red **entiende, no redacta**: las respuestas son textos escritos y revisados a mano, amables y con las "
        "advertencias de seguridad. Así nunca puede inventar un dato de salud. Solo agrega lo que entiende: nunca "
        "quita una restricción que detectaron las reglas.", "",
        "## Cómo es", "",
        "- **Tipo:** perceptrón multicapa (una capa oculta ReLU) con %d salidas sigmoides (clasificación "
        "multietiqueta): 3 restricciones, 17 tipos de comida, 2 de precio y 8 intenciones." % len(m.ETIQUETAS),
        "- **Entrada:** palabras, pares de palabras y trozos de 2 a 4 letras, llevados a %d posiciones con "
        "*hashing*. Los trozos de letras son lo que la hace tolerante a errores de tipeo." % m.DIM,
        "- **Entrenamiento:** %d frases sintéticas (plantillas formales y coloquiales, sinónimos, zonas reales de la "
        "base, errores de tipeo simulados y ejemplos negativos), optimizador Adam, entropía cruzada binaria. "
        "Solo numpy, sin GPU." % n_datos,
        "- **En producción:** inferencia en Python puro y pesos en int8. No suma dependencias al servidor gratis de Render.", "",
        "## Comparación de versiones", "",
        "Se entrenaron %d versiones y se eligió la mejor **solo con la validación sintética**, para que la prueba "
        "manual y las consultas reales sigan siendo una evaluación independiente." % len(resultados), "",
        "| Neuronas ocultas | Épocas | Validación sintética | Prueba manual | Consultas reales | Tiempo |",
        "|---|---|---|---|---|---|",
    ]
    for f in resultados:
        marca = " **(elegida)**" if f is mejor else ""
        inf.append("| %d%s | %d | %s | %s | %s | %.0f s |" % (
            f["oculta"], marca, f["epocas"], pct(f["val"]), pct(f["man"]),
            pct(f["reales"]) if f["reales"] else "-", f["seg"]))
    inf += ["", "## Resultados de la versión elegida", "",
            "| Conjunto | Aciertos exactos | Precisión | Exhaustividad |", "|---|---|---|---|",
            "| Validación sintética | %s | %.2f | %.2f |" % (pct(val), val["precision"], val["recall"]),
            "| Prueba escrita a mano | %s | %.2f | %.2f |" % (pct(man), man["precision"], man["recall"])]
    if rea:
        inf.append("| Consultas reales hechas a Foody | %s | %.2f | %.2f |" % (pct(rea), rea["precision"], rea["recall"]))
    inf += ["", "*Acierto exacto:* todas las etiquetas de la frase correctas, sin sobrantes. *Precisión:* de las "
            "etiquetas que puso la red, cuántas eran correctas (bajo = inventa). *Exhaustividad:* de las correctas, "
            "cuántas encontró (bajo = se le escapan).", "",
            "### Por grupo (prueba escrita a mano)", "", "| Grupo | Precisión | Exhaustividad |", "|---|---|---|"]
    inf += ["| %s | %.2f | %.2f |" % (g, pr, rc) for g, (pr, rc) in man["grupos"].items()]
    for nombre, r in (("prueba escrita a mano", man), ("consultas reales", rea)):
        if r and r["fallos"]:
            inf += ["", "### Fallos en %s" % nombre, "", "| Consulta | Esperado | Obtenido |", "|---|---|---|"]
            if nombre == "consultas reales":
                inf += ["| (%d frases; no se publican por privacidad) | | |" % len(r["fallos"])]
            else:
                inf += ["| %s | %s | %s |" % (t, ", ".join(e) or "(nada)", ", ".join(o) or "(nada)") for t, e, o in r["fallos"]]
    inf += ["", "## Límites", "",
            "- Honestidad sobre la evaluación: la prueba escrita a mano y las consultas reales no se usan para "
            "entrenar, pero sí se miraron durante el desarrollo para encontrar qué le faltaba aprender (se agregaron "
            "plantillas generales, nunca las frases de prueba). La prueba más independiente son consultas NUEVAS "
            "que la red no vio nunca (por ejemplo, las de producción exportadas con scripts/exportar_consultas_reales.py).",
            "- Los datos de entrenamiento son sintéticos. Las consultas reales se usan solo para evaluar; cuando "
            "haya más, se pueden sumar al entrenamiento.",
            "- No entiende negaciones («no soy celíaco»): igual que las reglas, en la duda agrega la restricción, que "
            "es lo más seguro.",
            "- No redacta: si la pregunta no encaja en ninguna intención conocida, Foody pide que la reformule.",
            "- La zona la siguen resolviendo las reglas (con corrección de tipeo aparte), porque son más de 1.600 "
            "nombres propios."]
    if not hay_reales:
        inf.append("- En esta corrida no había consultas reales etiquetadas (data/consultas_reales_etiquetadas.csv).")
    ruta = os.path.join(RAIZ, "docs", "pruebas", "modelo_propio.md")
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write("\n".join(inf) + "\n")
    print("Informe:", os.path.normpath(ruta))


if __name__ == "__main__":
    main()
