"""
GastronomIA - Lo que Foody sabe explicar en el modo sin IA (sin Gemini).

La red neuronal propia (modelo_foody.py) reconoce QUÉ pregunta la persona («¿qué es sin TACC?»,
«¿qué diferencia hay entre vegano y vegetariano?», «los lácteos me caen mal») y Foody responde con
estos textos, escritos y revisados a mano: amables, claros y con las advertencias de seguridad.
La red no redacta: así nunca puede inventar un dato de salud.

Reglas para editar estos textos:
  - Nunca prometer que algo es seguro: recomendar siempre confirmar con el local.
  - No dar consejos médicos: ante dudas de salud, sugerir consultar a un profesional.
  - Tono cálido y respetuoso, en español rioplatense, sin Markdown.
"""

from typing import Dict, Iterable, List, Optional

CONFIRMAR = "Igual, te recomiendo confirmar siempre con el local antes de pedir."

RESTRICCIONES: Dict[str, str] = {
    "sin_tacc": (
        "Sin TACC quiere decir sin trigo, avena, cebada ni centeno, los cereales que tienen gluten. Es lo que necesitan "
        "las personas celíacas: para ellas hasta una miga puede hacer daño, por eso importa también evitar la "
        "contaminación cruzada (usar la misma tabla, aceite o cuchillo que con comida con gluten). En Argentina los "
        "productos aptos llevan el logo oficial «Sin TACC». " + CONFIRMAR
    ),
    "vegano": (
        "La alimentación vegana no incluye nada de origen animal: ni carne ni pescado, y tampoco lácteos, huevo ni miel. "
        "Se basa en verduras, legumbres, cereales, frutas, frutos secos y semillas."
    ),
    "vegetariano": (
        "La alimentación vegetariana no incluye carne ni pescado, pero en general sí lácteos y huevo "
        "(por eso también se la llama ovolactovegetariana)."
    ),
}
DIFERENCIA_VEGANO_VEGETARIANO = (
    "La diferencia es que la persona vegetariana deja la carne y el pescado pero suele comer lácteos y huevo, "
    "mientras que la vegana no come nada de origen animal (tampoco lácteos, huevo ni miel). Todo plato vegano "
    "sirve para alguien vegetariano, pero no al revés."
)

COCINAS: Dict[str, str] = {
    "pizzeria": "Las pizzerías porteñas son un clásico: pizza a la piedra o al molde, fugazzeta, faina y muzza. "
                "Si sos celíaco o celíaca, buscá las que tienen prepizzas sin TACC y horno separado.",
    "italiana": "La cocina italiana es la de las pastas (ravioles, ñoquis, sorrentinos, lasagna), el risotto y las "
                "salsas como la bolognesa o la pesto. Ojo: la pasta común tiene trigo, así que sin TACC hay que pedir "
                "la versión especial.",
    "hamburguesa": "Las hamburgueserías ofrecen hamburguesas de carne y muchas veces también vegetarianas o veganas "
                   "(de legumbres, hongos o soja), con papas fritas de acompañamiento.",
    "japonesa": "La cocina japonesa incluye el sushi (arroz con pescado o verduras), el sashimi, el ramen y las "
                "tempuras. Para celíacos: la salsa de soja común tiene trigo, conviene pedir la versión sin TACC.",
    "asiatica": "Comida asiática reúne cocinas como la tailandesa, la coreana, la vietnamita o los wok: "
                "sabores con jengibre, curry, leche de coco y salteados.",
    "china": "La cocina china tiene arroz y fideos salteados, chop suey, dim sum y platos agridulces. "
             "Muchas salsas llevan soja con trigo, así que si necesitás sin TACC, preguntá.",
    "parrilla": "La parrilla es el asado argentino: cortes como vacío, bife de chorizo o entraña, chorizo, morcilla "
                "y achuras. Si no comés carne, muchas tienen provoleta y verduras asadas.",
    "cafe": "Los cafés y cafeterías son ideales para desayunar, merendar o hacer un brunch: café, medialunas, "
            "tostados y algo dulce.",
    "mexicana": "La comida mexicana tiene tacos, burritos, nachos, quesadillas y guacamole. Las tortillas de maíz "
                "no tienen gluten, pero las de harina sí: si sos celíaco o celíaca, preguntá cuáles usan.",
    "peruana": "La cocina peruana es famosa por el ceviche (pescado marinado en limón), el lomo saltado, el arroz "
               "chaufa y el ají de gallina.",
    "sandwicheria": "En las sandwicherías vas a encontrar sándwiches de miga, lomitos, sánguches calientes y fríos.",
    "comida_rapida": "La comida rápida es para resolver al paso: panchos, papas fritas, hamburguesas o porciones.",
    "pasteleria": "Las pastelerías tienen tortas, tartas, alfajores, masas y postres. Hay cada vez más con "
                  "opciones sin TACC o veganas.",
    "panaderia": "En las panaderías hay pan, facturas, medialunas y bizcochitos. Para sin TACC hacen falta "
                 "panaderías especializadas, porque la harina en el aire contamina.",
    "heladeria": "Las heladerías argentinas son de helado artesanal: dulce de leche, chocolate, frutales y "
                 "al agua. Muchos sabores no tienen TACC, pero el cucurucho común sí: pedilo en vasito.",
    "empanadas": "Las empanadas son un clásico argentino: de carne, pollo, jamón y queso, humita o verdura, "
                 "al horno o fritas, y con estilos regionales como las salteñas o las tucumanas.",
    "comida_casera": "La comida casera es la de bodegón o la de viandas: milanesas, guisos, tortillas, pastas y "
                     "platos abundantes como en casa.",
}

