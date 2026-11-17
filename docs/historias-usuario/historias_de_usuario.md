# GastronomIA — Historias de usuario (HU-01 a HU-16)

Fuente: consignas del proyecto (sección 4). Formato: Como [rol], quiero [acción], para [beneficio]. Criterios de aceptación en Dado que / Cuando / Entonces.
Estado de implementación: se calcula solo en la auditoría automática (`AUDITORIA.bat`).

## HU-01 — Búsqueda mediante lenguaje coloquial con IA
**Historia:** Como usuario, quiero ingresar mi necesidad gastronómica mediante una consulta en lenguaje coloquial, para obtener resultados relevantes sin tener que configurar manualmente múltiples filtros de búsqueda.
- **CA-01 (Interpretación):** Dado que el usuario ingresa una consulta válida en lenguaje natural (ej. "Busco un restaurante vegano en Palermo"), cuando presiona "Buscar con IA", entonces el sistema debe identificar los parámetros relevantes (ubicación y preferencia).
- **CA-02 (Generación):** Dado que la IA interpreta correctamente los parámetros, cuando finaliza el procesamiento, entonces el sistema debe realizar la búsqueda en el dataset y mostrar los establecimientos coincidentes.
- **CA-03 (No interpretable):** Dado que la IA no puede determinar los parámetros de forma confiable, cuando finaliza el procesamiento, entonces el sistema debe informar que no pudo interpretar la solicitud y ofrecer la búsqueda por filtros manuales.
- **CA-04 (Sin resultados):** Dado que la consulta fue interpretada, cuando no existen establecimientos coincidentes, entonces el sistema debe informar que no hay resultados y permitir modificar los criterios.

## HU-02 — Advertencias sobre información de seguridad alimentaria
**Historia:** Como usuario con una restricción alimentaria, quiero conocer el nivel de certeza de la información nutricional o alimentaria presentada, para diferenciar los datos confirmados de aquellos inferidos y tomar una decisión informada.
- **CA-01 (Info inferida):** Dado que la información alimentaria fue inferida, cuando se muestra la ficha, entonces el sistema debe mostrar visiblemente: "Información inferida. Confirmar con el local".
- **CA-02 (Opciones sin TACC):** Dado que el usuario consulta opciones sin TACC, cuando se muestran los resultados, entonces el sistema debe presentar una advertencia indicando que la información de preparación y contaminación cruzada debe ser confirmada directamente con el local.
- **CA-03 (Ausencia de info):** Dado que el sistema no dispone de información suficiente sobre una dieta, cuando se muestra la ficha, entonces el sistema debe indicar "Sin datos" y no presentar la condición como confirmada.

## HU-03 — Manejo de consultas fuera de la cobertura geográfica
**Historia:** Como usuario de la aplicación, quiero que el bot me avise claramente cuando consulto por restaurantes de una zona de otro país (la base cubre toda la Argentina), para no perder tiempo buscando donde el sistema aún no dispone de datos.
- **CA:** Dado que el usuario pide recomendaciones para una ubicación fuera de Argentina (ej. Montevideo), cuando la IA procesa la entidad geográfica, entonces el sistema responde indicando que solo cuenta con datos de establecimientos de toda la Argentina, sin inventar resultados.
- **CA-02:** Dado que el usuario pide una ciudad o provincia de Argentina (ej. Córdoba, Rosario o Mendoza), cuando la IA procesa la entidad geográfica, entonces el sistema consulta la base y responde con los locales disponibles.

## HU-04 — Citación transparente de la fuente de datos
**Historia:** Como usuario analítico, quiero conocer la fuente pública de donde proviene la información del establecimiento recomendado, para tener mayor confianza sobre el origen y la vigencia del dato.
- **CA:** Dado que la IA genera una recomendación basada en la base de datos, cuando presenta la ficha, entonces incluye una cita explícita indicando el origen del registro (ej. "Fuente: Portal de Datos Abiertos CABA" o "Fuente: OpenStreetMap").

## HU-05 — Facilidad de contacto directo para confirmación de restricciones
**Historia:** Como usuario celíaco o con alergias alimentarias, quiero recibir el teléfono o enlace web del local recomendado junto a la sugerencia, para poder llamar y verificar de forma directa la seguridad de los platos antes de asistir.
- **CA:** Dado que el usuario solicita un lugar con restricciones alimenticias y el local cuenta con teléfono/web en el dataset, cuando el sistema entrega la recomendación, entonces adjunta la sugerencia de contactar al comercio junto con el número o enlace de acceso rápido.

## HU-06 — Refinamiento y filtrado conversacional de resultados
**Historia:** Como usuario indeciso, quiero repreguntarle al bot sobre los resultados presentados (ej. "de estos, ¿cuál es el más barato?"), para acotar las opciones en el mismo flujo conversacional sin volver a escribir la consulta completa.
- **CA:** Dado que el bot acaba de presentar una lista de restaurantes, cuando el usuario envía un mensaje de seguimiento pidiendo filtrar o reordenar, entonces la IA interpreta el contexto previo y filtra la lista dada sin reiniciar la búsqueda desde cero.

