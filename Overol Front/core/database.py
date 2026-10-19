"""Capa de datos: conexión SQLite, creación de tablas, datos demo, auditoría y consultas."""

import re
import sqlite3
from datetime import datetime, timedelta

from core.constants import DB_PATH, UPLOAD_DIR
from core.security import hash_password, normalize_rut


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    UPLOAD_DIR.mkdir(exist_ok=True)

    conn = get_connection()

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rut TEXT UNIQUE,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('cliente','profesional','admin')),
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            phone TEXT DEFAULT '',
            commune TEXT DEFAULT '',
            contact_preference TEXT DEFAULT 'WhatsApp',
            service_interest TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS professionals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            trade TEXT NOT NULL,
            specialties TEXT NOT NULL,
            certifications TEXT DEFAULT '',
            experience TEXT DEFAULT '',
            visit_fee TEXT DEFAULT '',
            verified INTEGER NOT NULL DEFAULT 0,
            verification_status TEXT NOT NULL DEFAULT 'Pendiente',
            availability INTEGER NOT NULL DEFAULT 1,
            coverage TEXT DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS verification_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professional_id INTEGER NOT NULL,
            document_type TEXT NOT NULL,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY(professional_id) REFERENCES professionals(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            professional_id INTEGER NOT NULL,
            service TEXT NOT NULL,
            home_zone TEXT,
            commune TEXT NOT NULL,
            tentative_date TEXT NOT NULL,
            tentative_time TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendiente',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(client_id) REFERENCES users(id),
            FOREIGN KEY(professional_id) REFERENCES professionals(id)
        );

        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER UNIQUE NOT NULL,
            client_id INTEGER NOT NULL,
            professional_id INTEGER NOT NULL,
            quality INTEGER NOT NULL,
            punctuality INTEGER NOT NULL,
            treatment INTEGER NOT NULL,
            comment TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(request_id) REFERENCES requests(id),
            FOREIGN KEY(client_id) REFERENCES users(id),
            FOREIGN KEY(professional_id) REFERENCES professionals(id)
        );

        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            professional_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            response TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Abierto',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(request_id) REFERENCES requests(id),
            FOREIGN KEY(client_id) REFERENCES users(id),
            FOREIGN KEY(professional_id) REFERENCES professionals(id)
        );

        CREATE TABLE IF NOT EXISTS training_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            content_type TEXT NOT NULL,
            description TEXT NOT NULL,
            external_url TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS training_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professional_id INTEGER NOT NULL,
            content_id INTEGER NOT NULL,
            completed_at TEXT NOT NULL,
            UNIQUE(professional_id, content_id),
            FOREIGN KEY(professional_id) REFERENCES professionals(id),
            FOREIGN KEY(content_id) REFERENCES training_content(id)
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendiente',
            created_at TEXT NOT NULL,
            FOREIGN KEY(rating_id) REFERENCES ratings(id)
        );

        CREATE TABLE IF NOT EXISTS professional_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professional_id INTEGER NOT NULL,
            trade TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            years_experience INTEGER,
            specialties TEXT DEFAULT '',
            certifications TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE(professional_id, trade),
            FOREIGN KEY(professional_id) REFERENCES professionals(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS client_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER UNIQUE NOT NULL,
            professional_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            comment TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(request_id) REFERENCES requests(id),
            FOREIGN KEY(professional_id) REFERENCES professionals(id),
            FOREIGN KEY(client_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS user_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            from_admin INTEGER NOT NULL DEFAULT 0,
            body TEXT NOT NULL,
            read_by_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(request_id) REFERENCES requests(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            entity TEXT NOT NULL,
            entity_id INTEGER,
            details TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )

    run_migrations(conn)
    seed_data(conn)
    normalize_existing_ruts(conn)
    migrate_trades(conn)
    seed_demo_extras(conn)
    conn.commit()
    conn.close()


def normalize_existing_ruts(conn):
    """Migración: deja todos los RUT sin puntos ni espacios (formato 12345678-5)."""
    legacy = {"13456789-6": "13456789-9", "14567890-7": "14567890-0"}
    rows = conn.execute("SELECT id, rut FROM users WHERE rut IS NOT NULL").fetchall()
    for row in rows:
        clean = normalize_rut(row["rut"])
        clean = legacy.get(clean, clean)
        if clean != row["rut"]:
            taken = conn.execute(
                "SELECT 1 FROM users WHERE rut = ? AND id != ?", (clean, row["id"])
            ).fetchone()
            if not taken:
                conn.execute("UPDATE users SET rut = ? WHERE id = ?", (clean, row["id"]))


def seed_data(conn):
    now = now_str()

    # Admin demo
    if not conn.execute(
        "SELECT id FROM users WHERE email = ?",
        ("admin@overol.cl",),
    ).fetchone():
        conn.execute(
            """
            INSERT INTO users
            (name, rut, email, password_hash, role, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Administrador Overol",
                "99999999-9",
                "admin@overol.cl",
                hash_password("admin123"),
                "admin",
                1,
                now,
            ),
        )

    # Cliente demo
    if not conn.execute(
        "SELECT id FROM users WHERE email = ?",
        ("cliente@overol.cl",),
    ).fetchone():
        conn.execute(
            """
            INSERT INTO users
            (name, rut, email, password_hash, role, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Usuario Demo",
                "11111111-1",
                "cliente@overol.cl",
                hash_password("cliente123"),
                "cliente",
                1,
                now,
            ),
        )

    # Profesionales demo
    profesionales = [
        {
            "name": "Carlos Muñoz",
            "rut": "12345678-5",
            "email": "carlos@overol.cl",
            "password": "profesional123",
            "trade": "Gasfitería",
            "specialties": "Gasfitería,Fugas de agua,Calefont y termo",
            "certifications": "Gasfitería domiciliaria",
            "experience": "8 años de experiencia",
            "visit_fee": "$15.000",
            "verified": 1,
            "status": "Aprobado",
            "coverage": "Santiago,Ñuñoa,Providencia",
        },
        {
            "name": "Daniel Soto",
            "rut": "13456789-9",
            "email": "daniel@overol.cl",
            "password": "profesional123",
            "trade": "Electricidad",
            "specialties": "Electricidad,Enchufes e interruptores,Tableros eléctricos",
            "certifications": "Instalaciones eléctricas",
            "experience": "6 años de experiencia",
            "visit_fee": "$18.000",
            "verified": 1,
            "status": "Aprobado",
            "coverage": "Maipú,Pudahuel,La Florida",
        },
        {
            "name": "Marcelo Rojas",
            "rut": "14567890-0",
            "email": "marcelo@overol.cl",
            "password": "profesional123",
            "trade": "Maestro multipropósito",
            "specialties": "Carpintería,Pintura,Muebles a medida,Pintura interior",
            "certifications": "Terminaciones",
            "experience": "5 años de experiencia",
            "visit_fee": "$12.000",
            "verified": 1,
            "status": "Aprobado",
            "coverage": "Pudahuel,Maipú,Santiago",
        },
    ]

    for p in profesionales:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (p["email"],),
        ).fetchone()

        if not existing:
            cur = conn.execute(
                """
                INSERT INTO users
                (name, rut, email, password_hash, role, active, created_at)
                VALUES (?, ?, ?, ?, 'profesional', 1, ?)
                """,
                (
                    p["name"],
                    p["rut"],
                    p["email"],
                    hash_password(p["password"]),
                    now,
                ),
            )
            user_id = cur.lastrowid

            conn.execute(
                """
                INSERT INTO professionals
                (user_id, trade, specialties, certifications,
                 experience, visit_fee, verified,
                 verification_status, availability, coverage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    user_id,
                    p["trade"],
                    p["specialties"],
                    p["certifications"],
                    p["experience"],
                    p["visit_fee"],
                    p["verified"],
                    p["status"],
                    p["coverage"],
                ),
            )

    training = [
        (
            "Formalización tributaria",
            "Tributario",
            "Guía",
            "Material introductorio sobre formalización y obligaciones tributarias.",
            "https://www.sii.cl/",
        ),
        (
            "Seguridad laboral",
            "Seguridad",
            "Video",
            "Buenas prácticas básicas para realizar trabajos de forma segura.",
            "",
        ),
        (
            "Gestión comercial",
            "Gestión",
            "Guía",
            "Recomendaciones para estructurar presupuestos y administrar servicios.",
            "",
        ),
    ]

    for item in training:
        if not conn.execute(
            "SELECT id FROM training_content WHERE title = ?",
            (item[0],),
        ).fetchone():
            conn.execute(
                """
                INSERT INTO training_content
                (title, category, content_type, description, external_url)
                VALUES (?, ?, ?, ?, ?)
                """,
                item,
            )


def audit(user_id, action, entity, entity_id=None, details=""):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO audit_log
        (user_id, action, entity, entity_id, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            action,
            entity,
            entity_id,
            details,
            now_str(),
        ),
    )
    conn.commit()
    conn.close()


def get_user_by_email(email):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE lower(email) = lower(?)",
        (email.strip(),),
    ).fetchone()
    conn.close()
    return row


def get_user(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return row


def get_user_profile(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return row


def save_user_profile(
    user_id,
    phone,
    commune,
    contact_preference,
    service_interest="",
    bio="",
    address="",
):
    now = now_str()
    conn = get_connection()

    existing = conn.execute(
        "SELECT id FROM user_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    if existing:
        conn.execute(
            """
            UPDATE user_profiles
            SET phone = ?, commune = ?, contact_preference = ?,
                service_interest = ?, bio = ?, address = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (
                phone.strip(),
                commune.strip(),
                contact_preference,
                service_interest.strip(),
                bio.strip(),
                address.strip(),
                now,
                user_id,
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO user_profiles
            (user_id, phone, commune, contact_preference,
             service_interest, bio, address, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                phone.strip(),
                commune.strip(),
                contact_preference,
                service_interest.strip(),
                bio.strip(),
                address.strip(),
                now,
                now,
            ),
        )

    conn.commit()
    conn.close()


# Modo api: roles del backend y clave de los usuarios espejo (nunca coincide con un hash)
API_ROLES = {"CLIENT": "cliente", "PROFESSIONAL": "profesional", "ADMIN": "admin"}
API_PASSWORD_PLACEHOLDER = "api$sin-clave-local"


def upsert_api_user(me):
    """
    Crea o actualiza la copia local (espejo) de un usuario del backend y devuelve su id local.
    El resto de las pantallas todavía usa SQLite, por eso necesita un usuario local.
    El backend manda en nombre, RUT, rol, teléfono, dirección y comuna.
    """
    role = API_ROLES.get(me.get("role"))
    if not role:
        raise ValueError(f"Rol desconocido del backend: {me.get('role')!r}")

    email = me["email"].strip().lower()
    name = f"{me.get('first_name', '').strip()} {me.get('last_name', '').strip()}".strip() or email
    rut = normalize_rut(me.get("rut") or "") or None

    conn = get_connection()
    try:
        # Si el RUT ya pertenece a otra cuenta local, el espejo queda sin RUT en vez de fallar
        if rut and conn.execute(
            "SELECT id FROM users WHERE rut = ? AND lower(email) != ?", (rut, email)
        ).fetchone():
            rut = None

        row = conn.execute("SELECT id FROM users WHERE lower(email) = ?", (email,)).fetchone()

        if row:
            user_id = row["id"]
            conn.execute(
                "UPDATE users SET name = ?, rut = ?, role = ?, active = 1 WHERE id = ?",
                (name, rut, role, user_id),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO users (name, rut, email, password_hash, role, active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (name, rut, email, API_PASSWORD_PLACEHOLDER, role, now_str()),
            )
            user_id = cur.lastrowid

        # Solo se actualiza un perfil existente; si no hay, el usuario lo completa al entrar
        for field in ("phone", "address", "commune"):
            value = (me.get(field) or "").strip()
            if value:
                conn.execute(
                    f"UPDATE user_profiles SET {field} = ?, updated_at = ? WHERE user_id = ?",
                    (value, now_str(), user_id),
                )

        conn.commit()
    finally:
        conn.close()

    return user_id


def get_professional_by_user(user_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT p.*, u.name, u.rut, u.email, u.active
        FROM professionals p
        JOIN users u ON u.id = p.user_id
        WHERE p.user_id = ?
        """,
        (user_id,),
    ).fetchone()
    conn.close()
    return row


def get_professional_by_id(professional_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT p.*, u.name, u.rut, u.email, u.active
        FROM professionals p
        JOIN users u ON u.id = p.user_id
        WHERE p.id = ?
        """,
        (professional_id,),
    ).fetchone()
    conn.close()
    return row


def get_all_professionals(
    specialty="Todas",
    commune="Todas",
    only_available=True,
    trade="Todas",
):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT p.*, u.name, u.rut, u.email, u.active
        FROM professionals p
        JOIN users u ON u.id = p.user_id
        WHERE u.active = 1
          AND p.verified = 1
        ORDER BY u.name
        """
    ).fetchall()

    conn.close()

    result = []

    for row in rows:
        trades = get_trades(row["id"])
        trade_names = [t["trade"] for t in trades]

        coverage = [
            x.strip()
            for x in row["coverage"].split(",")
            if x.strip()
        ]

        if trade != "Todas" and trade not in trade_names:
            continue

        if specialty != "Todas":
            scope = [t for t in trades if trade == "Todas" or t["trade"] == trade]
            specs = [
                x.strip()
                for t in scope
                for x in (t["specialties"] or "").split(",")
                if x.strip()
            ]
            if specialty not in specs and specialty not in trade_names:
                continue

        if commune != "Todas" and commune not in coverage:
            continue

        if only_available and not row["availability"]:
            continue

        result.append(row)

    return result


def get_requests_for_client(client_id):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            r.*,
            p.id AS professional_id,
            p.user_id AS professional_user_id,
            u.name AS professional_name
        FROM requests r
        JOIN professionals p ON p.id = r.professional_id
        JOIN users u ON u.id = p.user_id
        WHERE r.client_id = ?
        ORDER BY r.id DESC
        """,
        (client_id,),
    ).fetchall()
    conn.close()
    return rows


def get_requests_for_professional(professional_id):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            r.*,
            u.name AS client_name,
            u.email AS client_email
        FROM requests r
        JOIN users u ON u.id = r.client_id
        WHERE r.professional_id = ?
        ORDER BY r.id DESC
        """,
        (professional_id,),
    ).fetchall()
    conn.close()
    return rows


def get_all_requests():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            r.*,
            uc.name AS client_name,
            up.name AS professional_name
        FROM requests r
        JOIN users uc ON uc.id = r.client_id
        JOIN professionals p ON p.id = r.professional_id
        JOIN users up ON up.id = p.user_id
        ORDER BY r.id DESC
        """
    ).fetchall()
    conn.close()
    return rows


def get_rating_for_request(request_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM ratings WHERE request_id = ?",
        (request_id,),
    ).fetchone()
    conn.close()
    return row


def get_professional_rating(professional_id, trade=None):
    """Promedio y cantidad de valoraciones; de un oficio específico si se indica."""
    sql = """
        SELECT
            COUNT(*) AS total,
            AVG((quality + punctuality + treatment) / 3.0) AS average
        FROM ratings
        WHERE professional_id = ?
    """
    params = [professional_id]

    if trade:
        sql += " AND trade = ?"
        params.append(trade)

    conn = get_connection()
    row = conn.execute(sql, params).fetchone()
    conn.close()

    if not row or row["total"] == 0:
        return 0, 0

    return row["total"], round(row["average"], 2)


def get_claims_for_client(client_id):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            c.*,
            u.name AS professional_name
        FROM claims c
        JOIN professionals p ON p.id = c.professional_id
        JOIN users u ON u.id = p.user_id
        WHERE c.client_id = ?
        ORDER BY c.id DESC
        """,
        (client_id,),
    ).fetchall()
    conn.close()
    return rows


def get_claims_for_professional(professional_id):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            c.*,
            u.name AS client_name
        FROM claims c
        JOIN users u ON u.id = c.client_id
        WHERE c.professional_id = ?
        ORDER BY c.id DESC
        """,
        (professional_id,),
    ).fetchall()
    conn.close()
    return rows


