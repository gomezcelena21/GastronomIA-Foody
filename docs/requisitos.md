# GastronomIA — Requisitos

## 1. Objetivo
Permitir que una persona busque, filtre y elija establecimientos gastronómicos de toda la Argentina con lenguaje natural, con foco en restricciones alimentarias (sin TACC, vegetariano, vegano), a partir de una base consolidada de fuentes públicas (Overture Maps, OpenStreetMap, BA Data, Google Places y guías comunitarias; 71.343 registros). La IA interpreta y redacta; **nunca es la fuente de los datos**.

## 2. Requisitos funcionales
Derivan de las 16 historias de usuario (`docs/historias-usuario/historias_de_usuario.md`). El estado real de cada una lo calcula la auditoría automática (`AUDITORIA.bat`).

| ID | Requisito | Historias |
|---|---|---|
| RF-01 | Búsqueda en lenguaje natural con IA (zona, cocina, restricción, presupuesto) | HU-01, 08, 09 |
| RF-02 | Advertencia de seguridad alimentaria: nunca afirmar aptitud al 100 %; indicar «Información inferida / Sin datos» | HU-02 |
| RF-03 | Informar que solo hay datos de Argentina y rechazar consultas de otros países, sin inventar resultados | HU-03 |
| RF-04 | Mostrar la fuente de cada dato y el contacto (teléfono/web) del local | HU-04, 05 |
| RF-05 | Mantener el contexto de la conversación para repreguntas | HU-06 |
| RF-06 | Informar cuando no hay resultados y sugerir flexibilizar criterios | HU-07 |
| RF-07 | Búsqueda por cercanía | HU-10 |
| RF-08 | Perfil del usuario con una o varias restricciones, guardado entre sesiones | HU-11, 12 |
| RF-09 | Reseñas en lenguaje natural con valoración por aspecto | HU-13 |
| RF-10 | Sugerencias según historial y feedback proactivo | HU-14, 15 |
| RF-11 | Explicar el motivo de cada recomendación | HU-16 |

## 3. Requisitos no funcionales
| ID | Requisito | Cómo se cumple |
|---|---|---|
| RNF-01 | Prototipo local reproducible | Python + FastAPI, React + Vite, PostgreSQL/PostGIS; `setup.bat` y `restart.bat` |
| RNF-02 | La IA no inventa datos | `validar_respuesta_ia()` bloquea teléfonos, links, mails y locales que no están en la base y garantías absolutas |
| RNF-03 | Disponibilidad ante fallas o cuota agotada de la IA | control de cuota y modo sin IA (`docs/cuota_gemini.md`); errores sin detalles internos |
| RNF-04 | Seguridad básica | SQL parametrizado, rate limit, CORS acotado, sin secretos en el código (`docs/seguridad_ciberseguridad.md`) |
| RNF-05 | Trazabilidad | historia ↔ caso de prueba ↔ prueba automática; auditoría automática |
| RNF-06 | Modelo de IA configurable | `GEMINI_MODEL` y `GEMINI_RPM` en `backend/.env` |

## 4. Limitaciones conocidas
- El 35 % de los registros no tiene barrio («No especificado») y parte de las coordenadas es aproximada.
- Hay pocos registros con oferta alimentaria confirmada: la información se presenta siempre como no garantizada.
- No hay reservas, delivery ni medios de pago. El dato de ambiente no existe en la base.
- Sin autenticación (el diseño no la incluye): el backend escucha solo en 127.0.0.1.
