# Por qué el chat "se moría" a las 4 consultas (cuota de Gemini)

## Configuración actual (15/11/2026)
| Ajuste | Valor |
|---|---|
| Modelo (`GEMINI_MODEL`) | `gemini-3.5-flash-lite` (plan gratis: ~15 RPM y 500 pedidos por día) |
| `GEMINI_RPM` | 10 pedidos por minuto (deja margen para los reintentos ante 429) |
| `GEMINI_MAX_ESPERA` | 20 s: si el minuto está lleno, espera y responde con IA en vez de caer a modo sin IA |
| `GEMINI_TIMEOUT` | 12 s por pedido |

Con ~3 pedidos por consulta, el plan gratis alcanza para **unas 3 consultas por minuto** y del orden de **150 consultas por día** en total (antes, con `gemini-3.6-flash`, eran 5 RPM y 20 pedidos diarios: ~5-10 consultas por día).

## Causa
- El límite del plan gratuito de Gemini no es de tokens: es de **pedidos por minuto (RPM)**, tokens por minuto y **pedidos por día (RPD)**, por modelo y por proyecto. El "millón de tokens" es el tamaño de la ventana de contexto, no la cuota.
- Los valores exactos de cada modelo no figuran en la documentación pública: se ven en Google AI Studio (límites de uso). En pruebas publicadas en octubre de 2026 el plan gratis de un modelo Flash permitía 5 pedidos por minuto y 20 por día. El comentario del propio código (`gemini_service.py`) también habla de ~5 por minuto.
- **Cada mensaje del chat usa al menos 2 pedidos**: uno con la pregunta y otro al devolverle a Gemini el resultado de la búsqueda en la base (function calling). Si encadena herramientas (buscar + ver detalle) son 3 o más; el bucle admite hasta 6.
- Resultado: 2 consultas gastan ~4-5 pedidos y a la 3.ª o 4.ª Google responde 429 (RESOURCE_EXHAUSTED). El código anterior no esperaba ni reintentaba: devolvía un error.
- Agravante menor: cada respuesta de búsqueda (≈2.300 tokens con 10 locales) quedaba completa en el historial de la conversación.

## Qué se cambió
| Cambio | Dónde |
|---|---|
| Control de cuota: nunca más de `GEMINI_RPM` pedidos por minuto (10 por defecto); espera hasta `GEMINI_MAX_ESPERA` s (20) en vez de fallar | `backend/cuota.py`, `ChatService._enviar` |
| Ante un 429 lee cuánto esperar, reintenta una vez y distingue límite por minuto de límite diario | `cuota.clasificar_error`, `cuota.enviar_con_cuota` |
| **Modo sin IA**: si no hay cuota, el chat igual responde con datos reales de la base (interpreta zona, cocina y restricción por palabras clave) y avisa por qué | `diseno.armar_respuesta_sin_ia`, `ChatService._sin_ia` |
| Menos tokens: se quitan campos que la IA no usa (coordenadas, provincia, etc.) y la búsqueda devuelve 8 locales por defecto en vez de 10 | `diseno.compactar_para_ia` |
| Mensaje claro en pantalla si el backend limita al usuario (429/422) | `frontend/src/App.tsx` |

## Qué esperar
Con ~10 pedidos por minuto la IA alcanza para **unas 3 consultas por minuto** (cada consulta usa 2-4 pedidos), sin contar las que se responden en modo sin IA mientras el minuto se libera. Si se agota el límite del día, el modo sin IA se mantiene hasta que se renueve la cuota.

El aviso que ve la persona **no nombra a Gemini**. Indica que Foody alcanzó su límite diario, muestra resultados de la base y calcula la hora de renovación desde la medianoche del Pacífico a hora de Argentina (05:00 en invierno, 04:00 en verano). El texto exacto está en `diseno.py` y se prueba en `tests/test_diseno.py`.

## Cómo tener más margen
1. Mirar en Google AI Studio los límites de uso de tu modelo (`GEMINI_MODEL` en `backend/.env`) y probar con otro modelo gratuito que tenga más pedidos por minuto o por día. Los Flash-Lite son los que más cupo dan (`gemini-3.5-flash-lite`: ~15 RPM y 500 por día).
2. Si tu límite real es distinto de 10, ajustar `GEMINI_RPM` en `backend/.env` (dejá 2-3 pedidos de margen para los reintentos).
3. Activar facturación (nivel de pago): sube los límites.
4. Reducir los pedidos por mensaje (mejora futura): que el backend haga la primera búsqueda y le pase a Gemini los resultados en el mismo pedido, así cada consulta usa 1 pedido.

## Pruebas
`tests/test_cuota.py` (15 pruebas) y `tests/test_casos_uso_ia.py` (TC-024 a TC-027: seis consultas seguidas, 429 por minuto, límite diario). Lo que no se pudo probar en el entorno donde se armó: el comportamiento real con Gemini; hay que verlo con el caso manual TC-024 del Excel.

## Modo sin IA conversacional

Cuando no hay cuota, `diseno.armar_respuesta_sin_ia` responde con reglas y plantillas (sin red neuronal, sin costo y sin cuota):

- **Charla:** saluda, agradece, se despide y explica qué puede hacer, sin consultar la base.
- **Entiende** barrio, tipo de comida y restricciones (sin TACC, vegano, vegetariano) y se lo dice a la persona ("pizzería sin TACC en Palermo").
- **Seguimientos:** con el historial de la sesión entiende «¿y sin TACC?» o «¿y en Belgrano?». Una búsqueda nueva con su propia zona no arrastra filtros anteriores.
- **Sin resultados:** prueba sin el tipo de comida y después sin la zona, y lo explica. **Nunca afloja una restricción alimentaria.**
- **Seguridad:** solo muestra datos reales de la base, con su fuente y la advertencia de contaminación cruzada. Si la zona es de otro país (la base solo cubre Argentina), no consulta nada.
- **Aviso de cuota:** el mensaje largo solo aparece la primera vez; después usa uno corto.

Pruebas: `tests/test_modo_sin_ia.py`.
