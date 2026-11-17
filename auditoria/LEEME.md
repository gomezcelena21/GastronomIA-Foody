# Auditoría automática

Doble clic en `AUDITORIA.bat` (o `python auditoria/auditar.py`). En unos segundos:
1. Lee el código y comprueba que existe todo lo que dice el diseño (14 tablas, 9 endpoints, 8 métodos).
2. Revisa las 16 historias de usuario: qué código las implementa y qué pruebas las cubren.
3. Corre todas las pruebas automáticas y verifica que la planilla de casos diga la verdad.
4. Audita ciberseguridad (secretos, inyección SQL, descargas, CORS, dependencias).
5. Detecta documentos desactualizados y arma el checklist de las consignas.
6. Escribe `auditoria/reporte/reporte_auditoria.html` (se abre solo), `.md` y `.json`, y copia el resumen a `docs/auditoria_tpi.md`.

Estados: ✔ OK · ◐ PARCIAL (límite conocido, con motivo) · ⚠ ADVERTENCIA · ○ NO IMPLEMENTADA · ✋ MANUAL (no se puede verificar desde el código) · … NO EJECUTADO (necesita internet o una herramienta) · ✘ FALLA.
Si hay alguna ✘, el script termina con código 1.

Para mostrarle al profesor: ejecutar `AUDITORIA.bat`, y en el reporte señalar la sección 2 (historias) y la 3 (pruebas). Para ver que las pruebas son reales, romper algo a propósito (por ejemplo, borrar `validar_parametros` en `backend/diseno.py`) y volver a correr: aparece ✘.
No modifica el código del proyecto; solo escribe en `auditoria/reporte/` y `docs/auditoria_tpi.md`.
