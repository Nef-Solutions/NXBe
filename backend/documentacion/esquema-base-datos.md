# Esquema de base de datos de Overol

Diagrama entidad-relación generado a partir de los modelos Django actuales.
Representa entidades de negocio de las apps `authentication`, `catalog`,
`visits`, `assistant` y `payments`; omite tablas internas del framework Django
(permisos, grupos, sesiones y blacklist JWT).

```mermaid
erDiagram
    USER {
        int id PK
        string email UK
        string rut UK
        string role
        string account_status
        string phone
        string address
        string commune
    }

    PROFESSIONAL_PROFILE {
        int id PK
        int user_id FK,UK
        string rut UK
        string verification_status
        decimal visit_fee
        datetime subscription_expires_at
        decimal rating_avg
        boolean is_available
        json work_days
        json coverage_communes
    }

    PASSWORD_RESET_CODE {
        int id PK
        int user_id FK
        string code_hash
        datetime expires_at
        smallint attempts
        datetime consumed_at
    }

    VERIFICATION_CASE_MESSAGE {
        int id PK
        int professional_id FK
        text message
        text admin_response
        datetime resolved_at
        datetime created_at
    }

    HOME_ZONE {
        int id PK
        string name UK
        text description
    }

    TRADE_CATEGORY {
        int id PK
        string name UK
        text keywords
    }

    SPECIALTY {
        int id PK
        int category_id FK
        string name
    }

    PROFESSIONAL_TRADE {
        int id PK
        int professional_id FK
        int category_id FK
        smallint years_experience
        boolean certification_verified
        boolean is_active
    }

    VISIT_REQUEST {
        int id PK
        int client_id FK
        int professional_id FK
        int specialty_id FK
        int home_zone_id FK
        string status
        date visit_date
        string visit_time
        text problem_description
        datetime expires_at
        datetime completed_at
    }

    RATING {
        int id PK
        int visit_id FK
        int author_id FK
        int target_id FK
        int trade_id FK
        smallint quality
        smallint punctuality
        smallint treatment
    }

    AFTER_SALES_CLAIM {
        int id PK
        int visit_id FK,UK
        int client_id FK
        text description
        string status
        text admin_resolution
    }

    SUPPORT_TICKET {
        int id PK
        int user_id FK
        int visit_id FK
        string subject
        text description
        string status
    }

    NOTIFICATION {
        int id PK
        int recipient_id FK
        int related_visit_id FK
        string title
        boolean is_read
        datetime created_at
    }

    PROFESSIONAL_CONTENT {
        int id PK
        string title
        string module
        string url
        boolean is_external
        boolean is_visible
        int order
    }

    CONTENT_PROGRESS {
        int id PK
        int professional_id FK
        int content_id FK
        datetime completed_at
    }

    ADMIN_AUDIT_LOG {
        int id PK
        int administrator_id FK
        string action
        string target_type
        int target_id
        text reason
    }

    ASSISTANT_DAILY_USAGE {
        int id PK
        int user_id FK
        date date
        smallint request_count
    }

    PROFESSIONAL_SUBSCRIPTION_PLAN {
        int id PK
        string code UK
        string name
        decimal amount
        smallint duration_months
        boolean is_active UK_partial
        datetime created_at
        datetime updated_at
    }

    PAYMENT_TRANSACTION {
        int id PK
        int payer_id FK
        int visit_id FK
        int professional_id FK
        int subscription_plan_id FK
        smallint subscription_duration_months
        decimal amount
        string buy_order UK
        string status
        string token_hash
        int response_code
    }

    USER ||--o| PROFESSIONAL_PROFILE : "tiene"
    USER ||--o{ PASSWORD_RESET_CODE : "solicita"
    PROFESSIONAL_PROFILE ||--o{ VERIFICATION_CASE_MESSAGE : "tiene"

    HOME_ZONE }o--o{ TRADE_CATEGORY : "se asocia a"
    TRADE_CATEGORY ||--o{ SPECIALTY : "agrupa"
    PROFESSIONAL_PROFILE }o--o{ SPECIALTY : "está calificado en"
    PROFESSIONAL_PROFILE ||--o{ PROFESSIONAL_TRADE : "declara"
    TRADE_CATEGORY ||--o{ PROFESSIONAL_TRADE : "corresponde a"

    USER ||--o{ VISIT_REQUEST : "cliente"
    PROFESSIONAL_PROFILE ||--o{ VISIT_REQUEST : "atiende"
    SPECIALTY ||--o{ VISIT_REQUEST : "especialidad solicitada"
    HOME_ZONE o|--o{ VISIT_REQUEST : "zona opcional"

    VISIT_REQUEST ||--o{ RATING : "recibe"
    USER ||--o{ RATING : "autor"
    USER ||--o{ RATING : "evaluado"
    PROFESSIONAL_TRADE o|--o{ RATING : "oficio opcional"

    VISIT_REQUEST ||--o| AFTER_SALES_CLAIM : "puede tener"
    USER ||--o{ AFTER_SALES_CLAIM : "cliente"
    USER ||--o{ SUPPORT_TICKET : "crea"
    VISIT_REQUEST o|--o{ SUPPORT_TICKET : "visita opcional"

    USER ||--o{ NOTIFICATION : "recibe"
    VISIT_REQUEST o|--o{ NOTIFICATION : "relacionada opcional"
    PROFESSIONAL_PROFILE ||--o{ CONTENT_PROGRESS : "registra"
    PROFESSIONAL_CONTENT ||--o{ CONTENT_PROGRESS : "tiene avances"
    USER ||--o{ ADMIN_AUDIT_LOG : "administrador"
    USER o|--o{ ASSISTANT_DAILY_USAGE : "cuota; null es global"

    USER ||--o{ PAYMENT_TRANSACTION : "paga"
    VISIT_REQUEST o|--o{ PAYMENT_TRANSACTION : "pago de visita"
    PROFESSIONAL_PROFILE o|--o{ PAYMENT_TRANSACTION : "pago de suscripción"
    PROFESSIONAL_SUBSCRIPTION_PLAN o|--o{ PAYMENT_TRANSACTION : "plan comprado"
```

