"""Documentos de verificación cifrados (Fernet): migración de los antiguos sin borrar
originales, clave generada si falta, solo el admin descifra y cada vista queda registrada."""

import io
import os
from pathlib import Path

from comun import check, new_app as _new_app, preparar, terminar, usuarios

front = preparar()

# Clave de prueba en un archivo que aún no existe: se prueba que la app la genere
KEY_FILE = Path(front).parent / "clave_prueba_documentos.key"
KEY_FILE.unlink(missing_ok=True)
os.environ["OVEROL_CLAVE_DOCUMENTOS_ARCHIVO"] = str(KEY_FILE)

import streamlit  # noqa: E402
from PIL import Image  # noqa: E402

U = usuarios(front)  # crea la base si no existe (sin documentos: no se genera clave)
ADMIN, CLIENT, PRO_USER = U["admin"], U["cliente"], U["carlos"]

from core import database as db  # noqa: E402


def new_app(user_id):
    return _new_app(front, user_id)


UPLOADS = Path(front) / "documentos_verificacion"
UPLOADS.mkdir(exist_ok=True)
check(not KEY_FILE.exists(), "sin documentos que cifrar no se genera ninguna clave")

_buf = io.BytesIO()
Image.new("RGB", (40, 24), (245, 158, 11)).save(_buf, format="PNG")
PNG = _buf.getvalue()  # imagen válida
BROKEN = b"\x89PNG\r\n\x1a\n" + b"no-es-una-imagen" * 10  # firma válida, contenido dañado

# ---------- Documentos antiguos sin cifrar (como los dejaba la versión anterior) ----------
raw = db.get_connection()
pid = db.get_professional_by_user(PRO_USER)["id"]
(UPLOADS / "antiguo_1.png").write_bytes(PNG)
cur = raw.execute(
    "INSERT INTO verification_documents (professional_id, document_type, original_name, stored_name, uploaded_at) "
    "VALUES (?, 'Documento de identidad', 'cedula.png', 'antiguo_1.png', '2026-10-01 10:00:00')", (pid,))
legacy_id = cur.lastrowid
(UPLOADS / "antiguo_2.png").write_bytes(BROKEN)
cur = raw.execute(
    "INSERT INTO verification_documents (professional_id, document_type, original_name, stored_name, uploaded_at) "
    "VALUES (?, 'Otro respaldo', 'danada.png', 'antiguo_2.png', '2026-10-01 11:00:00')", (pid,))
broken_id = cur.lastrowid
raw.execute("UPDATE professionals SET verified = 0, verification_status = 'Pendiente' WHERE id = ?", (pid,))
raw.commit()
raw.close()

streamlit.cache_resource.clear()  # simula reiniciar Streamlit: init_db vuelve a correr
at = new_app(ADMIN)  # arranque: migración
from cryptography.fernet import Fernet  # noqa: E402

check(not at.exception, "arranca sin excepción tras migrar")
check(KEY_FILE.exists() and Fernet(KEY_FILE.read_bytes().strip()), "sin OVEROL_CLAVE_DOCUMENTOS se genera la clave en el archivo indicado")
doc = next(d for d in db.get_verification_documents(pid) if d["id"] == legacy_id)
enc_path = UPLOADS / doc["stored_name"]
check(doc["encrypted"] == 1 and doc["stored_name"] == "antiguo_1.png.enc" and enc_path.exists(),
      "migración: el documento antiguo queda cifrado como «.enc»")
check(enc_path.read_bytes() != PNG and Fernet(KEY_FILE.read_bytes().strip()).decrypt(enc_path.read_bytes()) == PNG,
      "migración: el archivo cifrado no es legible y se descifra al original con la clave")
check((UPLOADS / "antiguo_1.png").exists(), "migración: el original sin cifrar NO se borra")
check(db.legacy_plain_documents() == ["antiguo_1.png", "antiguo_2.png"], "migración: se informan los originales que quedan sin cifrar")
log, _ = db.get_audit_log(action="DOC_ENCRYPT")
check({r["entity_id"] for r in log} >= {legacy_id, broken_id} and all(r["user_id"] is None for r in log),
      "migración: cada documento cifrado queda en la bitácora")
