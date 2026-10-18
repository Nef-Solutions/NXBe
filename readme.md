# OVEROL — Backend (API & Core de Negocio)

Plataforma digital para la conexión directa entre usuarios del hogar y profesionales de oficios calificados en Chile, eliminando intermediarios y promoviendo la formalización laboral mediante suscripciones mensuales y capacitación técnica.

Este repositorio contiene la arquitectura base y el núcleo de negocio del backend implementado bajo el patrón de **Monolito Modular** utilizando Python, Django REST Framework y PostgreSQL con PostGIS en Docker.

---

## 1. Herramientas y Requisitos Previos

Antes de ejecutar el proyecto, el equipo debe contar con las siguientes herramientas instaladas:

- **Python** (Instalado desde [python.org](https://www.python.org/downloads/) asegurando marcar la opción *"Add python.exe to PATH"*).
- **Docker Desktop** (Debe estar abierto y en ejecución para levantar la base de datos y la caché).
- **Visual Studio Code** (Con la extensión oficial de *Python* de Microsoft).
- **Git** para control de versiones.

---

## 2. Stack Tecnológico y Dependencias

Las librerías instaladas en el entorno virtual se encuentran en [`documentacion/requirements.txt`](documentacion/requirements.txt):

| Paquete | Versión instalada / Función |
| :--- | :--- |
| `Django` | Framework web principal y ORM. |
| `djangorestframework` | Construcción de endpoints REST. |
| `psycopg2-binary` | Driver conector entre Python y PostgreSQL. |
| `django-cors-headers` | Middleware para permitir peticiones HTTP desde el frontend. |
| `python-dotenv` | Manejo de variables de entorno seguras. |
| `Pillow` | Procesamiento y validación de imágenes (fotos de carnet/cédula). |
| `asgiref` / `sqlparse` / `tzdata` | Dependencias internas de Django (con soporte de zona horaria `America/Santiago`). |

---

## 3. Servicios en Docker (`docker-compose.yml`)

El proyecto orquesta dos servicios en contenedores para aislar la persistencia:

1. **`overol_db` (PostgreSQL 16 + PostGIS 3.4):**
   - **Imagen:** `postgis/postgis:16-3.4`
   - **Puerto:** `5432:5432`
   - **Base de datos:** `overol_db`
   - **Usuario:** `overol_user`
   - **Contraseña:** `overol_password`
   - **Volumen persistente:** `postgres_data`
   - *Finalidad:* Base de datos relacional y soporte geoespacial para comunas y radios de cobertura.
2. **`overol_redis` (Redis 7):**
   - **Imagen:** `redis:7-alpine`
   - **Puerto:** `6379:6379`
   - *Finalidad:* Caché de alto rendimiento y futuro broker de tareas asíncronas / websockets.

---

## 4. Arquitectura: Estructura del Monolito Modular

Todo el código de negocio se encuentra modularizado dentro del paquete `apps/` para evitar acoplamiento y permitir que cada módulo tenga sus propios modelos, servicios, validadores y tests:

```text
overol-backend/
├── apps/
│   ├── authentication/             # Módulo de Identidad y Verificación (Épica 001)
│   │   ├── migrations/             # Migraciones del modelo de usuario y perfil
│   │   ├── models.py               # User personalizado (roles) y ProfessionalProfile
│   │   ├── validators.py           # Algoritmo Módulo 11 (RUT) y sanitización anti-SQLi
│   │   ├── tests.py                # 4 pruebas unitarias (RUT, "Bernardo O'Higgins", SQLi)
│   │   └── apps.py                 # Configuración de app: 'apps.authentication'
│   │
│   ├── catalog/                    # Módulo de Catálogo y Búsquedas (Épica 002)
│   │   ├── migrations/             # Migraciones del catálogo
│   │   ├── models.py               # HomeZone, TradeCategory y Specialty
│   │   ├── services.py             # ProfessionalSearchService (búsqueda parametrizada)
│   │   ├── tests.py                # 4 pruebas unitarias (filtros por zona, oficio, keyword)
│   │   └── apps.py                 # Configuración de app: 'apps.catalog'
│   │
│   ├── visits/                     # Módulo de Visitas, Evaluaciones y Posventa (Épicas 004, 006, 009)
│   │   └── apps.py                 # Configuración de app: 'apps.visits'
│   │
│   └── assistant/                  # Módulo de Asistente IA / Chatbot de Diagnóstico (Épica 003)
│       └── apps.py                 # Configuración de app: 'apps.assistant'
│
├── core/                           # Configuración global del proyecto
│   ├── settings.py                 # Configurado con DB Docker, CORS, Media, Auth y Zona Horaria
│   ├── urls.py                     # Enrutador principal + soporte de archivos /media/
│   ├── wsgi.py / asgi.py           # Puntos de entrada del servidor
│   └── __init__.py
│
├── media/                          # Directorio donde se almacenan las fotos de cédulas
├── docker-compose.yml              # Orquestación de BD y Caché
├── manage.py                       # CLI de Django
└── README.md                       # Documentación técnica
```
## 5. Reglas de Negocio y Seguridad Implementadas
### A. Usuario y Verificación (Épica 001)
Roles: CLIENT (Cliente), PROFESSIONAL (Profesional), ADMIN (Administrador).

RUT Chileno: Validación matemática obligatoria con algoritmo Módulo 11 (validate_rut_chileno). Impide registros duplicados con el mismo RUT.

Cédula de Identidad: Campos id_card_front e id_card_back para carga de imágenes en media/verifications/.

Estados de Verificación: PENDING (Pendiente), APPROVED (Aprobado), REJECTED (Rechazado).

### B. Sanitización y Prevención de SQL Injection (Caso "Bernardo O’higgin’s . ")
El desafío: Admitir nombres con apóstrofes legítimos (O'Higgins, D'Angelo), apóstrofes tipográficos (’) y espacios/puntos sueltos al final, sin abrir vulnerabilidades de inyección SQL.

Sanitizador (sanitize_person_name):

Normaliza apóstrofes tipográficos (’ -> ').

Limpia espacios repetidos y signos de puntuación espurios al final ("Bernardo O’higgin’s . " se convierte de forma limpia y segura en "Bernardo O'higgin's").

Rechaza caracteres y secuencias peligrosas de inyección (;, --, /*, char()).

ORM Parametrizado: Todas las consultas se ejecutan con sentencias preparadas de PostgreSQL, asegurando que cadenas con comillas simples nunca alteren la sintaxis de la consulta SQL.

### C. Catálogo y Búsqueda de Profesionales (Épica 002)
Taxonomía:

HomeZone: Zonas del hogar (Cocina, Baño, Jardín, etc.).

TradeCategory: Oficios (Gasfitería, Electricidad, Cerrajería, etc.) asociados a zonas del hogar y con keywords descriptivas.

Specialty: Sub-especialidades técnicas ligadas a los profesionales calificados.

Servicio ProfessionalSearchService:

Regla estricta: Solo retorna profesionales con perfil en estado APPROVED.

Permite filtrado progresivo y combinado: por zona del hogar (zone_id), por categoría (category_id) y por término libre (keyword) utilizando objetos Q parametrizados.