def get_all_claims():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            c.*,
            uc.name AS client_name,
            up.name AS professional_name
        FROM claims c
        JOIN users uc ON uc.id = c.client_id
        JOIN professionals p ON p.id = c.professional_id
        JOIN users up ON up.id = p.user_id
        ORDER BY c.id DESC
        """
    ).fetchall()
    conn.close()
    return rows


def count_recent_failed_logins(email, minutes=10, action="LOGIN_FAILED"):
    """Cuenta intentos fallidos de login recientes para un correo (anti fuerza bruta)."""
    since = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    row = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM audit_log
        WHERE action = ?
          AND details = ?
          AND created_at >= ?
        """,
        (action, email.strip().lower(), since),
    ).fetchone()
    conn.close()
    return row["total"]


def get_verification_documents(professional_id):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM verification_documents
        WHERE professional_id = ?
        ORDER BY id DESC
        """,
        (professional_id,),
    ).fetchall()
    conn.close()
    return rows


def change_request_status(
    request_id,
    new_status,
    allowed_from,
    client_id=None,
    professional_id=None,
):
    """
    Cambia el estado de una solicitud SOLO si:
      - su estado actual está en `allowed_from`, y
      - pertenece al cliente / profesional indicado.
    Devuelve True si se aplicó el cambio (protege contra doble clic y pestañas desfasadas).
    """
    placeholders = ",".join("?" for _ in allowed_from)
    sql = (
        "UPDATE requests SET status = ?, updated_at = ? "
        f"WHERE id = ? AND status IN ({placeholders})"
    )
    params = [new_status, now_str(), request_id, *allowed_from]

    if client_id is not None:
        sql += " AND client_id = ?"
        params.append(client_id)

    if professional_id is not None:
        sql += " AND professional_id = ?"
        params.append(professional_id)

    conn = get_connection()
    cur = conn.execute(sql, params)
    conn.commit()
    changed = cur.rowcount == 1
    conn.close()
    return changed


# ============================================================
# MIGRACIONES (conservan los datos de versiones anteriores)
# ============================================================

def add_column_if_missing(conn, table, column, definition):
    columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def run_migrations(conn):
    add_column_if_missing(conn, "user_profiles", "address", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "professionals", "schedule", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "professionals", "about", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "requests", "trade", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "requests", "client_confirmed", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "requests", "professional_confirmed", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "requests", "reject_reason", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "requests", "reject_detail", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "ratings", "trade", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "professionals", "work_days", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "professionals", "work_start", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "professionals", "work_end", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "requests", "cancelled_by", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "requests", "cancel_reason", "TEXT DEFAULT ''")
    # Modo api: token de renovación del backend asociado a la sesión persistente
    add_column_if_missing(conn, "user_sessions", "api_refresh", "TEXT DEFAULT ''")

    # El horario guardado como texto ("Lun, Mar · 09:00–18:00") pasa a campos propios
    for row in conn.execute(
        "SELECT id, schedule FROM professionals WHERE work_days = '' AND schedule != ''"
    ).fetchall():
        match = re.match(r"^(.*) · (\d\d:\d\d)–(\d\d:\d\d)$", row["schedule"])
        if match:
            conn.execute(
                "UPDATE professionals SET work_days = ?, work_start = ?, work_end = ? WHERE id = ?",
                (",".join(d.strip() for d in match.group(1).split(",")),
                 match.group(2), match.group(3), row["id"]),
            )

    # El estado "Completada" pasa a llamarse "Finalizada" (como en las historias)
    conn.execute("UPDATE requests SET status = 'Finalizada' WHERE status = 'Completada'")
    conn.execute(
        """
        UPDATE requests
        SET client_confirmed = 1, professional_confirmed = 1
        WHERE status = 'Finalizada'
          AND client_confirmed = 0 AND professional_confirmed = 0
        """
    )
    # Solicitudes y valoraciones antiguas quedan asociadas a su oficio
    conn.execute("UPDATE requests SET trade = service WHERE trade = '' OR trade IS NULL")
    conn.execute(
        """
        UPDATE ratings
        SET trade = (SELECT r.trade FROM requests r WHERE r.id = ratings.request_id)
        WHERE trade = '' OR trade IS NULL
        """
    )


def migrate_trades(conn):
    """Crea la tabla de oficios a partir de los datos del modelo anterior."""
    from core.constants import ESPECIALIDADES_POR_OFICIO, OFICIOS

    all_known = {
        spec: trade
        for trade, specs in ESPECIALIDADES_POR_OFICIO.items()
        for spec in specs
    }

    professionals = conn.execute(
        """
        SELECT * FROM professionals
        WHERE id NOT IN (SELECT DISTINCT professional_id FROM professional_trades)
        """
    ).fetchall()

    for prof in professionals:
        tokens = [x.strip() for x in (prof["specialties"] or "").split(",") if x.strip()]
        trades = [prof["trade"]] + [
            t for t in tokens if t in OFICIOS and t != prof["trade"]
        ]
        specs_by_trade = {t: [] for t in trades}
        for token in tokens:
            if token in OFICIOS:
                continue
            owner = all_known.get(token, prof["trade"])
            specs_by_trade.setdefault(owner, []).append(token)

        match = re.search(r"\d+", prof["experience"] or "")
        years = int(match.group()) if match else None

        for trade in trades:
            insert_trade(
                conn,
                prof["id"],
                trade,
                years,
                specs_by_trade.get(trade, []),
                prof["certifications"] if trade == prof["trade"] else "",
            )

        sync_professional_summary(conn, prof["id"])


# ============================================================
# OFICIOS DEL PROFESIONAL (Historias 017, 018 y 025)
# ============================================================

def insert_trade(conn, professional_id, trade, years, specialties, certifications):
    conn.execute(
        """
        INSERT OR IGNORE INTO professional_trades
        (professional_id, trade, active, years_experience,
         specialties, certifications, created_at)
        VALUES (?, ?, 1, ?, ?, ?, ?)
        """,
        (
            professional_id,
            trade,
            years,
            ",".join(specialties),
            (certifications or "").strip(),
            now_str(),
        ),
    )


def sync_professional_summary(conn, professional_id):
    """Mantiene las columnas resumen de `professionals` (usadas por búsqueda y admin)."""
    rows = conn.execute(
        """
        SELECT * FROM professional_trades
        WHERE professional_id = ? AND active = 1
        ORDER BY id
        """,
        (professional_id,),
    ).fetchall()

    if not rows:
        return

    names = [r["trade"] for r in rows]
    specialties = []
    for r in rows:
        specialties += [x for x in (r["specialties"] or "").split(",") if x]

    years = [r["years_experience"] for r in rows if r["years_experience"] is not None]
    certs = [r["certifications"] for r in rows if r["certifications"]]

    conn.execute(
        """
        UPDATE professionals
        SET trade = ?, specialties = ?, experience = ?, certifications = ?
        WHERE id = ?
        """,
        (
            names[0],
            ",".join(names + specialties),
            f"{max(years)} años de experiencia" if years else "",
            "; ".join(certs),
            professional_id,
        ),
    )


def get_trades(professional_id, active_only=True):
    conn = get_connection()
    sql = "SELECT * FROM professional_trades WHERE professional_id = ?"
    if active_only:
        sql += " AND active = 1"
    rows = conn.execute(sql + " ORDER BY id", (professional_id,)).fetchall()
    conn.close()
    return rows


def add_trade(professional_id, trade, years=None, specialties=(), certifications=""):
    """
    Agrega un oficio. Si el oficio existió antes (inactivo) se REACTIVA y conserva su
    valoración histórica. Devuelve 'creado', 'reactivado' o 'existente'.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM professional_trades WHERE professional_id = ? AND trade = ?",
        (professional_id, trade),
    ).fetchone()

    if row and row["active"]:
        conn.close()
        return "existente"

    if row:
        conn.execute(
            """
            UPDATE professional_trades
            SET active = 1, years_experience = ?, specialties = ?, certifications = ?
            WHERE id = ?
            """,
            (years, ",".join(specialties), certifications.strip(), row["id"]),
        )
        result = "reactivado"
    else:
        insert_trade(conn, professional_id, trade, years, list(specialties), certifications)
        result = "creado"

    sync_professional_summary(conn, professional_id)
    conn.commit()
    conn.close()
    return result