conn = db.get_connection()
db.encrypt_legacy_documents(conn)
conn.commit()
conn.close()
check(not (UPLOADS / "antiguo_1.png.enc.enc").exists(), "la migración no vuelve a cifrar lo ya cifrado")

# ---------- El admin abre el documento: se descifra y queda registrado ----------
at = new_app(ADMIN)
at.button(key="admin_navigation_btn_1").click().run()
check(any("2 archivo(s) antiguo(s) sin cifrar" in w.value for w in at.warning), "[admin] aviso de originales sin cifrar")
check(any(b.key == f"view_doc_{legacy_id}" for b in at.button) and not at.get("download_button"),
      "[admin] el documento aparece cerrado (sin descifrar) con «🔓 Ver documento»")
views_before = db.get_audit_log(action="DOC_VIEW")[1]
at.button(key=f"view_doc_{legacy_id}").click().run()
log, views_after = db.get_audit_log(action="DOC_VIEW", limit=1)
check(not at.exception and at.get("image") and at.get("download_button"), "[admin] al abrirlo ve la imagen y puede descargarla")
check(views_after == views_before + 1 and log[0]["user_id"] == ADMIN and log[0]["entity_id"] == legacy_id
      and "cedula.png" in log[0]["details"], "[admin] la bitácora registra qué admin vio qué documento")
at.button(key="admin_navigation_btn_1").click().run()
check(db.get_audit_log(action="DOC_VIEW")[1] == views_after, "[admin] redibujar no duplica el registro")
at.button(key=f"hide_doc_{legacy_id}").click().run()
check(any(b.key == f"view_doc_{legacy_id}" for b in at.button) and not at.get("download_button"), "[admin] «Ocultar» lo vuelve a cerrar")

at.button(key=f"view_doc_{broken_id}").click().run()
check(not at.exception and any("No se puede mostrar la vista previa" in c.value for c in at.caption)
      and at.get("download_button"), "[admin] una imagen dañada no bota la pantalla: aviso y descarga")
views_after = db.get_audit_log(action="DOC_VIEW")[1]

# ---------- Nadie más puede descifrar ----------
for uid, who in ((PRO_USER, "el profesional dueño"), (CLIENT, "un cliente")):
    data, err = db.read_verification_document(legacy_id, uid, log=True)
    check(data is None and "administración" in err, f"{who} no puede descifrar el documento")
check(db.get_audit_log(action="DOC_VIEW")[1] == views_after, "los intentos rechazados no se registran como vistas")

# ---------- Subida nueva desde la pantalla del profesional: se guarda cifrada ----------
class FakeUpload:
    name = "cedula_reverso.png"

    def getvalue(self):
        return PNG


real_uploader = streamlit.file_uploader
streamlit.file_uploader = lambda *a, **k: FakeUpload()
try:
    at = new_app(PRO_USER)
    at.button(key="professional_navigation_btn_2").click().run()
    check(any("se guardan cifrados" in i.value for i in at.info), "[profesional] se le informa que los documentos van cifrados")
    before = {d["id"] for d in db.get_verification_documents(pid)}
    at.button(key="send_document").click().run()
finally:
    streamlit.file_uploader = real_uploader
new = [d for d in db.get_verification_documents(pid) if d["id"] not in before]
check(not at.exception and len(new) == 1, "[profesional] la subida crea el registro")
if new:
    path = UPLOADS / new[0]["stored_name"]
    check(new[0]["encrypted"] == 1 and path.suffix == ".enc" and path.read_bytes() != PNG,
          "[profesional] el archivo nuevo se guarda cifrado («.enc»)")
    check(not any(p.name.startswith(f"{PRO_USER}_") and p.suffix == ".png" for p in UPLOADS.iterdir()),
          "[profesional] no queda copia sin cifrar de la subida")
    data, err = db.read_verification_document(new[0]["id"], ADMIN)
    check(data == PNG, "[admin] la subida nueva se descifra al contenido original")

# ---------- Archivo alterado o clave distinta: error claro ----------
enc_path.write_bytes(Fernet(Fernet.generate_key()).encrypt(PNG))
data, err = db.read_verification_document(legacy_id, ADMIN)
check(data is None and "clave no coincide" in err, "archivo cifrado con otra clave → error claro, sin excepción")

KEY_FILE.unlink(missing_ok=True)
terminar()
