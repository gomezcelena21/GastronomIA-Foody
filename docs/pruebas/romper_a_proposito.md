# Romper a propósito (prueba de las pruebas)

Ejecutado el 2026-11-15 con Python 3.12.3 por `python scripts/romper_a_proposito.py --informe`.

Se introduce un error a propósito en una **copia temporal** de `backend/diseno.py` (tu código no se toca) y se corren las pruebas (test_diseno, test_casos_uso_ia, test_caja_blanca, test_caja_negra, test_modo_sin_ia, test_comercios, test_evaluacion_interprete). Si alguna falla, el error fue **detectado**; si todas pasan, **sobrevivió** y falta una prueba.

**Resultado: 12 de 12 errores detectados.**

| ID | Error introducido | Resultado | Pruebas que fallaron |
|---|---|---|---|
| M1 | El mínimo de resultados pasa de 1 a 0 (valor límite) | DETECTADO | 3 |
| M2 | Se quita el control de que la descarga quede dentro de la carpeta permitida (BUG-01) | DETECTADO | 1 |
| M3 | Se invierte la validación de provincia (acepta las de afuera) | DETECTADO | 7 |
| M4 | Error de uno en el limitador: deja pasar un mensaje de más (> en vez de >=) | DETECTADO | 3 |
| M5 | El mensaje ya no se recorta a 1.500 caracteres | DETECTADO | 3 |
| M6 | El modo sin IA afloja también la restricción sin TACC al no encontrar resultados | DETECTADO | 3 |
| M7 | El seguimiento deja de retomar la zona de la consulta anterior | DETECTADO | 2 |
| M8 | Se cambia la advertencia alimentaria (ya no pide confirmar con el local) | DETECTADO | 1 |
| M9 | Los datos de comercios ya no se limpian de < y > antes de dárselos a la IA | DETECTADO | 1 |
| M10 | «Lanús» deja de entenderse como «Lanús Oeste» (zona con datos) | DETECTADO | 1 |
| M11 | Un partido de GBA sin datos deja de reconocerse (se ignora la zona) | DETECTADO | 4 |
| M12 | El detector de órdenes para la IA deja de reconocer «ignorá las instrucciones» | DETECTADO | 1 |

Es la regla de oro 4 del apunte de la unidad 7: *verificá que la prueba pueda fallar*.