def update_trade(trade_id, professional_id, years, specialties, certifications):
    conn = get_connection()
    conn.execute(
        """
        UPDATE professional_trades
        SET years_experience = ?, specialties = ?, certifications = ?
        WHERE id = ? AND professional_id = ?
        """,
        (years, ",".join(specialties), certifications.strip(), trade_id, professional_id),
    )
    sync_professional_summary(conn, professional_id)
    conn.commit()
    conn.close()


def deactivate_trade(trade_id, professional_id):
    """
    Desactiva (no borra) un oficio: su historial de valoraciones se conserva.
    No permite quitar el último oficio activo. Devuelve True si se desactivó.
    """
    conn = get_connection()
    active = conn.execute(
        "SELECT COUNT(*) AS n FROM professional_trades WHERE professional_id = ? AND active = 1",
        (professional_id,),
    ).fetchone()["n"]

    if active <= 1:
        conn.close()
        return False

    conn.execute(
        "UPDATE professional_trades SET active = 0 WHERE id = ? AND professional_id = ?",
        (trade_id, professional_id),
    )
    sync_professional_summary(conn, professional_id)
    conn.commit()
    conn.close()
    return True


def get_trade_ratings(professional_id):
    """Valoración independiente de cada oficio (activos e inactivos)."""
    result = []
    for trade in get_trades(professional_id, active_only=False):
        total, average = get_professional_rating(professional_id, trade["trade"])
        result.append({"trade": trade, "total": total, "average": average})
    return result


