"""Capa de datos: conexión SQLite, creación de tablas, datos demo, auditoría y consultas."""

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

    seed_data(conn)
    normalize_existing_ruts(conn)
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
            "specialties": "Gasfitería",
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
            "specialties": "Electricidad",
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
            "specialties": "Carpintería,Pintura",
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
                service_interest = ?, bio = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (
                phone.strip(),
                commune.strip(),
                contact_preference,
                service_interest.strip(),
                bio.strip(),
                now,
                user_id,
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO user_profiles
            (user_id, phone, commune, contact_preference,
             service_interest, bio, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                phone.strip(),
                commune.strip(),
                contact_preference,
                service_interest.strip(),
                bio.strip(),
                now,
                now,
            ),
        )

    conn.commit()
    conn.close()


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
        specialties = [
            x.strip()
            for x in row["specialties"].split(",")
            if x.strip()
        ]

        coverage = [
            x.strip()
            for x in row["coverage"].split(",")
            if x.strip()
        ]

        if (
            specialty != "Todas"
            and specialty not in specialties
            and specialty != row["trade"]
        ):
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


def get_professional_rating(professional_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            AVG((quality + punctuality + treatment) / 3.0) AS average
        FROM ratings
        WHERE professional_id = ?
        """,
        (professional_id,),
    ).fetchone()
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


def count_recent_failed_logins(email, minutes=10):
    """Cuenta intentos fallidos de login recientes para un correo (anti fuerza bruta)."""
    since = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    row = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM audit_log
        WHERE action = 'LOGIN_FAILED'
          AND details = ?
          AND created_at >= ?
        """,
        (email.strip().lower(), since),
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
