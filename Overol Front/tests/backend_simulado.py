"""Imitación en memoria del backend Django de Overol, para las pruebas AppTest.

Reemplaza `requests.request` y responde con los mismos códigos y formatos que el backend
real de origin/main (leídos de su código: apps/authentication y apps/catalog):

  POST /auth/token/            200 {access, refresh} · 401 credenciales · 429 {detail, retry_after}
  POST /auth/token/refresh/    200 {access, refresh} (rota y anula el anterior) · 401 token_not_valid
  POST /auth/logout/           204 (anula el refresh enviado) · 401 sin acceso
  GET|PATCH /auth/me/          200 perfil · 400 por campo · 401 sin acceso
  POST /auth/register/         201 {id, email, role} · 400 por campo
  POST /auth/password/change/  204 · 400 {current_password|new_password: [...]}
  POST /auth/password/reset/   202 {detail}
  GET /catalog/categories/ · /specialties/ · /professionals/ (paginado) · /professionals/{id}/
  GET|PATCH /professionals/me/availability/   403 si no es profesional
  GET|POST /requests/          lista por rol · 201 · 400 por campo o non_field_errors
  POST /requests/{id}/{accion}/  200 · 400 motivo · 403 sin permiso · 404 · 409 transición inválida

Cualquier otra ruta responde 404, como una ruta que el backend no tiene.
No reemplaza una prueba contra el backend real (ver PRUEBAS_MANUALES.md).
"""

import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from itertools import count
from urllib.parse import parse_qs, urlsplit

DEMO_PASSWORD = "OverolDemo123!"
COMMON_PASSWORDS = {"password", "password123", "12345678", "123456789", "qwerty123", "overol123"}
NAME_RE = re.compile(r"[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s']+")

# Parte del catálogo oficial del backend (66 oficios); los últimos no tienen especialidades
CATEGORIES = {
    1: ("Gasfitería", ["Fugas de agua", "Destapes", "Grifería y artefactos sanitarios", "Calefont y termo"]),
    2: ("Electricidad", ["Enchufes e interruptores", "Tableros eléctricos", "Iluminación", "Instalación de ventiladores"]),
    3: ("Carpintero", ["Muebles a medida", "Reparación de puertas", "Closets", "Instalación de pisos"]),
    4: ("Pintor", ["Pintura interior", "Pintura exterior", "Empastes y reparaciones", "Impermeabilización"]),
    5: ("Cerrajería", ["Apertura de puertas", "Cambio de chapas"]),
    6: ("Soldador", []),
    7: ("Jardinero", []),
}


KEYWORDS = {
    1: "gasfiter, gasfíter, gasfitería, calefont, cañerías",
    2: "eléctrico, electricista, electricidad, enchufes, tablero",
    3: "carpintero, carpintería",
    4: "pintor, pintura",
    5: "cerrajero, cerrajería, cerradura, llave",
    6: "soldador, soldadura",
    7: "jardinero, jardinería",
}


class Respuesta:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data
        self.content = json.dumps(data, default=str).encode() if data is not None else b""

    def json(self):
        return self._data