## Reglas y notas de lectura

- `PROFESSIONAL_SUBSCRIPTION_PLAN` tiene un único plan activo como máximo,
  garantizado por una restricción parcial de base de datos. La migración
  `payments.0003_professionalsubscriptionplan_and_payment_plan` carga el plan
  inicial `professional-monthly` por $10.000 CLP y un mes.
- `PAYMENT_TRANSACTION.amount` y `subscription_duration_months` son valores
  guardados al iniciar el pago. Cambiar el plan no altera las condiciones de
  pagos ya iniciados. Las transacciones históricas anteriores al plan tienen
  `subscription_plan_id` nulo y duración predeterminada de un mes.
- Cada pago se relaciona exactamente con una visita o con un perfil
  profesional. El plan es opcional, solo aplica a un pago profesional y los
  nuevos pagos de suscripción siempre lo referencian.
- `PROFESSIONAL_PROFILE.subscription_expires_at` guarda la vigencia actual; no
  existe una tabla separada de períodos de suscripción.
- Los enlaces entre `HOME_ZONE` y `TRADE_CATEGORY`, y entre `SPECIALTY` y
  `PROFESSIONAL_PROFILE`, usan tablas Many-to-Many creadas automáticamente por
  Django y no se muestran como entidades independientes.
- `ADMIN_AUDIT_LOG.target_type` y `target_id` describen el objeto auditado, pero
  no son una clave foránea.
- Los archivos (documentos de cédula, fotos y certificaciones) se guardan en
  almacenamiento; la base conserva sus referencias y metadatos de campo.

## Fuente

- [Modelos de pagos](../apps/payments/models.py)
- [Migración de planes](../apps/payments/migrations/0003_professionalsubscriptionplan_and_payment_plan.py)
- [Modelos de autenticación](../apps/authentication/models.py)
- [Modelos de catálogo](../apps/catalog/models.py)
- [Modelos de visitas y contenido](../apps/visits/models.py)
- [Modelo de cuotas Overil](../apps/assistant/models.py)
