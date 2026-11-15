from django.conf import settings
from django.core.files.storage import FileSystemStorage


def _build_private_verification_storage():
    """Cédulas de verificación: nunca tienen URL pública; se leen a través de la API.

    En producción (S3_PRIVATE_BUCKET definido) van a un bucket privado compatible con S3;
    en desarrollo, a la carpeta local PRIVATE_MEDIA_ROOT.
    """
    if settings.S3_PRIVATE_BUCKET:
        from storages.backends.s3 import S3Storage

        return S3Storage(bucket_name=settings.S3_PRIVATE_BUCKET, querystring_auth=True)
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT, base_url=None)


private_verification_storage = _build_private_verification_storage()
