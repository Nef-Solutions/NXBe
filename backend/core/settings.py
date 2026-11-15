"""
Django settings for core project.
"""

from pathlib import Path
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-change-this-secret-key-0123456789abcdef')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

def _env_list(name, default=''):
    """Lista separada por comas desde una variable de entorno (sin espacios ni vacíos)."""
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


ALLOWED_HOSTS = _env_list('ALLOWED_HOSTS', '127.0.0.1,localhost')

# Render publica el dominio del servicio en esta variable: se permite sin configurarlo a mano.
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Orígenes https desde los que se envían formularios con CSRF (por ejemplo el login de /admin/).
CSRF_TRUSTED_ORIGINS = _env_list('CSRF_TRUSTED_ORIGINS')
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Librerías de terceros
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',

    # Módulos del Monolito Modular de Overol
    'apps.authentication',
    'apps.catalog',
    'apps.visits',
    'apps.assistant',
    'apps.payments',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # <-- Crucial: debe ir arriba de CommonMiddleware
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Sirve /static/ cuando corre con Gunicorn (Docker)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database (PostgreSQL en Docker, o la URL completa que entrega el proveedor en producción)
if os.getenv('DATABASE_URL'):
    import dj_database_url

    DATABASES = {
        'default': dj_database_url.parse(
            os.environ['DATABASE_URL'],
            conn_max_age=int(os.getenv('DATABASE_CONN_MAX_AGE', '60')),
            conn_health_checks=True,
        )
    }
elif os.getenv('DATABASE_ENGINE') == 'sqlite3':
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': os.getenv('SQLITE_NAME', ':memory:')}}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'overol_db'),
            'USER': os.getenv('POSTGRES_USER', 'overol_user'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'overol_password'),
            'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization (Configurado para Chile)
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Destino de collectstatic (lo usa la imagen Docker)


# Configuración de archivos subidos por usuarios (Media - Cédulas y perfiles)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
PRIVATE_MEDIA_ROOT = os.getenv('PRIVATE_MEDIA_ROOT', os.path.join(BASE_DIR, 'private_media'))

# Almacenamiento externo compatible con S3 (por ejemplo Supabase Storage) para producción,
# donde el disco del servidor se borra en cada despliegue. Sin estas variables se usa el disco local.
#   S3_MEDIA_BUCKET    bucket PÚBLICO para fotos de perfil y certificaciones
#   S3_PRIVATE_BUCKET  bucket PRIVADO para las cédulas (solo se leen a través de la API)
S3_MEDIA_BUCKET = os.getenv('S3_MEDIA_BUCKET', '')
S3_PRIVATE_BUCKET = os.getenv('S3_PRIVATE_BUCKET', '')
AWS_S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL') or None
AWS_S3_REGION_NAME = os.getenv('S3_REGION') or None
AWS_ACCESS_KEY_ID = os.getenv('S3_ACCESS_KEY_ID') or None
AWS_SECRET_ACCESS_KEY = os.getenv('S3_SECRET_ACCESS_KEY') or None
AWS_S3_ADDRESSING_STYLE = 'path'
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
if S3_MEDIA_BUCKET:
    # URL pública del bucket, por ejemplo https://<ref>.supabase.co/storage/v1/object/public/media
    _media_public_url = os.getenv('S3_MEDIA_PUBLIC_URL', '').rstrip('/')
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': S3_MEDIA_BUCKET,
            'querystring_auth': False,
            'custom_domain': _media_public_url.split('://', 1)[-1] or None,
        },
    }


# Modelo de usuario personalizado
AUTH_USER_MODEL = 'authentication.User'


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'assistant': '5/hour',
        'password_reset': '5/hour',
        'password_reset_confirm': '10/hour',
    },
}


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
# Correo saliente (solo si EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'webmaster@localhost')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')
ASSISTANT_DAILY_USER_LIMIT = 10
ASSISTANT_DAILY_GLOBAL_LIMIT = 50
ASSISTANT_MAX_OUTPUT_TOKENS = 30

TRANSBANK_RETURN_URL = os.getenv(
    'TRANSBANK_RETURN_URL',
    'http://127.0.0.1:8000/api/payments/transbank/return/',
)
PAYMENT_RESULT_URL = os.getenv(
    'PAYMENT_RESULT_URL',
    'http://localhost:3000/payment-result',
)

# Configuración CORS. El front Streamlit llama a la API desde su servidor (no desde el
# navegador), así que en producción basta con la lista de CORS_ALLOWED_ORIGINS (puede quedar vacía).
CORS_ALLOWED_ORIGINS = _env_list('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_ALL_ORIGINS = DEBUG and not CORS_ALLOWED_ORIGINS

# Producción (DEBUG=False): el proveedor termina https en su proxy y reenvía por http.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True