class BackendSimulado:
    def __init__(self):
        self.ids = count(1)
        self.tokens = count(1)
        self.users = {}
        self.access = {}       # token de acceso → id de usuario
        self.refresh = {}      # token de renovación vigente → id de usuario
        self.blacklist = set()
        self.calls = []        # (método, ruta, cuerpo)
        self.reset_emails = []
        self.reset_codes = {}       # correo → {code, attempts, expires}
        self.code_seq = count(123456)
        self.msg_ids = count(1)
        self.payments = {}
        self.payment_ids = count(1)
        self.plan_amount = 10000
        self.assistant_use = {}     # id de usuario → consultas en la hora
        self.assistant_down = False
        self.assistant_messages = []
        self._files = None
        self.ratings = []
        self.claims = {}
        self.notifications = []
        self.audit_log = []
        self.caido = False
        self.page_size_max = 50
        self.visits = {}
        self.visit_ids = count(1)
        self.before_action = None  # función que corre justo antes de una acción (carreras)
        self.specialties = {}
        sid = count(1)
        for cid, (_, names) in CATEGORIES.items():
            for name in names:
                self.specialties[next(sid)] = (name, cid)
        self._seed()

    # ---------------- Datos de demo (como seed_demo, ampliado) ----------------
    def _seed(self):
        self.add_user("cliente1@demo.overol.cl", "Clara", "Pérez", "CLIENT", "11111111-1",
                      phone="+56 9 1111 1111", address="Av. Los Pajaritos 1234", commune="Maipú")
        self.add_user("cliente2@demo.overol.cl", "Cristián", "Lagos", "CLIENT", "22222222-2")
        self.add_user("admin@demo.overol.cl", "Ana", "Admin", "ADMIN", "33333333-3",
                      phone="+56 9 3333 3333", address="Oficina 1", commune="Santiago")
        self.add_professional(
            "profesional1@demo.overol.cl", "Carlos", "Muñoz", "12345678-5",
            trades=[(1, 8, ["Fugas de agua", "Calefont y termo"])],
            coverage=["Santiago", "Ñuñoa", "Providencia"], fee=15000, rating=4.5,
            bio="Gasfiter con 8 años de experiencia en reparación de fugas, destapes e instalación "
                "de calefont. Trabajo ordenado y con presupuesto claro antes de comenzar.",
            opinions=[(5, 5, 4, "Muy prolijo y puntual con la llave del baño")],
        )
        self.add_professional(
            "profesional2@demo.overol.cl", "Daniel", "Soto", "13456789-9",
            trades=[(2, 6, ["Enchufes e interruptores", "Tableros eléctricos"])],
            coverage=["Maipú", "Pudahuel", "La Florida"], fee=18000, rating=4.0,
            bio="Técnico eléctrico con 6 años de experiencia en tableros, enchufes e iluminación. "
                "Priorizo la seguridad de la instalación y dejo todo probado.",
        )
        self.add_professional(
            "profesional3@demo.overol.cl", "Marcelo", "Rojas", "14567890-0",
            trades=[(3, 5, ["Muebles a medida"]), (4, 5, ["Pintura interior"])],
            coverage=["Pudahuel", "Maipú", "Santiago"], fee=12000, rating=0,
            bio="Maestro multipropósito con 5 años de experiencia en carpintería y pintura. "
                "Resuelvo los arreglos del hogar en una sola visita.",
        )
        self.add_professional(
            "pendiente@demo.overol.cl", "Pablo", "Pendiente", "15678901-6",
            trades=[(1, 2, [])], coverage=["Santiago"], status="PENDING",
        )

    def add_user(self, email, first, last, role, rut, password=DEMO_PASSWORD, phone="", address="", commune=""):
        uid = next(self.ids)
        self.users[uid] = {
            "id": uid, "email": email, "first_name": first, "last_name": last, "role": role,
            "rut": rut, "password": password, "phone": phone, "address": address, "commune": commune,
            "account_status": "ACTIVE", "failed": 0, "locked_until": 0, "professional": None,
        }
        return uid

    def add_professional(self, email, first, last, rut, trades, coverage, fee=0, rating=0, bio="",
                         opinions=(), status="APPROVED"):
        uid = self.add_user(email, first, last, "PROFESSIONAL", rut,
                            phone="+56 9 2222 2222", address="Calle Moneda 456", commune=coverage[0])
        self.users[uid]["professional"] = {
            "id": 100 + uid, "verification_status": status, "visit_fee": fee, "rating_avg": rating,
            "bio": bio, "headline": "", "contact_preference": "WhatsApp",
            "work_days": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            "work_start": "09:00:00", "work_end": "18:00:00", "is_available": True,
            "coverage_communes": list(coverage),
            "trades": [{"id": 1000 + uid * 10 + i, "category_id": cid, "years_experience": years, "specialties": specs}
                       for i, (cid, years, specs) in enumerate(trades)],
            "opinions": [{"quality": q, "punctuality": p, "treatment": t, "comment": c,
                          "created_at": "2026-11-01T10:00:00", "author_name": "Clara P."}
                         for q, p, t, c in opinions],
            # Los perfiles de demo tienen suscripción vigente (el seed_demo real no la trae)
            "subscription_expires_at": datetime.now(timezone.utc) + timedelta(days=20) if status == "APPROVED" else None,
        }
        return uid

    def by_email(self, email):
        return next((u for u in self.users.values() if u["email"] == (email or "").strip().lower()), None)

    def professional(self, email):
        return self.by_email(email)["professional"]

    def issue_tokens(self, uid):
        access, refresh = f"acc-{next(self.tokens)}", f"ref-{next(self.tokens)}"
        self.access[access] = uid
        self.refresh[refresh] = uid
        return access, refresh

    def expire_access(self):
        """Todos los tokens de acceso vencen (obliga al front a renovar)."""
        self.access.clear()

    # ---------------- Despacho de peticiones ----------------
    def request(self, method, url, json=None, headers=None, timeout=None, **kwargs):
        import requests

        from core.constants import API_BASE_URL

        parts = urlsplit(url.replace(API_BASE_URL, "/"))
        self.calls.append((method, parts.path + (f"?{parts.query}" if parts.query else ""), json))
        if self.caido:
            raise requests.ConnectionError("backend simulado apagado")

        query = {k: v[0] for k, v in parse_qs(parts.query).items()}
        token = (headers or {}).get("Authorization", "").removeprefix("Bearer ").strip()
        user = self.users.get(self.access.get(token)) if token else None
        if user and user["account_status"] == "DEACTIVATED":
            user = None  # JWTAuthentication rechaza un usuario con is_active=False
        body = json or kwargs.get("data") or {}
        self._files = kwargs.get("files")  # multipart: {campo: (nombre, bytes, tipo)}
        path = parts.path

        routes = {
            ("POST", "/auth/token/"): self._token,
            ("POST", "/auth/token/refresh/"): self._refresh,
            ("POST", "/auth/register/"): self._register,
            ("POST", "/auth/password/reset/"): self._reset,
            ("POST", "/auth/password/reset/confirm/"): self._reset_confirm,
            ("GET", "/catalog/categories/"): self._categories,
            ("GET", "/catalog/specialties/"): self._specialties,
            ("GET", "/catalog/professionals/"): self._search,
        }
        protected = {
            ("POST", "/auth/logout/"): self._logout,
            ("GET", "/auth/me/"): self._me,
            ("PATCH", "/auth/me/"): self._patch_me,
            ("POST", "/auth/password/change/"): self._change_password,
            ("GET", "/requests/"): self._list_visits,
            ("POST", "/requests/"): self._create_visit,
            ("GET", "/auth/verification/documents/"): self._documents,
            ("POST", "/auth/verification/documents/"): self._upload_documents,
            ("GET", "/auth/verification/messages/"): self._messages,
            ("POST", "/auth/verification/messages/"): self._send_message,
            ("GET", "/payments/professional-subscription/"): self._subscription,
            ("POST", "/payments/professional-subscription/transbank/"): self._start_subscription,
            ("POST", "/assistant/chat/"): self._assistant,
            ("POST", "/ratings/"): self._rate,
            ("GET", "/claims/"): self._list_claims,
            ("POST", "/claims/"): self._create_claim,
        }
        for prefix in ("/professionals/me/availability/", "/catalog/professionals/me/availability/"):
            protected[("GET", prefix)] = lambda u, b: self._availability(u, b, "GET")
            protected[("PATCH", prefix)] = lambda u, b: self._availability(u, b, "PATCH")
        if (method, path) in routes:
            return routes[(method, path)](body, query)
        if (method, path) in protected:
            if not user:
                return Respuesta(401, {"detail": "Las credenciales de autenticación no se proveyeron.",
                                       "code": "not_authenticated"})
            return protected[(method, path)](user, body)
        match = re.fullmatch(r"/catalog/professionals/(\d+)/", path)
        if method == "GET" and match:
            return self._detail(int(match.group(1)))
        match = re.fullmatch(r"/payments/visits/(\d+)/(transbank/)?", path)
        if match and user and method in ("GET", "POST"):
            vid = int(match.group(1))
            if method == "POST" and match.group(2):
                return self._start_visit_payment(user, vid)
            if method == "GET" and not match.group(2):
                return self._visit_payment(user, vid)
        match = re.fullmatch(r"/claims/(\d+)/(\w+)/", path)
        if method == "POST" and match and user:
            return self._claim_action(user, int(match.group(1)), match.group(2), body)
        match = re.fullmatch(r"/requests/(\d+)/(\w+)/", path)
        if method == "POST" and match:
            if not user:
                return Respuesta(401, {"detail": "Las credenciales de autenticación no se proveyeron.",
                                       "code": "not_authenticated"})
            return self._visit_action(user, int(match.group(1)), match.group(2), body)
        return Respuesta(404, {"detail": "No encontrado."})

    # ---------------- Autenticación ----------------
    def _token(self, body, _):
        user = self.by_email(body.get("email"))
        now = time.time()
        if user and user["locked_until"] > now:
            return Respuesta(429, {"detail": "La cuenta está temporalmente bloqueada.",
                                   "retry_after": max(1, int(user["locked_until"] - now))})
        if user and user["account_status"] != "ACTIVE":
            return Respuesta(401, {"detail": "Credenciales inválidas."})
        if not user or user["password"] != body.get("password"):
            if user:
                user["failed"] += 1
                if user["failed"] >= 3:
                    user["locked_until"] = now + 5 * 60
            return Respuesta(401, {"detail": "No se encontró una cuenta de usuario activa para las credenciales provistas"})
        user["failed"], user["locked_until"] = 0, 0
        access, refresh = self.issue_tokens(user["id"])
        return Respuesta(200, {"access": access, "refresh": refresh})

    def _refresh(self, body, _):
        old = body.get("refresh")
        uid = self.refresh.pop(old, None)
        # SimpleJWT 5.5 no revisa la cuenta al renovar (solo JWTAuthentication revisa is_active)
        if not uid or old in self.blacklist:
            return Respuesta(401, {"detail": "El token es inválido o ha expirado", "code": "token_not_valid"})
        self.blacklist.add(old)  # ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION
        access, refresh = self.issue_tokens(uid)
        return Respuesta(200, {"access": access, "refresh": refresh})

    def _logout(self, user, body):
        refresh = body.get("refresh")
        if refresh:
            if refresh not in self.refresh:
                return Respuesta(400, {"detail": "El token está en lista negra"})
            self.refresh.pop(refresh)
            self.blacklist.add(refresh)
        return Respuesta(204)

    def _me_data(self, user):
        data = {k: user[k] for k in ("id", "email", "first_name", "last_name", "phone", "rut",
                                     "address", "commune", "role")}
        data.update(username=user["email"], profile_photo=None, client_rating_avg=None)
        pro = user["professional"]
        data["professional_profile_id"] = pro["id"] if pro else None
        data["verification_status"] = pro["verification_status"] if pro else None
        if pro:  # el backend omite estos campos en un cliente (no tiene perfil profesional)
            data.update(bio=pro["bio"], headline=pro["headline"], visit_fee=str(pro["visit_fee"]),
                        contact_preference=pro["contact_preference"], certifications=None)
        return data

    def _me(self, user, _):
        return Respuesta(200, self._me_data(user))

    def _patch_me(self, user, body):
        errors = {}
        if "bio" in body and len(body["bio"] or "") > 500:
            errors["bio"] = ["Asegúrese de que este campo no tenga más de 500 caracteres."]
        if "headline" in body and len(body["headline"] or "") > 160:
            errors["headline"] = ["Asegúrese de que este campo no tenga más de 160 caracteres."]
        if errors:
            return Respuesta(400, errors)
        for key in ("phone", "address", "commune"):
            if key in body:
                user[key] = body[key]
        if user["professional"]:  # en un cliente, el backend descarta estos campos sin error
            for key in ("bio", "headline", "contact_preference", "visit_fee"):
                if key in body:
                    user["professional"][key] = body[key]
        return Respuesta(200, self._me_data(user))

    def _password_problems(self, password, user_data=()):
        problems = []
        if len(password or "") < 8:
            problems.append("La contraseña es demasiado corta. Debe contener al menos 8 caracteres.")
        if (password or "").lower() in COMMON_PASSWORDS:
            problems.append("Esta contraseña es demasiado común.")
        if (password or "").isdigit():
            problems.append("Esta contraseña es completamente numérica.")
        if any(v and v.split("@")[0].lower() in (password or "").lower() for v in user_data):
            problems.append("La contraseña es demasiado similar a la de correo electrónico.")
        return problems

    def _change_password(self, user, body):
        if body.get("current_password") != user["password"]:
            return Respuesta(400, {"current_password": ["La contraseña actual no es correcta."]})
        problems = self._password_problems(body.get("new_password"))
        if problems:
            return Respuesta(400, {"new_password": problems})
        user["password"] = body["new_password"]
        return Respuesta(204)


    def _register(self, body, _):
        errors = {}
        for field in ("email", "first_name", "last_name", "password", "privacy_policy_version", "role"):
            if not body.get(field):
                errors[field] = ["Este campo es requerido."]
        if body.get("email") and self.by_email(body["email"]):
            errors["email"] = ["Ya existe un/a usuario con este/a correo electrónico."]
        if body.get("rut") and any(u["rut"] == body["rut"] for u in self.users.values()):
            errors["rut"] = ["Ya existe un/a usuario con este/a RUT."]
        for field in ("first_name", "last_name"):
            if body.get(field) and not NAME_RE.fullmatch(body[field]):
                errors[field] = ["El nombre solo puede contener letras, espacios y apóstrofes."]
        if errors:
            return Respuesta(400, errors)
        if not body.get("privacy_policy_accepted"):
            return Respuesta(400, {"privacy_policy_accepted": "Debe aceptar la política de privacidad y los términos de uso."})
        if body["role"] not in ("CLIENT", "PROFESSIONAL"):
            return Respuesta(400, {"role": "El rol de registro no es válido."})
        pro = body.get("professional_profile") or {}
        if body["role"] == "PROFESSIONAL":
            if not pro:
                return Respuesta(400, {"professional_profile": "Los datos profesionales son obligatorios."})
            if not isinstance(pro.get("coverage_communes"), list) or not pro["coverage_communes"]:
                return Respuesta(400, {"professional_profile": {"coverage_communes": "Debe indicar al menos una comuna de cobertura."}})
            if not isinstance(pro.get("categories"), list) or not pro["categories"]:
                return Respuesta(400, {"professional_profile": {"categories": "Debe indicar al menos un oficio."}})
        if not body.get("rut"):
            return Respuesta(400, {"rut": "El RUT es obligatorio."})
        problems = self._password_problems(body["password"], (body.get("email"),))
        if problems:
            return Respuesta(400, {"password": problems})
        if body["role"] == "PROFESSIONAL" and not body.get("address"):
            return Respuesta(400, {"address": "La dirección es obligatoria para profesionales."})

        uid = self.add_user(body["email"].lower(), body["first_name"], body["last_name"], body["role"], body["rut"],
                            password=body["password"], phone=body.get("phone", ""),
                            address=body.get("address", ""), commune=body.get("commune", ""))
        if body["role"] == "PROFESSIONAL":
            trades = []
            for i, item in enumerate(pro["categories"]):
                cid = item.get("category") if isinstance(item, dict) else item
                if cid in CATEGORIES:  # el backend real descarta sin error un oficio desconocido
                    selected = item.get("specialties", []) if isinstance(item, dict) else pro.get("specialties", [])
                    # Specialty.objects.filter(pk__in=selected, category=category): las de otro oficio se ignoran
                    names = [self.specialties[s][0] for s in selected if s in self.specialties and self.specialties[s][1] == cid]
                    trades.append({"id": 1000 + uid * 10 + i, "category_id": cid,
                                   "years_experience": item.get("years_experience", 0) if isinstance(item, dict) else 0,
                                   "specialties": names})
            self.users[uid]["professional"] = {
                "id": 100 + uid, "verification_status": "PENDING", "visit_fee": pro.get("visit_fee", 0),
                "rating_avg": 0, "bio": "", "headline": "", "contact_preference": "", "work_days": [],
                "work_start": None, "work_end": None, "is_available": True,
                "coverage_communes": pro["coverage_communes"], "trades": trades, "opinions": [],
            }
        return Respuesta(201, {"id": uid, "email": body["email"].lower(), "role": body["role"]})

    # ---------------- Disponibilidad (apps/catalog/views.AvailabilityView) ----------------
    def _availability(self, user, body, method):
        pro = user["professional"]
        if user["role"] != "PROFESSIONAL" or not pro:
            return Respuesta(403, {"detail": "Solo los profesionales pueden gestionar su disponibilidad."})
        if method == "PATCH":
            for field in ("work_days", "work_start", "work_end", "is_available", "coverage_communes"):
                if field in body:
                    value = body[field]
                    if field in ("work_start", "work_end") and value:
                        value = value[:5] + ":00"  # TimeField: el backend la devuelve como HH:MM:SS
                    pro[field] = value
        return Respuesta(200, {k: pro[k] for k in ("work_days", "work_start", "work_end", "is_available", "coverage_communes")})

    # ---------------- Solicitudes (apps/visits) ----------------
    def _expire(self):
        """Vencimiento perezoso al listar o crear: hoy el backend usa 30 días (PEDIDO 5.6)."""
        limit = datetime.now(timezone.utc) - timedelta(days=30)
        for visit in self.visits.values():
            if visit["status"] == "PENDING" and visit["created_at"] <= limit:
                visit["status"] = "EXPIRED"

    def age_visit(self, vid, days):
        """Hace que una solicitud parezca creada hace `days` días."""
        self.visits[vid]["created_at"] -= timedelta(days=days)

    def _pro_user(self, pid):
        return next((u for u in self.users.values() if u["professional"] and u["professional"]["id"] == pid), None)

    def _visit_data(self, visit, viewer):
        client = self.users[visit["client"]]
        pro_user = self._pro_user(visit["professional"])
        name, cid = self.specialties[visit["specialty"]]
        allowed = viewer["id"] in (client["id"], pro_user["id"]) and visit["status"] in (
            "ACCEPTED", "PROFESSIONAL_FINISHED", "COMPLETED")
        other = pro_user if viewer["id"] == client["id"] else client
        iso = lambda value: value.isoformat().replace("+00:00", "Z") if value else None  # noqa: E731
        return {
            "id": visit["id"], "client": client["id"], "client_name": f"{client['first_name']} {client['last_name']}",
            "professional": visit["professional"], "professional_name": f"{pro_user['first_name']} {pro_user['last_name']}",
            "specialty": visit["specialty"], "specialty_name": name, "category_name": CATEGORIES[cid][0],
            "problem_description": visit["problem_description"], "tentative_schedule": "",
            "visit_date": visit["visit_date"], "visit_time": visit["visit_time"], "commune": visit["commune"],
            "home_zone": None, "visit_address": visit["visit_address"], "status": visit["status"],
            "rejection_reason": visit["rejection_reason"], "cancelled_by": visit["cancelled_by"],
            "cancel_reason": visit["cancel_reason"],
            "client_confirmed_at": iso(visit["client_confirmed_at"]),
            "professional_confirmed_at": iso(visit["professional_confirmed_at"]),
            "completed_at": iso(visit["completed_at"]), "expires_at": iso(visit["expires_at"]),
            "phone": other["phone"] if allowed else None,
            "address": other["address"] if allowed else None,
            "contact_commune": other["commune"] if allowed else None,
            "created_at": iso(visit["created_at"]),
        }

    def _list_visits(self, user, _):
        self._expire()
        if user["role"] == "PROFESSIONAL":
            mine = [v for v in self.visits.values() if user["professional"] and v["professional"] == user["professional"]["id"]]
        else:
            mine = [v for v in self.visits.values() if v["client"] == user["id"]]
        mine.sort(key=lambda v: v["created_at"], reverse=True)
        return Respuesta(200, [self._visit_data(v, user) for v in mine])

    def _create_visit(self, user, body):
        # Campos (ModelSerializer): obligatorios y claves primarias válidas
        errors = {}
        for field in ("professional", "specialty", "problem_description", "visit_address"):
            if field not in body or body[field] is None:
                errors[field] = ["Este campo es requerido."]
            elif isinstance(body[field], str) and not body[field].strip():
                errors[field] = ["Este campo no puede estar en blanco."]
        pro_user = self._pro_user(body.get("professional"))
        if "professional" not in errors and not pro_user:
            errors["professional"] = [f'Clave primaria "{body["professional"]}" inválida - objeto no existe.']
        if "specialty" not in errors and body.get("specialty") not in self.specialties:
            errors["specialty"] = [f'Clave primaria "{body["specialty"]}" inválida - objeto no existe.']
        if errors:
            return Respuesta(400, errors)

        # VisitRequestSerializer.validate, en el mismo orden
        self._expire()
        pro = pro_user["professional"]
        name, cid = self.specialties[body["specialty"]]

        def fail(message, field=None):
            return Respuesta(400, {field: [message]} if field else {"non_field_errors": [message]})

        if user["role"] != "CLIENT":
            return fail("Solo un cliente puede solicitar una visita.")
        if pro["verification_status"] != "APPROVED":
            return fail("El profesional no está verificado.")
        if not self.active_subscription(pro):
            return fail("El profesional no tiene una suscripción mensual vigente.")
        if not any(t["category_id"] == cid and name in t["specialties"] for t in pro["trades"]):
            return fail("La especialidad no pertenece al profesional seleccionado.")
        visit_date = date.fromisoformat(body["visit_date"]) if body.get("visit_date") else None
        if visit_date and visit_date < date.today():
            return fail("La fecha no puede estar en el pasado.", "visit_date")
        if not visit_date:
            return fail("La fecha de visita es obligatoria.", "visit_date")
        if not body.get("visit_time"):
            return fail("La hora de visita es obligatoria.", "visit_time")
        days = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
        if days[visit_date.weekday()] not in {str(d).strip().lower() for d in pro["work_days"] or []}:
            return fail("La solicitud está fuera de los días de atención del profesional.", "visit_date")
        if not pro["work_start"] or not pro["work_end"]:
            return fail("El profesional no tiene un horario de atención configurado.", "visit_time")
        parts = re.split(r"\s*(?:-|–|—|a)\s*", body["visit_time"], maxsplit=1)
        if not all(re.fullmatch(r"\d{2}:\d{2}", x.strip()) for x in (parts[0], parts[-1])):
            return fail("La hora debe usar HH:MM o HH:MM - HH:MM.", "visit_time")
        start, end = parts[0].strip(), parts[-1].strip()
        if end <= start or start < pro["work_start"][:5] or end > pro["work_end"][:5]:
            return fail("La solicitud está fuera del horario de atención del profesional.", "visit_time")
        if any(v["client"] == user["id"] and v["professional"] == pro["id"] and v["status"] == "PENDING"
               for v in self.visits.values()):
            return fail("Ya tienes una solicitud pendiente para este profesional.")
        if not pro["is_available"]:
            return fail("El profesional no está disponible.")
        if body.get("commune") and pro["coverage_communes"] and body["commune"] not in pro["coverage_communes"]:
            return fail("La comuna está fuera de la cobertura del profesional.", "commune")

        vid = next(self.visit_ids)
        now = datetime.now(timezone.utc)
        self.visits[vid] = {
            "id": vid, "client": user["id"], "professional": pro["id"], "specialty": body["specialty"],
            "problem_description": body["problem_description"], "visit_date": body["visit_date"],
            "visit_time": body["visit_time"], "commune": body.get("commune", ""),
            "visit_address": body["visit_address"], "status": "PENDING", "rejection_reason": "",
            "cancelled_by": "", "cancel_reason": "", "client_confirmed_at": None,
            "professional_confirmed_at": None, "completed_at": None,
            "created_at": now, "expires_at": now + timedelta(days=30),
        }
        return Respuesta(201, self._visit_data(self.visits[vid], user))

    def add_visit(self, client_email, pro_email, status="PENDING", **fields):
        """Crea una solicitud directamente (sin validar), para preparar una prueba."""
        client = self.by_email(client_email)
        pro = self.professional(pro_email)
        trade = pro["trades"][0]
        sid = next(s for s, (n, c) in self.specialties.items() if c == trade["category_id"] and n in trade["specialties"])
        vid = next(self.visit_ids)
        now = datetime.now(timezone.utc)
        self.visits[vid] = {
            "id": vid, "client": client["id"], "professional": pro["id"], "specialty": sid,
            "problem_description": "Solicitud de prueba", "visit_date": (date.today() + timedelta(days=3)).isoformat(),
            "visit_time": "09:00 - 11:00", "commune": pro["coverage_communes"][0], "visit_address": client["address"],
            "status": status, "rejection_reason": "", "cancelled_by": "", "cancel_reason": "",
            "client_confirmed_at": None, "professional_confirmed_at": None, "completed_at": None,
            "created_at": now, "expires_at": now + timedelta(days=30),
        }
        self.visits[vid].update(fields)
        return vid

    def _visit_action(self, user, vid, action, body):
        """apps/visits/views.VisitActionView: 409 si la transición no vale, 403 sin permiso."""
        visit = self.visits.get(vid)
        if not visit:
            return Respuesta(404, {"detail": "No encontrado."})
        if self.before_action:
            self.before_action(visit)
        pro_user = self._pro_user(visit["professional"])
        now = datetime.now(timezone.utc)

        def conflict(message):
            return Respuesta(409, {"detail": message})

        def only(owner_id):
            return user["id"] == owner_id

        if action not in ("accept", "reject", "cancel", "cancel_professional", "finish", "confirm"):
            return Respuesta(400, {"detail": "Acción no soportada."})
        professional_actions = ("accept", "reject", "cancel_professional", "finish")
        if not only(pro_user["id"] if action in professional_actions else visit["client"]):
            return Respuesta(403, {"detail": "No tienes permisos para esta solicitud."})

        if action == "accept":
            if visit["status"] != "PENDING":
                return conflict("Solo se pueden aceptar solicitudes pendientes.")
            visit["status"] = "ACCEPTED"
        elif action == "reject":
            reason = body.get("reason")
            if not reason or not str(reason).strip():
                return Respuesta(400, {"reason": ["Este campo es requerido." if reason is None else "Este campo no puede estar en blanco."]})
            if len(reason) > 500:
                return Respuesta(400, {"reason": ["Asegúrese de que este campo no tenga más de 500 caracteres."]})
            if visit["status"] != "PENDING":
                return conflict("Solo se pueden rechazar solicitudes pendientes.")
            visit["status"], visit["rejection_reason"] = "REJECTED", reason
        elif action == "cancel":
            if visit["status"] not in ("PENDING", "ACCEPTED"):
                return conflict("Solo se pueden cancelar solicitudes pendientes o aceptadas.")
            visit.update(status="CANCELLED", cancelled_by="CLIENT", cancel_reason=(body.get("reason") or "").strip()[:500])
        elif action == "cancel_professional":
            reason = (body.get("reason") or "").strip()
            if visit["status"] != "ACCEPTED":
                return conflict("Solo se pueden cancelar solicitudes aceptadas.")
            if not reason or len(reason) > 500:
                return conflict("El motivo debe tener entre 1 y 500 caracteres.")
            visit.update(status="CANCELLED", cancelled_by="PROFESSIONAL", cancel_reason=reason)
        elif action == "finish":
            if visit["status"] != "ACCEPTED":
                return conflict("Solo se pueden finalizar servicios aceptados.")
            visit.update(status="PROFESSIONAL_FINISHED", professional_confirmed_at=now)
            if visit["client_confirmed_at"]:
                visit.update(status="COMPLETED", completed_at=now)
        elif action == "confirm":
            if visit["status"] not in ("ACCEPTED", "PROFESSIONAL_FINISHED"):
                return conflict("El cliente solo puede confirmar un servicio activo.")
            visit["client_confirmed_at"] = now
            if visit["professional_confirmed_at"]:
                visit.update(status="COMPLETED", completed_at=now)
        return Respuesta(200, self._visit_data(visit, user))

    # ---------------- Recuperación con código (authentication/views.py) ----------------
    def _reset(self, body, _):
        self.reset_emails.append(body.get("email"))
        user = self.by_email(body.get("email"))
        if user and user["account_status"] != "DEACTIVATED":
            self.reset_codes[user["email"]] = {"code": f"{next(self.code_seq):06d}", "attempts": 0,
                                                "expires": time.time() + 600}
        return Respuesta(202, {"detail": "Si el correo está registrado, recibirás un código para recuperar tu contraseña."})

    def _reset_confirm(self, body, _):
        errors = {}
        if not body.get("email"):
            errors["email"] = ["Este campo es requerido."]
        if not re.fullmatch(r"\d{6}", str(body.get("code", ""))):
            errors["code"] = ["Este valor no coincide con el patrón requerido."]
        if len(body.get("new_password") or "") < 8:
            errors["new_password"] = ["Asegúrese de que este campo tenga al menos 8 caracteres."]
        if errors:
            return Respuesta(400, errors)
        user = self.by_email(body["email"])
        entry = self.reset_codes.get(user["email"]) if user else None
        invalid = Respuesta(400, {"detail": "El código no es válido o ha expirado."})
        if not entry or entry["expires"] <= time.time() or entry["attempts"] >= 5:
            return invalid
        if entry["code"] != body["code"]:
            entry["attempts"] += 1
            return invalid
        problems = self._password_problems(body["new_password"], (user["email"],))
        if problems:
            return Respuesta(400, {"new_password": problems})
        user["password"] = body["new_password"]
        del self.reset_codes[user["email"]]
        for token, uid in list(self.refresh.items()):  # anula las sesiones abiertas
            if uid == user["id"]:
                self.refresh.pop(token)
                self.blacklist.add(token)
        return Respuesta(200, {"detail": "La contraseña se restableció correctamente."})

    # ---------------- Cédula y mensajes de verificación ----------------
    def _pro_or_403(self, user, message):
        if user["role"] != "PROFESSIONAL" or not user["professional"]:
            return None, Respuesta(403, {"detail": message})
        return user["professional"], None

    def _documents_data(self, pro):
        return {"professional_profile_id": pro["id"], "verification_status": pro["verification_status"],
                "documents": {"front_uploaded": bool(pro.get("id_front")), "back_uploaded": bool(pro.get("id_back"))}}

    def _documents(self, user, _):
        pro, error = self._pro_or_403(user, "Solo los profesionales pueden cargar documentos de verificación.")
        return error or Respuesta(200, self._documents_data(pro))

    def _upload_documents(self, user, _):
        pro, error = self._pro_or_403(user, "Solo los profesionales pueden cargar documentos de verificación.")
        if error:
            return error
        files = self._files or {}
        if not files:
            return Respuesta(400, {"non_field_errors": ["Envía al menos uno de los archivos id_card_front o id_card_back."]})
        for field, (name, data, _type) in files.items():
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext == "pdf":
                if len(data) > 10 * 1024 * 1024:
                    return Respuesta(400, {field: ["El PDF no puede superar 10 MB."]})
                if b"%PDF-" not in data[:1024] or b"%%EOF" not in data[-2048:]:
                    return Respuesta(400, {field: ["El archivo no es un PDF válido."]})
                continue
            if len(data) > 5 * 1024 * 1024:
                return Respuesta(400, {field: ["La imagen no puede superar 5 MB."]})
            png, jpg = data.startswith(b"\x89PNG"), data.startswith(b"\xff\xd8\xff")
            if not (png and ext == "png") and not (jpg and ext in ("jpg", "jpeg")):
                return Respuesta(400, {field: ["El archivo debe ser una imagen JPEG o PNG válida."]})
        for field in files:
            pro["id_front" if field == "id_card_front" else "id_back"] = files[field][0]
        pro["verification_status"] = "PENDING"
        return Respuesta(200, self._documents_data(pro))

    def _messages(self, user, _):
        pro, error = self._pro_or_403(user, "Solo los profesionales pueden gestionar su verificación.")
        return error or Respuesta(200, sorted(pro.setdefault("messages", []), key=lambda m: m["id"], reverse=True))

    def _send_message(self, user, body):
        pro, error = self._pro_or_403(user, "Solo los profesionales pueden gestionar su verificación.")
        if error:
            return error
        if not (body.get("message") or "").strip():
            return Respuesta(400, {"message": ["Este campo no puede estar en blanco."]})
        item = {"id": next(self.msg_ids), "professional": pro["id"], "message": body["message"], "admin_response": "",
                "resolved_at": None, "created_at": datetime.now(timezone.utc).isoformat()}
        pro.setdefault("messages", []).append(item)
        return Respuesta(201, item)

    # ---------------- Suscripción y pagos (apps/payments) ----------------
    def active_subscription(self, pro):
        return bool(pro.get("subscription_expires_at") and pro["subscription_expires_at"] > datetime.now(timezone.utc))

    def _payment_data(self, payment):
        return {k: payment[k] for k in ("id", "visit_id", "professional_profile_id", "amount", "buy_order",
                                         "status", "created_at", "updated_at")}

    def _start_payment(self, payer, amount, visit_id=None, professional_id=None):
        pid = next(self.payment_ids)
        token = f"tbk-{pid:04d}"
        now = datetime.now(timezone.utc).isoformat()
        self.payments[pid] = {"id": pid, "visit_id": visit_id, "professional_profile_id": professional_id,
                              "amount": str(amount), "buy_order": f"ov-{pid:023d}", "status": "PENDING",
                              "created_at": now, "updated_at": now, "token": token, "payer": payer}
        return Respuesta(201, {**self._payment_data(self.payments[pid]),
                               "url": "https://webpay3gint.transbank.cl/webpayserver/initTransaction",
                               "token": token, "environment": "sandbox"})

    def _subscription(self, user, _):
        if user["role"] != "PROFESSIONAL":
            return Respuesta(403, {"detail": "Solo los profesionales pueden consultar su suscripción."})
        pro = user["professional"]
        expires = pro.get("subscription_expires_at")
        status = "ACTIVE" if self.active_subscription(pro) else "EXPIRED" if expires else "INACTIVE"
        latest = next((p for p in sorted(self.payments.values(), key=lambda p: p["id"], reverse=True)
                       if p["professional_profile_id"] == pro["id"]), None)
        return Respuesta(200, {
            "professional_profile_id": pro["id"], "status": status, "amount": str(self.plan_amount),
            "plan": {"code": "professional-monthly", "name": "Suscripción profesional mensual", "duration_months": 1},
            "expires_at": expires.isoformat() if expires else None,
            "latest_payment": self._payment_data(latest) if latest else None,
        })

    def _start_subscription(self, user, _):
        if user["role"] != "PROFESSIONAL":
            return Respuesta(403, {"detail": "Solo un profesional puede contratar esta suscripción."})
        pro = user["professional"]
        if any(p["professional_profile_id"] == pro["id"] and p["status"] == "PENDING" for p in self.payments.values()):
            return Respuesta(409, {"detail": "Ya existe un pago de suscripción pendiente."})
        return self._start_payment(user["id"], self.plan_amount, professional_id=pro["id"])

    def _visit_payment(self, user, vid):
        payment = next((p for p in sorted(self.payments.values(), key=lambda p: p["id"], reverse=True)
                        if p["visit_id"] == vid and p["payer"] == user["id"]), None)
        if not payment:
            return Respuesta(404, {"detail": "No existe un pago para esta solicitud."})
        return Respuesta(200, self._payment_data(payment))

    def _start_visit_payment(self, user, vid):
        visit = self.visits.get(vid)
        if not visit or visit["client"] != user["id"]:
            return Respuesta(404, {"detail": "No se encontró la solicitud de visita."})
        if visit["status"] != "ACCEPTED":
            return Respuesta(409, {"detail": "Solo puedes pagar una solicitud aceptada por el profesional."})
        fee = self._pro_user(visit["professional"])["professional"]["visit_fee"]
        if not fee or int(float(fee)) <= 0:
            return Respuesta(409, {"detail": "El profesional no tiene una tarifa de visita válida."})
        mine = [p for p in self.payments.values() if p["visit_id"] == vid]
        if any(p["status"] == "AUTHORIZED" for p in mine):
            return Respuesta(409, {"detail": "Esta solicitud ya tiene un pago autorizado."})
        if any(p["status"] == "PENDING" for p in mine):
            return Respuesta(409, {"detail": "Ya existe un pago pendiente para esta solicitud."})
        return self._start_payment(user["id"], int(float(fee)), visit_id=vid)

    def webpay_return(self, token, outcome="authorized"):
        """Simula que Transbank vuelve al backend: confirma y devuelve los parámetros con que
        el backend redirige al front (PAYMENT_RESULT_URL)."""
        payment = next(p for p in self.payments.values() if p["token"] == token)
        if outcome == "cancelled":
            payment["status"] = "REJECTED"
        elif payment["status"] == "PENDING":
            payment["status"] = "AUTHORIZED" if outcome == "authorized" else "REJECTED"
            if payment["status"] == "AUTHORIZED" and payment["professional_profile_id"]:
                pro = next(u["professional"] for u in self.users.values()
                           if u["professional"] and u["professional"]["id"] == payment["professional_profile_id"])
                start = max(pro.get("subscription_expires_at") or datetime.now(timezone.utc), datetime.now(timezone.utc))
                pro["subscription_expires_at"] = start + timedelta(days=30)
        params = {"status": payment["status"].lower() if outcome != "cancelled" else "cancelled"}
        if payment["visit_id"]:
            params["visit_id"] = str(payment["visit_id"])
        if payment["professional_profile_id"]:
            params["professional_profile_id"] = str(payment["professional_profile_id"])
        return params

    # ---------------- Asistente (apps/assistant) ----------------
    def _assistant(self, user, body):
        message = (body.get("message") or "").strip()
        if not message:
            return Respuesta(400, {"message": ["Este campo no puede estar en blanco."]})
        if len(message) > 1500:
            return Respuesta(400, {"message": ["Asegúrese de que este campo no tenga más de 1500 caracteres."]})
        used = self.assistant_use.setdefault(user["id"], 0)
        if used >= 5:  # throttle de DRF: 5 por hora
            return Respuesta(429, {"detail": "Solicitud fue regulada (throttled). Se espera que esté disponible en 3540 segundos."})
        self.assistant_use[user["id"]] = used + 1
        if self.assistant_down:
            return Respuesta(503, {"detail": "El asistente no está disponible en este momento. Inténtalo más tarde."})
        self.assistant_messages.append(message)
        return Respuesta(200, {"reply": f"Para «{message[:40]}» te recomiendo contactar a un profesional de Overol."})

    # ---------------- Valoraciones y reclamos (apps/visits) ----------------
    def _rate(self, user, body):
        errors = {}
        for field in ("visit", "quality", "punctuality", "treatment"):
            if body.get(field) in (None, ""):
                errors[field] = ["Este campo es requerido."]
        for field in ("quality", "punctuality", "treatment"):
            if field not in errors and not 1 <= int(body[field]) <= 5:
                errors[field] = ["Asegúrese de que este valor es menor o igual a 5." if int(body[field]) > 5
                                 else "Asegúrese de que este valor es mayor o igual a 1."]
        visit = self.visits.get(body.get("visit"))
        if "visit" not in errors and not visit:
            errors["visit"] = [f'Clave primaria "{body.get("visit")}" inválida - objeto no existe.']
        elif visit and visit["status"] != "COMPLETED":
            errors["visit"] = ["El servicio debe estar completado."]
        if errors:
            return Respuesta(400, errors)
        pro_user = self._pro_user(visit["professional"])
        if user["id"] not in (visit["client"], pro_user["id"]):
            return Respuesta(400, {"visit": ["No puedes calificar este servicio."]})
        if any(r["visit"] == visit["id"] and r["author"] == user["id"] for r in self.ratings):
            return Respuesta(400, {"visit": ["Este servicio ya fue calificado por este usuario."]})
        target = pro_user["id"] if user["id"] == visit["client"] else visit["client"]
        rating = {"id": len(self.ratings) + 1, "visit": visit["id"], "author": user["id"], "target": target,
                  "quality": int(body["quality"]), "punctuality": int(body["punctuality"]),
                  "treatment": int(body["treatment"]), "comment": body.get("comment", ""),
                  "created_at": datetime.now(timezone.utc).isoformat()}
        self.ratings.append(rating)
        if target == pro_user["id"]:
            mine = [r for r in self.ratings if r["target"] == target]
            pro_user["professional"]["rating_avg"] = sum(
                (r["quality"] + r["punctuality"] + r["treatment"]) / 3 for r in mine) / len(mine)
            if rating["comment"]:
                pro_user["professional"]["opinions"].insert(0, {
                    "quality": rating["quality"], "punctuality": rating["punctuality"], "treatment": rating["treatment"],
                    "comment": rating["comment"], "created_at": rating["created_at"],
                    "author_name": f"{user['first_name']} {user['last_name'][:1]}."})
        return Respuesta(201, {k: rating[k] for k in ("id", "visit", "quality", "punctuality", "treatment", "comment", "created_at")})

    def _claim_data(self, claim):
        return {k: claim[k] for k in ("id", "visit", "description", "professional_response", "admin_resolution",
                                       "status", "created_at", "resolved_at")}

    def _list_claims(self, user, _):
        if user["role"] == "ADMIN":
            mine = list(self.claims.values())
        else:
            pid = user["professional"]["id"] if user["professional"] else None
            mine = [c for c in self.claims.values()
                    if c["client"] == user["id"] or self.visits[c["visit"]]["professional"] == pid]
        return Respuesta(200, [self._claim_data(c) for c in mine])

    def _create_claim(self, user, body):
        visit = self.visits.get(body.get("visit"))
        if not (body.get("description") or "").strip():
            return Respuesta(400, {"description": ["Este campo no puede estar en blanco."]})
        if not visit:
            return Respuesta(400, {"visit": [f'Clave primaria "{body.get("visit")}" inválida - objeto no existe.']})
        if any(c["visit"] == visit["id"] for c in self.claims.values()):
            return Respuesta(400, {"visit": ["Ya existe after sales claim con este visit."]})
        if visit["status"] != "COMPLETED":
            return Respuesta(400, {"visit": ["Solo se puede reclamar un servicio completado."]})
        if visit["client"] != user["id"]:
            return Respuesta(400, {"visit": ["Solo el cliente del servicio puede reclamarlo."]})
        cid = len(self.claims) + 1
        self.claims[cid] = {"id": cid, "visit": visit["id"], "client": user["id"], "description": body["description"],
                            "professional_response": "", "admin_resolution": "", "status": "OPEN",
                            "created_at": datetime.now(timezone.utc).isoformat(), "resolved_at": None}
        return Respuesta(201, self._claim_data(self.claims[cid]))

    def _claim_action(self, user, cid, action, body):
        claim = self.claims.get(cid)
        if not claim:
            return Respuesta(404, {"detail": "No encontrado."})
        pro_user = self._pro_user(self.visits[claim["visit"]]["professional"])
        if action == "respond":
            if user["id"] != pro_user["id"] or claim["status"] != "OPEN":
                return Respuesta(403, {"detail": "No puedes responder este reclamo."})
            if not (body.get("response") or "").strip():
                return Respuesta(400, {"detail": "La respuesta es obligatoria."})
            claim.update(professional_response=body["response"].strip(), status="PROFESSIONAL_RESPONDED")
            self.notifications_add(claim["client"], "Respuesta de posventa", body["response"].strip())
        elif action == "escalate":
            if user["id"] not in (claim["client"], pro_user["id"]):
                return Respuesta(403, {"detail": "No puedes escalar este reclamo."})
            claim["status"] = "ESCALATED"
        elif action == "resolve":
            if user["role"] != "ADMIN":
                return Respuesta(403, {"detail": "Solo un administrador puede resolver reclamos."})
            if not (body.get("resolution") or "").strip():
                return Respuesta(400, {"detail": "La resolución es obligatoria."})
            claim.update(admin_resolution=body["resolution"].strip(), status="RESOLVED",
                         resolved_at=datetime.now(timezone.utc).isoformat())
            self.audit_log.append(("resolve_claim", user["id"], cid))
        else:
            return Respuesta(400, {"detail": "Acción no soportada."})
        return Respuesta(200, self._claim_data(claim))

    def notifications_add(self, user_id, title, message, visit=None):
        self.notifications.append({"id": len(self.notifications) + 1, "recipient": user_id, "title": title,
                                   "message": message, "related_visit": visit, "is_read": False,
                                   "created_at": datetime.now(timezone.utc).isoformat()})

    # ---------------- Catálogo ----------------
    def _categories(self, *_):
        return Respuesta(200, [{"id": cid, "name": name, "keywords": KEYWORDS.get(cid, ""), "home_zones": []}
                               for cid, (name, _) in CATEGORIES.items()])

    def _specialties(self, _, query):
        cid = query.get("category_id")
        return Respuesta(200, [{"id": sid, "name": name, "category_id": c}
                               for sid, (name, c) in self.specialties.items() if not cid or str(c) == cid])

    def _serialize(self, user, detail=False):
        pro = user["professional"]
        trades = [{
            "id": t["id"], "category_id": t["category_id"], "category": CATEGORIES[t["category_id"]][0],
            "years_experience": t["years_experience"], "description": "",
            "specialties": [{"id": sid, "name": name} for sid, (name, c) in self.specialties.items()
                            if c == t["category_id"] and name in t["specialties"]],
        } for t in pro["trades"]]
        data = {
            "id": pro["id"], "name": f"{user['first_name']} {user['last_name']}",
            "first_name": user["first_name"], "last_name": user["last_name"],
            "specialties": [s["name"] for t in trades for s in t["specialties"]],
            "categories": [t["category"] for t in trades], "visit_fee": f"{pro['visit_fee']}",
            "rating_avg": f"{pro['rating_avg']:.2f}", "verification_status": pro["verification_status"],
            "trades": trades, "profile_photo": None, "commune": None, "bio": pro["bio"],
            "coverage": pro["coverage_communes"], "work_days": pro["work_days"],
            "work_start": pro["work_start"], "work_end": pro["work_end"], "rut": None, "address": None,
        }
        if detail:
            data["opinions"] = pro["opinions"]
        return data

    def _approved(self):
        return [u for u in self.users.values()
                if u["professional"] and u["professional"]["verification_status"] == "APPROVED"
                and u["account_status"] == "ACTIVE" and self.active_subscription(u["professional"])]

    def _search(self, _, query):
        result = []
        for user in self._approved():
            pro = user["professional"]
            cats = {t["category_id"] for t in pro["trades"]}
            specs = {s for t in pro["trades"] for s in t["specialties"]}
            if "category_id" in query and int(query["category_id"]) not in cats:
                continue
            if "specialty_id" in query and self.specialties.get(int(query["specialty_id"]), ("",))[0] not in specs:
                continue
            if "commune" in query and query["commune"] not in pro["coverage_communes"]:
                continue
            result.append(self._serialize(user))
        size = min(int(query.get("page_size", 20)), self.page_size_max)
        page = int(query.get("page", 1))
        more = page * size < len(result)
        return Respuesta(200, {"count": len(result), "next": f"?page={page + 1}" if more else None,
                               "previous": None, "results": result[(page - 1) * size: page * size]})

    def _detail(self, pid):
        user = next((u for u in self._approved() if u["professional"]["id"] == pid and u["account_status"] == "ACTIVE"), None)
        if not user:
            return Respuesta(404, {"detail": "No encontrado."})
        return Respuesta(200, self._serialize(user, detail=True))


backend = BackendSimulado()


def instalar():
    """Conecta la imitación: desde aquí, ninguna petición de la app sale a la red."""
    import requests

    requests.request = backend.request
    return backend