NOMBRES = {
    "sin_tacc": "sin TACC", "vegano": "vegano", "vegetariano": "vegetariano",
    "pizzeria": "pizzería", "italiana": "comida italiana", "hamburguesa": "hamburguesas", "japonesa": "comida japonesa",
    "asiatica": "comida asiática", "china": "comida china", "parrilla": "parrilla", "cafe": "café",
    "mexicana": "comida mexicana", "peruana": "comida peruana", "sandwicheria": "sandwichería",
    "comida_rapida": "comida rápida", "pasteleria": "pastelería", "panaderia": "panadería", "heladeria": "heladería",
    "empanadas": "empanadas", "comida_casera": "comida casera",
}

OTRA_RESTRICCION = (
    "Gracias por contarme, es importante. Por ahora en nuestra base solo tengo datos de opciones sin TACC, veganas "
    "y vegetarianas, así que no puedo saber qué locales son aptos para otras necesidades (por ejemplo sin lactosa, "
    "para personas con diabetes o con alergias). Puedo mostrarte locales de la zona que quieras, pero te pido que "
    "consultes con el local antes de pedir, y si tenés dudas de salud, con un profesional."
)
NOTA_OTRA_RESTRICCION = ("Te cuento que no tengo datos de esa necesidad alimentaria en particular, así que por favor "
                         "confirmalo con el local antes de pedir.")
FUERA_DE_TEMA = (
    "Perdón, en eso no te puedo ayudar: soy Foody y solo sé de comida y de dónde comer en Argentina. "
    "Si querés, contame qué tenés ganas de comer y en qué zona, y te busco opciones."
)
OPINION = (
    "¡Gracias por contarme tu experiencia! Lamento si no fue lo que esperabas, y me alegra si estuvo bueno. "
    "¿Te busco otra opción? Decime la zona y qué tenés ganas de comer."
)
QUE_ES_GENERAL = (
    "Te puedo explicar qué es sin TACC, qué es la comida vegana o vegetariana y en qué consisten tipos de comida "
    "como parrilla, pizzería, sushi, comida peruana o mexicana. ¿Sobre cuál querés saber?"
)
SOLO_PRECIO = ("¡Dale, busco algo que cuide el bolsillo! ¿En qué zona o ciudad querés comer? Si me decís también "
               "qué tenés ganas de comer, mejor.")


def explicar(etiquetas: Iterable[str]) -> Optional[str]:
    """Texto que explica las restricciones y tipos de comida pedidos (máximo 3), o None si no hay ninguno."""
    etiquetas = list(dict.fromkeys(etiquetas))
    partes: List[str] = []
    if "vegano" in etiquetas and "vegetariano" in etiquetas:
        partes.append(DIFERENCIA_VEGANO_VEGETARIANO)
        etiquetas = [e for e in etiquetas if e not in ("vegano", "vegetariano")]
    for e in etiquetas:
        texto = RESTRICCIONES.get(e) or COCINAS.get(e)
        if texto:
            partes.append(texto)
    if not partes:
        return None
    return " ".join(partes[:3])


def invitacion(etiquetas: Iterable[str]) -> str:
    """Cierre amable que ofrece buscar lo que se explicó."""
    opciones = {"sin_tacc": "opciones sin TACC", "vegano": "opciones veganas", "vegetariano": "opciones vegetarianas"}
    nombres = [opciones.get(e) or "lugares de %s" % NOMBRES[e] for e in etiquetas if e in NOMBRES][:2]
    if not nombres:
        return "¿Querés que te busque opciones? Decime en qué zona."
    return "¿Querés que te muestre %s? Decime en qué zona o ciudad." % " y ".join(nombres)