## HU-07 — Manejo de consultas sin resultados coincidentes
**Historia:** Como usuario con requerimientos muy específicos, quiero que el bot me informe explícitamente cuando no existan locales que cumplan con todos mis filtros, para no recibir información errónea ni inventada.
- **CA:** Dado que el usuario pide una combinación inexistente en la base de datos, cuando la intersección da cero resultados, entonces la IA aclara que no se encontraron locales exactos y ofrece flexibilizar algún criterio de búsqueda.

## HU-08 — Extracción inteligente de preferencias (Ambiente/Presupuesto)
**Historia:** Como usuario, quiero buscar lugares usando adjetivos informales sobre el ambiente o presupuesto (ej. "un lugar lindo para una cita y no muy caro"), para que el bot interprete la intención del encuentro y sugiera opciones acordes.
- **CA:** Dado que el usuario ingresa una frase con adjetivos informales, cuando la IA procesa el mensaje, entonces clasifica e infiere los atributos equivalentes (ej. Precio: Accesible, Ambiente: Romántico) y busca locales compatibles.

## HU-09 — Búsqueda específica de restricciones
**Historia:** Como usuario con restricciones alimenticias, quiero consultar lugares para comer expresándolo en lenguaje natural, para obtener opciones de forma rápida sin tener que navegar por menús complicados.
- **CA:** Dado que el usuario escribe "dónde puedo comer pizza sin TACC por Palermo", cuando la IA procese la consulta, entonces devuelve al menos 3 opciones de la base de datos ubicadas en Palermo con oferta certificada o apta celíaca.

## HU-10 — Búsqueda por ubicación actual
**Historia:** Como usuario, quiero buscar opciones gastronómicas cercanas a mi posición actual, para resolver dónde comer en el momento.
- **CA:** Dado que el usuario comparte su ubicación geográfica, cuando solicita una recomendación inmediata, entonces el sistema filtra y devuelve únicamente locales con opciones para sus restricciones en un radio no mayor a 15 cuadras.

## HU-11 — Registro de restricciones recurrentes
**Historia:** Como usuario recurrente, quiero que el bot registre mis restricciones alimenticias principales, para no tener que aclararlas en cada conversación.
- **CA:** Dado que el usuario declaró ser vegano en su primer uso, cuando inicie una nueva sesión y pida "sugerime un lugar para cenar", entonces el sistema aplica automáticamente el filtro vegano sin volver a preguntar.

## HU-12 — Múltiples restricciones simultáneas
**Historia:** Como usuario con múltiples necesidades de dieta, quiero registrar más de una restricción al mismo tiempo (ej. celíaco e intolerante a la lactosa), para que las sugerencias cumplan con todo mi perfil.
- **CA:** Dado que el usuario configura su perfil con dos o más restricciones, cuando solicita recomendaciones, entonces el sistema entrega únicamente locales que cumplan con la intersección de todas ellas.

## HU-13 — Reseñas en lenguaje natural
**Historia:** Como usuario, quiero expresarle al bot qué me pareció un lugar en mis propias palabras, para dar mi opinión sin tener que llenar formularios estructurados.
- **CA:** Dado que el usuario envía un mensaje informal (ej. "la hamburguesa vegana tremenda pero la música muy fuerte"), cuando la IA analice el texto, entonces extrae y almacena la valoración positiva de la comida y la negativa del ambiente, confirmando el guardado.

## HU-14 — Sugerencias basadas en historial
**Historia:** Como usuario habitual, quiero recibir sugerencias adaptadas a mis comentarios pasados, para descubrir lugares que coincidan con mi estilo y preferencias personales.
- **CA:** Dado que el usuario expresó previamente que no le gustan los lugares caros ni ruidosos, cuando pida una recomendación, entonces la IA prioriza opciones que se clasifiquen como accesibles y de ambiente tranquilo.

## HU-15 — Solicitud proactiva de feedback
**Historia:** Como usuario que asistió a un lugar recomendado, quiero que el bot me pregunte de forma proactiva cómo fue mi experiencia, para dejar mi reseña de forma rápida y oportuna.
- **CA:** Dado que el bot le recomendó un lugar hace 3 horas, cuando se cumpla el tiempo estimado de la visita, entonces el bot envía un mensaje automático preguntando si llegó a ir y qué tal estuvo para seguir ajustando sus gustos.

## HU-16 — Explicación de la recomendación
**Historia:** Como usuario, quiero que el bot me explique por qué me recomienda un lugar determinado, para entender el criterio detrás de la sugerencia.
- **CA:** Dado que el bot genera una recomendación basada en el historial, cuando muestra la opción, entonces incluye una explicación clara en lenguaje natural (ej. "Te sugiero este lugar porque buscas opciones sin TACC y valoras que tengan mesas afuera").
