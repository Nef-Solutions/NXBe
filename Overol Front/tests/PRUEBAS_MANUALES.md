# Pruebas manuales contra el backend real

Las pruebas automáticas usan una imitación del backend. Estas se hacen a mano, con el backend Django de verdad y un navegador.
Anota en cada caso ✅ o ❌ y lo que viste.

**Etapa B:** login, bloqueo, registro, completar perfil, Mi perfil, contraseñas y sesión recordada.

## Preparación (una vez)

```powershell
# 1. Backend (desde la carpeta backend del repositorio)
cd "C:\Users\benja\Documents\NXBe_repo\backend"
docker compose up -d
$env:PYTHONDONTWRITEBYTECODE = "1"
$py = "C:\Users\benja\Documents\Overol_envs\backend_venv\Scripts\python.exe"
& $py manage.py migrate
& $py manage.py seed_demo
& $py manage.py runserver 127.0.0.1:8000     # déjala abierta

# 2. Front (otra ventana)
cd "C:\Users\benja\Documents\NXBe_repo\Overol Front"
& "C:\Users\benja\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe" app.py
```

**Usuarios de `seed_demo`:** contraseña `OverolDemo123!`.

| Rol | Correo |
|---|---|
| Cliente | `cliente1@demo.overol.cl`, `cliente2@demo.overol.cl` |
| Profesional | `profesional1@demo.overol.cl` a `profesional3@demo.overol.cl` |
| Admin | `admin@demo.overol.cl` (también entra a `/admin/` de Django) |

**Antes de empezar:** confirma que la carpeta del front **no** tiene `overol.db`, o bórralo. Al terminar, revisa que siga sin existir.

## Casos

| # | Caso | Pasos | Resultado esperado |
|---|---|---|---|
| 1 | Registro de cliente | «Ingresar o registrarme» → «Crear cuenta» → Cliente, datos válidos y RUT nuevo → «Crear cuenta» | Aviso «Cuenta creada correctamente». En `/admin/` → Users aparece la cuenta, con rol `CLIENT`, teléfono, dirección y comuna |
| 2 | Registro de profesional con un oficio que el backend no tiene | Profesional, oficio **Pintura**, comunas Santiago y Ñuñoa | Error: «El oficio «Pintura» todavía no está disponible…», con la lista de oficios del backend. No se crea ninguna cuenta |
| 3 | Registro de profesional | Igual, con oficio **Gasfitería** y 4 años de experiencia | Cuenta creada. En `/admin/` → Professional profiles: `coverage_communes` = Santiago y Ñuñoa, estado `PENDING`. En Professional trades: un oficio Gasfitería con 4 años |
| 4 | Contraseña débil | Registro con la contraseña `password123` | Error «La contraseña no cumple las reglas de seguridad del servidor:» con la lista de reglas |
| 5 | Correo repetido | Registro con `cliente1@demo.overol.cl` | Error «Correo: …ya existe…» |
| 6 | Login correcto | `cliente1@demo.overol.cl` con «Mantener mi sesión» marcado | Entra como cliente. La barra muestra Inicio, Buscar profesionales, Mi perfil y Quiénes somos |
| 7 | Clave incorrecta | `cliente2@demo.overol.cl` con una clave equivocada | «Correo o contraseña incorrectos. Tras 3 intentos fallidos, la cuenta se bloquea por seguridad durante 5 minutos.» |
| 8 | Bloqueo | 3 claves equivocadas seguidas y después la clave correcta | «Cuenta bloqueada por intentos fallidos. Intenta de nuevo en 5 minutos» (o 4, según el tiempo). Pasados 5 minutos, entra |
| 9 | Completar perfil | En `/admin/` → Users, borra el teléfono y la dirección de `cliente2` → entra con esa cuenta | Pide «Completa tu perfil» antes de mostrar la barra. Al guardar teléfono, dirección y comuna, entra. En `/admin/` quedan guardados |
| 10 | Mi perfil del cliente | Cliente → Mi perfil → cambia la dirección → Guardar | Aviso «Tus datos fueron actualizados». En `/admin/` la dirección cambió. No aparece «Preferencia de contacto», porque el backend no la guarda para clientes |
| 11 | Mi perfil del profesional | `profesional1` → Mi perfil → preferencia «Correo electrónico», un titular y una presentación → Guardar | En `/admin/` → Professional profiles: `contact_preference`, `headline` y `bio` actualizados. Arriba dice «Tu identidad está verificada» |
| 12 | Profesional pendiente | Entra con el profesional del caso 3 | Aviso «Tu cuenta está pendiente de verificación» y no aparece en «Buscar profesionales». Apruébalo en `/admin/` (Professional profiles → `verification_status` = APPROVED) y aparece en el catálogo |
| 13 | Cambiar contraseña | Mi perfil → «Cambiar contraseña» con la actual equivocada, y después con la correcta | Primero: «La contraseña actual no es correcta». Después: «Contraseña actualizada», y la nueva clave sirve para entrar |
| 14 | Recuperar contraseña | Pantalla de ingreso → «¿Olvidaste tu contraseña?» → `cliente1@demo.overol.cl` | Mensaje «Si el correo está registrado, recibirás instrucciones…». En la **ventana de runserver** se imprime el correo con el enlace (el backend usa correo por consola) |
| 15 | Recargar con la sesión recordada | Con el caso 6 abierto, recarga la página (F5) | Sigue dentro, sin pedir la contraseña |
| 16 | La cookie no lleva tokens | F12 → Application → Cookies → `localhost:8501` | Hay una sola cookie `overol_session`, con un valor aleatorio largo, SameSite = Lax. **No** contiene `eyJ…` (un token JWT), ni el correo ni el nombre |
| 17 | Cerrar sesión | «Cerrar sesión» en la barra lateral → recarga la página | Vuelve a la vista de visitante y al recargar no entra solo. La cookie `overol_session` desaparece |
| 18 | Cerrar y reabrir el navegador | Entra con «Mantener sesión», cierra el navegador entero y vuelve a abrir `localhost:8501` | Sigue dentro |
| 19 | Reinicio del servidor del front | Con la sesión recordada, detén el front (Ctrl+C), arráncalo de nuevo y recarga | Pide iniciar sesión otra vez (el token vivía en la memoria del servidor). La cookie vieja se borra |
| 20 | Sin «Mantener sesión» | Entra con la casilla desmarcada → recarga la página | Al recargar vuelve a la vista de visitante |
| 21 | Cuenta desactivada | Con un cliente adentro, en `/admin/` → Users desmarca **Active** (o `account_status` = DEACTIVATED con Active desmarcado) → espera 1 minuto y haz clic en cualquier sección | Se cierra la sesión con el aviso «Tu sesión terminó». Si intenta entrar: «Correo o contraseña incorrectos» |
| 21b | Cuenta suspendida | Igual, pero solo `account_status` = SUSPENDED (Active marcado) | **Limitación conocida del backend:** la sesión abierta sigue funcionando hasta que vence el token de renovación, porque SimpleJWT solo revisa `is_active`. Un ingreso nuevo sí se rechaza. Está en el pedido a Nefi |
| 22 | Admin | Entra con `admin@demo.overol.cl` | Solo aparece «Quiénes somos», con el aviso de usar `/admin/` de Django mientras se conecta el panel |
| 23 | Backend apagado | Detén runserver y recarga el front | La portada abre sin cifras ni destacados. «Profesionales» muestra «No se pudo cargar el catálogo». Al intentar ingresar: «No se pudo conectar con el servidor de Overol» |
| 24 | Sin SQLite | Al terminar todo lo anterior | La carpeta del front sigue **sin** `overol.db` |
