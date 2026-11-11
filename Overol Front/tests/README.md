# Pruebas del front (AppTest)

Pruebas automáticas de las pantallas de Streamlit con `streamlit.testing.v1.AppTest`.
Hacen clic en los botones por su `key` y revisan la base y lo que queda en pantalla.

## Cómo correrlas

Desde la carpeta `Overol Front`, con el Python que tiene Streamlit:

```powershell
python tests/correr_pruebas.py                    # todas, en modo local y api
python tests/correr_pruebas.py busqueda tickets   # solo algunas
python tests/correr_pruebas.py --modo local       # un solo modo
python tests/correr_pruebas.py --base-nueva       # base demo desde cero, sin copiar overol.db
python tests/correr_pruebas.py -v                 # muestra cada verificación
```

Al final aparece `TODO OK` o la lista de verificaciones que fallaron.
Requisitos: `pip install -r requirements.txt` (incluye `cryptography`) y Pillow, que viene con Streamlit.

## Qué protege el corredor

- **Base:** cada prueba trabaja sobre una **copia temporal** del front, que incluye una copia de `overol.db`. Si `overol.db` no existe, la app crea la base demo.
  El `overol.db` real no se modifica, y las copias se borran al terminar.
- **Clave:** cada copia usa una **clave de prueba propia**. Nunca se lee ni se crea la clave real de los documentos (`OVEROL_CLAVE_DOCUMENTOS` se ignora durante las pruebas).
- **Archivos que no se copian:** `documentos_verificacion/`, `*.key`, `.env` ni `__pycache__`.
- **Backend:** el modo `api` no necesita el backend encendido. Las pruebas entran con la sesión ya iniciada y `comun.py` reemplaza `requests.request` por un **backend simulado**:
  `/api/catalog/` responde con los profesionales de la copia SQLite en el formato del backend (mismos ids), y cualquier otra ruta falla como si el backend estuviera apagado.
  En modo local, registra cualquier intento de salir a la red.
  `prueba_modo_api.py` usa su propio backend simulado para el login y el registro.
  Las respuestas se armaron leyendo el código del backend: **no reemplazan una prueba contra el backend real**.

No corras un archivo `prueba_*.py` directo: se niega a correr sin una copia y sin la clave de prueba.

## Suites

| Archivo | Qué revisa |
|---|---|
| `prueba_navegacion.py` | Barra de los 4 roles (orden y que todo abra), cada rol solo ve lo suyo, cerrar sesión |
| `prueba_busqueda.py` | Palabra clave sin distinguir mayúsculas ni tildes, varias palabras, filtros, «Limpiar búsqueda», visitante sin nombres |
| `prueba_solicitudes.py` | Reglas al crear (días y horas, duplicadas), contacto solo con la solicitud aceptada, rechazo, finalización de ambas partes, cancelaciones, vencimiento a 72 h |
| `prueba_notificaciones.py` | Contador en la barra, marcar una o todas como leídas, cada uno ve solo las suyas |
| `prueba_tickets.py` | Abrir con asunto, responder, resolver, reabrir, límites de 100 y 500 caracteres |
| `prueba_indicadores_reclamos.py` | Cifras de Indicadores, reclamo de posventa y mediación del admin |
| `prueba_admin_panel.py` | Bitácora con filtros y paginación, suspender y reactivar con motivo |
| `prueba_verificacion.py` | Mensajes profesional ↔ admin y decisión con motivo |
| `prueba_cifrado.py` | Migración de documentos antiguos sin borrar originales, solo el admin descifra, registro de cada vista |
| `prueba_catalogo_api.py` | Fase 3: tarjetas y perfiles desde la API, filtros enviados al backend, paginación, visitante sin nombres, «Disponible pronto», backend caído. En modo local, que el catálogo siga en SQLite |
| `prueba_modo_api.py` | Con un backend simulado: registro de profesional (comunas y oficio del backend, oficio inexistente), reglas de contraseña, bloqueo 429, días con nombre completo. En modo local, que nada salga a la red |

`comun.py` reúne las utilidades: sesión simulada, búsqueda de los usuarios demo por correo y `check`.

## Límites conocidos

- **No es un navegador.** AppTest no muestra el diseño: los estilos, el CSS y la barra fija hay que mirarlos a mano.
- **Botón de mantener presionado:** es un componente propio que AppTest no puede pulsar. La cancelación del cliente se prueba llamando a la función de la base.
- **Subida de documentos:** AppTest no sube archivos, así que `prueba_cifrado.py` reemplaza `st.file_uploader` durante esa parte.