# ============================================================
# FINALIZACIÓN POR AMBAS PARTES, RECHAZO Y CONTACTO
# ============================================================

def confirm_request_completion(request_id, party, client_id=None, professional_id=None):
    """
    Registra la confirmación de finalización de una de las partes.
    Devuelve 'Finalizada' si ya confirmaron ambas, 'Esperando' si falta la otra parte
    o None si la solicitud no se puede confirmar (otro estado / no le pertenece).
    """
    column = "client_confirmed" if party == "client" else "professional_confirmed"
    owner_sql = "client_id = ?" if party == "client" else "professional_id = ?"
    owner_id = client_id if party == "client" else professional_id

    conn = get_connection()
    cur = conn.execute(
        f"""
        UPDATE requests SET {column} = 1, updated_at = ?
        WHERE id = ? AND status = 'Aceptada' AND {owner_sql}
        """,
        (now_str(), request_id, owner_id),
    )

    if cur.rowcount != 1:
        conn.commit()
        conn.close()
        return None

    row = conn.execute(
        "SELECT client_confirmed, professional_confirmed FROM requests WHERE id = ?",
        (request_id,),
    ).fetchone()

    outcome = "Esperando"
    if row["client_confirmed"] and row["professional_confirmed"]:
        conn.execute(
            "UPDATE requests SET status = 'Finalizada', updated_at = ? WHERE id = ?",
            (now_str(), request_id),
        )
        outcome = "Finalizada"

    conn.commit()
    conn.close()
    return outcome


