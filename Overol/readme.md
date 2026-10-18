# Proyecto Overol

Repositorio del proyecto Capstone Overol.

## Organización del repositorio

- [backend](backend/): API Django, modelos, migraciones, Docker y documentación técnica.
- [Documentos_equipo](Documentos_equipo/): material de trabajo del equipo.
- [Fase 1](Fase%201/): entregables de la primera fase.
- [Fase 2](Fase%202/): entregables de la segunda fase.

## Comenzar

El backend se ejecuta desde su propia carpeta:

```powershell
Set-Location backend
python manage.py runserver
```

Para preparar un computador nuevo, seguir [backend/documentacion/instalacion.md](backend/documentacion/instalacion.md).

## Documentación del backend

- [Índice de documentación](backend/documentacion/README.md)
- [Contrato de API](backend/documentacion/api.md)
- [Arquitectura](backend/documentacion/arquitectura.md)
- [Docker](backend/documentacion/docker.md)
- [Estado del DoD](backend/documentacion/estado-dod.md)
- [Pruebas](backend/documentacion/pruebas.md)

## Seguridad

No subir `backend/.env`. Ese archivo está ignorado por Git. Para otro computador, copiar `backend/.env.example` como `backend/.env` y completar los valores locales.
