# Diagrama de base de datos

Este diagrama representa el modelo implementado en las migraciones actuales. Las áreas de pago, chatbot y geolocalización real no aparecen porque están fuera del alcance solicitado.

```mermaid
erDiagram
    USER ||--o| PROFESSIONAL_PROFILE : tiene
    USER ||--o{ VERIFICATION_CASE_MESSAGE : envia
    PROFESSIONAL_PROFILE ||--o{ VERIFICATION_CASE_MESSAGE : contiene
    HOME_ZONE }o--o{ TRADE_CATEGORY : relaciona
    TRADE_CATEGORY ||--o{ SPECIALTY : contiene
    SPECIALTY }o--o{ PROFESSIONAL_PROFILE : habilita
    PROFESSIONAL_PROFILE ||--o{ PROFESSIONAL_TRADE : declara
    TRADE_CATEGORY ||--o{ PROFESSIONAL_TRADE : clasifica
    USER ||--o{ VISIT_REQUEST : solicita
    PROFESSIONAL_PROFILE ||--o{ VISIT_REQUEST : recibe
    SPECIALTY ||--o{ VISIT_REQUEST : utiliza
    VISIT_REQUEST ||--o{ RATING : recibe
    USER ||--o{ RATING : escribe
    USER ||--o{ RATING : recibe
    VISIT_REQUEST ||--o| AFTER_SALES_CLAIM : genera
    USER ||--o{ AFTER_SALES_CLAIM : abre
    USER ||--o{ SUPPORT_TICKET : crea
    VISIT_REQUEST ||--o{ SUPPORT_TICKET : relaciona
    USER ||--o{ NOTIFICATION : recibe
    VISIT_REQUEST ||--o{ NOTIFICATION : referencia
    PROFESSIONAL_CONTENT ||--o{ CONTENT_PROGRESS : registra
    PROFESSIONAL_PROFILE ||--o{ CONTENT_PROGRESS : completa
    USER ||--o{ ADMIN_AUDIT_LOG : ejecuta

    USER {
        bigint id PK
        string email UK
        string rut UK
        string role
        string account_status
        datetime locked_until
        datetime privacy_policy_accepted_at
    }
    PROFESSIONAL_PROFILE {
        bigint id PK
        bigint user_id FK
        string rut UK
        string verification_status
        decimal visit_fee
        decimal rating_avg
    }
    HOME_ZONE {
        bigint id PK
        string name UK
    }
    TRADE_CATEGORY {
        bigint id PK
        string name UK
        text keywords
    }
    SPECIALTY {
        bigint id PK
        bigint category_id FK
        string name
    }
    PROFESSIONAL_TRADE {
        bigint id PK
        bigint professional_id FK
        bigint category_id FK
        smallint years_experience
        boolean certification_verified
        boolean is_active
    }
    VISIT_REQUEST {
        bigint id PK
        bigint client_id FK
        bigint professional_id FK
        bigint specialty_id FK
        string status
        text problem_description
        string tentative_schedule
        string visit_address
    }
    RATING {
        bigint id PK
        bigint visit_id FK
        bigint author_id FK
        bigint target_id FK
        smallint quality
        smallint punctuality
        smallint treatment
    }
    AFTER_SALES_CLAIM {
        bigint id PK
        bigint visit_id FK UK
        bigint client_id FK
        string status
    }
    SUPPORT_TICKET {
        bigint id PK
        bigint user_id FK
        bigint visit_id FK
        string status
    }
    NOTIFICATION {
        bigint id PK
        bigint recipient_id FK
        bigint related_visit_id FK
        boolean is_read
    }
    PROFESSIONAL_CONTENT {
        bigint id PK
        string module
        string title
        boolean is_visible
    }
    CONTENT_PROGRESS {
        bigint id PK
        bigint professional_id FK
        bigint content_id FK
        datetime completed_at
    }
    ADMIN_AUDIT_LOG {
        bigint id PK
        bigint administrator_id FK
        string action
        string target_type
        bigint target_id
        text reason
    }
```

## Reglas importantes

- `User.email` y `User.rut` son únicos. El RUT de `ProfessionalProfile` también es único.
- Un profesional solo aparece en búsquedas cuando su verificación está `APPROVED` y su cuenta está `ACTIVE`.
- Una solicitud comienza en `PENDING`.
- Una calificación solo se permite cuando la solicitud está `COMPLETED`.
- Un usuario solo puede calificar una vez la misma visita.
- El progreso de un contenido es único por profesional y contenido.
- La bitácora administrativa solo debe crearse desde acciones administrativas; sus campos están en solo lectura en Django Admin.