def reject_request(request_id, professional_id, reason, detail=""):
    """Rechaza una solicitud Pendiente registrando el motivo. True si se aplicó."""
    conn = get_connection()
    cur = conn.execute(
        """
        UPDATE requests
        SET status = 'Rechazada', reject_reason = ?, reject_detail = ?, updated_at = ?
        WHERE id = ? AND professional_id = ? AND status = 'Pendiente'
        """,
        (reason, detail.strip(), now_str(), request_id, professional_id),
    )
    conn.commit()
    changed = cur.rowcount == 1
    conn.close()
    return changed


def get_contact_info(user_id):
    """Datos de contacto de un usuario (solo deben mostrarse con la solicitud aceptada)."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT u.name, u.email, up.phone, up.contact_preference
        FROM users u
        LEFT JOIN user_profiles up ON up.user_id = u.id
        WHERE u.id = ?
        """,
        (user_id,),
    ).fetchone()
    conn.close()
    return row


def get_client_rating_for_request(request_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM client_ratings WHERE request_id = ?", (request_id,)
    ).fetchone()
    conn.close()
    return row


# ============================================================
# DATOS DE DEMOSTRACIÓN: descripciones, perfiles y actividad
# ============================================================

DEMO_ABOUT = {
    "carlos@overol.cl": (
        "Gasfiter con 8 años de experiencia en reparación de fugas, destapes e "
        "instalación de calefont. Trabajo ordenado y con presupuesto claro antes de comenzar."
    ),
    "daniel@overol.cl": (
        "Técnico eléctrico con 6 años de experiencia en tableros, enchufes e "
        "iluminación. Priorizo la seguridad de la instalación y dejo todo probado."
    ),
    "marcelo@overol.cl": (
        "Maestro multipropósito con 5 años de experiencia en carpintería y pintura. "
        "Resuelvo los arreglos del hogar en una sola visita."
    ),
}

DEMO_PROFILES = {
    "cliente@overol.cl": ("+56 9 1111 1111", "Maipú", "Av. Los Pajaritos 1234"),
    "carlos@overol.cl": ("+56 9 2222 2222", "Santiago", "Calle Moneda 456"),
    "daniel@overol.cl": ("+56 9 3333 3333", "Maipú", "Av. Pajaritos 2020"),
    "marcelo@overol.cl": ("+56 9 4444 4444", "Pudahuel", "Av. San Pablo 3100"),
}


def seed_demo_extras(conn):
    """Deja a los usuarios demo listos para entrar directo y con contenido que mostrar."""
    now = now_str()

    for email, text in DEMO_ABOUT.items():
        conn.execute(
            """
            UPDATE professionals SET about = ?
            WHERE (about IS NULL OR about = '')
              AND user_id = (SELECT id FROM users WHERE email = ?)
            """,
            (text, email),
        )

    conn.execute(
        """
        UPDATE professionals
        SET work_days = 'Lun,Mar,Mié,Jue,Vie', work_start = '09:00', work_end = '18:00',
            schedule = 'Lun, Mar, Mié, Jue, Vie · 09:00–18:00'
        WHERE work_days = '' AND schedule = ''
        """
    )

    for email, (phone, commune, address) in DEMO_PROFILES.items():
        user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            continue
        exists = conn.execute(
            "SELECT 1 FROM user_profiles WHERE user_id = ?", (user["id"],)
        ).fetchone()
        if not exists:
            conn.execute(
                """
                INSERT INTO user_profiles
                (user_id, phone, commune, contact_preference,
                 service_interest, bio, address, created_at, updated_at)
                VALUES (?, ?, ?, 'WhatsApp', '', '', ?, ?, ?)
                """,
                (user["id"], phone, commune, address, now, now),
            )

    # Actividad de ejemplo: solo en una base sin solicitudes
    if conn.execute("SELECT COUNT(*) AS n FROM requests").fetchone()["n"]:
        return

    client = conn.execute("SELECT id FROM users WHERE email = 'cliente@overol.cl'").fetchone()
    if not client:
        return

    def pro_id(email):
        row = conn.execute(
            """
            SELECT p.id FROM professionals p JOIN users u ON u.id = p.user_id
            WHERE u.email = ?
            """,
            (email,),
        ).fetchone()
        return row["id"] if row else None

    carlos, daniel, marcelo = (
        pro_id("carlos@overol.cl"), pro_id("daniel@overol.cl"), pro_id("marcelo@overol.cl")
    )
    if not (carlos and daniel and marcelo):
        return

    # (profesional, oficio, comuna, zona, fecha, descripción, estado, confirmaciones, (calidad, puntualidad, trato, comentario))
    demo = [
        (carlos, "Gasfitería", "Santiago", "Cocina", "2026-09-12",
         "Fuga bajo el lavaplatos de la cocina.", "Finalizada", 1,
         (5, 5, 5, "Llegó puntual, encontró la fuga rápido y dejó todo limpio.")),
        (daniel, "Electricidad", "Maipú", "Living", "2026-09-18",
         "Cambio de enchufes y revisión del tablero.", "Finalizada", 1,
         (5, 4, 5, "Muy prolijo y explicó cada paso. Recomendado.")),
        (marcelo, "Carpintería", "Pudahuel", "Dormitorio", "2026-09-25",
         "Ajuste de las puertas del closet.", "Finalizada", 1,
         (4, 5, 5, "Buen trabajo y buen trato. Quedó tal como lo pedí.")),
        (daniel, "Electricidad", "Maipú", "Living", "2026-10-20",
         "Instalación de focos en el living.", "Aceptada", 0, None),
        (carlos, "Gasfitería", "Santiago", "Baño", "2026-10-22",
         "Cambio de la llave del lavamanos.", "Pendiente", 0, None),
        (marcelo, "Pintura", "Pudahuel", "Living", "2026-10-05",
         "Pintar las paredes del living.", "Pendiente", 0, None),
    ]

    for pid, trade, commune, zone, date, desc, status, confirmed, rating in demo:
        created = now if desc != "Pintar las paredes del living." else (
            datetime.now() - timedelta(days=5)
        ).strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute(
            """
            INSERT INTO requests
            (client_id, professional_id, service, trade, home_zone, commune,
             tentative_date, tentative_time, description, status,
             client_confirmed, professional_confirmed, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, '09:00 - 11:00', ?, ?, ?, ?, ?, ?)
            """,
            (client["id"], pid, trade, trade, zone, commune, date, desc, status,
             confirmed, confirmed, created, created),
        )
        if rating:
            q, pu, tr, comment = rating
            conn.execute(
                """
                INSERT INTO ratings
                (request_id, client_id, professional_id, trade, quality,
                 punctuality, treatment, comment, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (cur.lastrowid, client["id"], pid, trade, q, pu, tr, comment, now),
            )


def get_public_reviews(professional_id, limit=5):
    """Opiniones con comentario, sin datos del cliente (se muestran en el perfil)."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT quality, punctuality, treatment, comment, trade
        FROM ratings
        WHERE professional_id = ? AND comment IS NOT NULL AND comment != ''
        ORDER BY id DESC
        LIMIT ?
        """,
        (professional_id, limit),
    ).fetchall()
    conn.close()
    return rows


def get_platform_stats():
    """Cifras reales para la portada."""
    professionals = get_all_professionals()
    communes = {
        c.strip()
        for p in professionals
        for c in p["coverage"].split(",")
        if c.strip()
    }
    trades = set()
    for p in professionals:
        trades.update(t["trade"] for t in get_trades(p["id"]))

    conn = get_connection()
    reviews = conn.execute("SELECT COUNT(*) AS n FROM ratings").fetchone()["n"]
    conn.close()

    return {
        "professionals": len(professionals),
        "trades": len(trades),
        "communes": len(communes),
        "reviews": reviews,
    }


# ============================================================
# SOLICITUDES: vencimiento, creación y cancelaciones
# ============================================================

def request_expires_at(created_at):
    """Fecha límite para que el profesional responda una solicitud pendiente."""
    from core.constants import HORAS_VENCIMIENTO

    return datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S") + timedelta(hours=HORAS_VENCIMIENTO)


def expire_pending_requests():
    """Marca como «Vencida» toda solicitud pendiente con más de 72 horas. Devuelve cuántas venció."""
    from core.constants import HORAS_VENCIMIENTO

    limit = (datetime.now() - timedelta(hours=HORAS_VENCIMIENTO)).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    ids = [
        row["id"]
        for row in conn.execute(
            "SELECT id FROM requests WHERE status = 'Pendiente' AND created_at <= ?", (limit,)
        ).fetchall()
    ]

    if ids:
        marks = ",".join("?" for _ in ids)
        conn.execute(
            f"UPDATE requests SET status = 'Vencida', updated_at = ? WHERE id IN ({marks})",
            [now_str(), *ids],
        )
        conn.commit()
    conn.close()

    for request_id in ids:
        audit(None, "EXPIRE", "requests", request_id,
              f"Solicitud vencida: sin respuesta en {HORAS_VENCIMIENTO} horas")

    return len(ids)


def next_work_date(work_days, start=None):
    """Primer día desde `start` (hoy por defecto) en que el profesional trabaja."""
    from core.constants import DIAS_SEMANA

    day = start or datetime.today().date()
    allowed = [d for d in (work_days or "").split(",") if d]

    if not allowed:
        return day

    for _ in range(8):
        if DIAS_SEMANA[day.weekday()] in allowed:
            return day
        day += timedelta(days=1)

    return day


def create_request(client_id, professional_id, trade, home_zone, commune, date, time, description):
    """
    Crea una solicitud de visita aplicando TODAS las reglas de negocio.
    Devuelve (True, id) o (False, mensaje).
    Solo un usuario con rol «cliente» puede agendar.
    """
    from core.constants import DIAS_SEMANA

    conn = get_connection()
    client = conn.execute("SELECT role, active FROM users WHERE id = ?", (client_id,)).fetchone()

    if not client or not client["active"] or client["role"] != "cliente":
        conn.close()
        return False, "Solo los clientes pueden solicitar visitas."

    pro = conn.execute(
        """
        SELECT p.*, u.active AS user_active
        FROM professionals p JOIN users u ON u.id = p.user_id
        WHERE p.id = ?
        """,
        (professional_id,),
    ).fetchone()

    if not pro or not pro["user_active"] or not pro["verified"] or not pro["availability"]:
        conn.close()
        return False, "Este profesional no está disponible para recibir solicitudes."

    if not conn.execute(
        "SELECT 1 FROM professional_trades WHERE professional_id = ? AND trade = ? AND active = 1",
        (professional_id, trade),
    ).fetchone():
        conn.close()
        return False, "El profesional no ofrece ese oficio."

    if not description.strip():
        conn.close()
        return False, "La descripción del trabajo es obligatoria."

    if date < datetime.today().date():
        conn.close()
        return False, "La fecha no puede ser anterior a hoy."

    work_days = [d for d in (pro["work_days"] or "").split(",") if d]
    if work_days and DIAS_SEMANA[date.weekday()] not in work_days:
        conn.close()
        return False, (
            f"El profesional no trabaja los {DIAS_SEMANA[date.weekday()]}. "
            f"Días disponibles: {', '.join(work_days)}."
        )

    start, _, end = time.partition(" - ")
    if pro["work_start"] and pro["work_end"] and not (
        pro["work_start"] <= start and end <= pro["work_end"]
    ):
        conn.close()
        return False, (
            f"El profesional atiende entre {pro['work_start']} y {pro['work_end']}."
        )

    duplicated = conn.execute(
        """
        SELECT id FROM requests
        WHERE client_id = ? AND professional_id = ? AND status = 'Pendiente'
        """,
        (client_id, professional_id),
    ).fetchone()

    if duplicated:
        conn.close()
        return False, (
            f"Ya tienes la solicitud #{duplicated['id']} pendiente con este profesional. "
            "Espera su respuesta o cancélala desde «Mis solicitudes»."
        )

    cur = conn.execute(
        """
        INSERT INTO requests
        (client_id, professional_id, service, trade, home_zone, commune,
         tentative_date, tentative_time, description, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pendiente', ?, ?)
        """,
        (client_id, professional_id, trade, trade, home_zone, commune,
         str(date), time, description.strip(), now_str(), now_str()),
    )
    request_id = cur.lastrowid
    conn.commit()
    conn.close()
    return True, request_id


def cancel_request_by_client(request_id, client_id):
    """El cliente cancela una solicitud pendiente o aceptada. True si se aplicó."""
    conn = get_connection()
    cur = conn.execute(
        """
        UPDATE requests
        SET status = 'Cancelada', cancelled_by = 'cliente', updated_at = ?
        WHERE id = ? AND client_id = ? AND status IN ('Pendiente', 'Aceptada')
        """,
        (now_str(), request_id, client_id),
    )
    conn.commit()
    changed = cur.rowcount == 1
    conn.close()
    return changed


def cancel_request_by_professional(request_id, professional_id, reason):
    """
    El profesional cancela una solicitud aceptada indicando el motivo (1 a 500 caracteres).
    Devuelve (True, "") o (False, mensaje).
    """
    from core.constants import MAX_TEXTO

    reason = (reason or "").strip()

    if not reason:
        return False, "Debes escribir el motivo de la cancelación."

    if len(reason) > MAX_TEXTO:
        return False, f"El motivo no puede superar los {MAX_TEXTO} caracteres."

    conn = get_connection()
    cur = conn.execute(
        """
        UPDATE requests
        SET status = 'Cancelada', cancelled_by = 'profesional', cancel_reason = ?, updated_at = ?
        WHERE id = ? AND professional_id = ? AND status = 'Aceptada'
        """,
        (reason, now_str(), request_id, professional_id),
    )
    conn.commit()
    changed = cur.rowcount == 1
    conn.close()

    if not changed:
        return False, "La solicitud ya cambió de estado."

    return True, ""


# ============================================================
# BLOQUEO DE INICIO DE SESIÓN
# ============================================================

def get_lock_remaining(email, action="LOGIN_FAILED", reset_action="LOGIN_RESET"):
    """
    Segundos que faltan para desbloquear el ingreso de ese correo (0 si no está bloqueado).
    Se bloquea al acumular MAX_INTENTOS_LOGIN fallos dentro de MINUTOS_BLOQUEO minutos
    (los fallos anteriores a un ingreso exitoso no cuentan).
    """
    from core.constants import MAX_INTENTOS_LOGIN, MINUTOS_BLOQUEO

    email = email.strip().lower()
    since = (datetime.now() - timedelta(minutes=MINUTOS_BLOQUEO)).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT created_at FROM audit_log
        WHERE action = ? AND details = ? AND created_at >= ?
          AND id > COALESCE(
                (SELECT MAX(id) FROM audit_log WHERE action = ? AND details = ?), 0)
        ORDER BY created_at DESC
        """,
        (action, email, since, reset_action, email),
    ).fetchall()
    conn.close()

    if len(rows) < MAX_INTENTOS_LOGIN:
        return 0

    last = datetime.strptime(rows[0]["created_at"], "%Y-%m-%d %H:%M:%S")
    remaining = (last + timedelta(minutes=MINUTOS_BLOQUEO) - datetime.now()).total_seconds()
    return max(0, int(remaining) + 1)


def count_login_failures(email, action="LOGIN_FAILED", reset_action="LOGIN_RESET"):
    """Fallos recientes (para avisar «te quedan N intentos»)."""
    from core.constants import MINUTOS_BLOQUEO

    email = email.strip().lower()
    since = (datetime.now() - timedelta(minutes=MINUTOS_BLOQUEO)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    row = conn.execute(
        """
        SELECT COUNT(*) AS n FROM audit_log
        WHERE action = ? AND details = ? AND created_at >= ?
          AND id > COALESCE(
                (SELECT MAX(id) FROM audit_log WHERE action = ? AND details = ?), 0)
        """,
        (action, email, since, reset_action, email),
    ).fetchone()
    conn.close()
    return row["n"]


# ============================================================
# MENSAJES A SOPORTE (Historia: cliente/profesional -> administrador)
# ============================================================

def _participant_of_request(conn, request_id, user_id):
    row = conn.execute(
        """
        SELECT r.client_id, p.user_id AS professional_user_id
        FROM requests r JOIN professionals p ON p.id = r.professional_id
        WHERE r.id = ?
        """,
        (request_id,),
    ).fetchone()
    return bool(row) and user_id in (row["client_id"], row["professional_user_id"])


def add_support_message(request_id, user_id, body, from_admin=False):
    """
    Agrega un mensaje al hilo de soporte de una solicitud.
    Un usuario solo puede escribir sobre solicitudes en las que participa.
    Devuelve (True, "") o (False, mensaje).
    """
    from core.constants import MAX_TEXTO

    body = (body or "").strip()

    if not body:
        return False, "Escribe un mensaje."

    if len(body) > MAX_TEXTO:
        return False, f"El mensaje no puede superar los {MAX_TEXTO} caracteres."

    conn = get_connection()

    if not from_admin and not _participant_of_request(conn, request_id, user_id):
        conn.close()
        return False, "No participas en esta solicitud."

    conn.execute(
        """
        INSERT INTO support_messages (request_id, user_id, from_admin, body, read_by_admin, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (request_id, user_id, 1 if from_admin else 0, body, 1 if from_admin else 0, now_str()),
    )
    conn.commit()
    conn.close()
    return True, ""


def get_support_thread(request_id, user_id):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM support_messages
        WHERE request_id = ? AND user_id = ?
        ORDER BY id
        """,
        (request_id, user_id),
    ).fetchall()
    conn.close()
    return rows


def get_support_inbox():
    """Un hilo por (solicitud, usuario), con mensajes sin leer, para el administrador."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            m.request_id,
            m.user_id,
            u.name AS user_name,
            u.role AS user_role,
            r.status AS request_status,
            r.trade AS trade,
            COUNT(*) AS total,
            SUM(CASE WHEN m.from_admin = 0 AND m.read_by_admin = 0 THEN 1 ELSE 0 END) AS unread,
            MAX(m.id) AS last_id
        FROM support_messages m
        JOIN users u ON u.id = m.user_id
        JOIN requests r ON r.id = m.request_id
        GROUP BY m.request_id, m.user_id
        ORDER BY unread DESC, last_id DESC
        """
    ).fetchall()
    conn.close()
    return rows


def mark_support_thread_read(request_id, user_id):
    conn = get_connection()
    conn.execute(
        """
        UPDATE support_messages SET read_by_admin = 1
        WHERE request_id = ? AND user_id = ? AND from_admin = 0
        """,
        (request_id, user_id),
    )
    conn.commit()
    conn.close()


# ============================================================
# ESTADÍSTICAS PARA LOS PERFILES
# ============================================================

def get_professional_stats(professional_id):
    """Cifras de la cabecera del perfil profesional."""
    conn = get_connection()
    finished = conn.execute(
        "SELECT COUNT(*) AS n FROM requests WHERE professional_id = ? AND status = 'Finalizada'",
        (professional_id,),
    ).fetchone()["n"]
    since = conn.execute(
        """
        SELECT u.created_at FROM professionals p JOIN users u ON u.id = p.user_id
        WHERE p.id = ?
        """,
        (professional_id,),
    ).fetchone()
    years = conn.execute(
        """
        SELECT MAX(years_experience) AS y FROM professional_trades
        WHERE professional_id = ? AND active = 1
        """,
        (professional_id,),
    ).fetchone()["y"]
    conn.close()

    reviews, average = get_professional_rating(professional_id)

    return {
        "finished": finished,
        "reviews": reviews,
        "average": average,
        "years": years,
        "member_since": since["created_at"][:4] if since and since["created_at"] else "",
    }


def get_client_stats(user_id):
    """Cifras de la cabecera del perfil personal del cliente."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'Finalizada' THEN 1 ELSE 0 END) AS finished
        FROM requests WHERE client_id = ?
        """,
        (user_id,),
    ).fetchone()
    rated = conn.execute(
        "SELECT COUNT(*) AS n FROM ratings WHERE client_id = ?", (user_id,)
    ).fetchone()["n"]
    since = conn.execute("SELECT created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    return {
        "requests": row["total"] or 0,
        "finished": row["finished"] or 0,
        "rated": rated,
        "member_since": since["created_at"][:4] if since and since["created_at"] else "",
    }
