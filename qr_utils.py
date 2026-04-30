# qr_utils.py -- QR code generation for BuildeeMgr workers
import io, base64, secrets
import qrcode
from qrcode.image.pil import PilImage
import database as db

QR_PREFIX = "BUILDEE_WORKER:"   # payload prefix for validation

def generate_token():
    """32-char hex token (collision-safe)"""
    return secrets.token_hex(16)

def make_qr_payload(worker_id: str, token: str) -> str:
    return f"{QR_PREFIX}{worker_id}:{token}"

def parse_qr_payload(raw: str):
    """Returns (worker_id, token) or raises ValueError"""
    if not raw.startswith(QR_PREFIX):
        raise ValueError("Not a BuildeeMgr QR code")
    rest = raw[len(QR_PREFIX):]
    parts = rest.split(":", 1)
    if len(parts) != 2:
        raise ValueError("Malformed payload")
    return parts[0], parts[1]

def qr_to_base64(data: str, box_size=8, border=3) -> str:
    """Generate QR and return data-URI (PNG base64)"""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a1a2e", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"

def ensure_worker_qr(worker_id: str) -> dict:
    """
    Make sure the worker has a QR token. Generate one if missing.
    Returns {'token': ..., 'payload': ..., 'qr_b64': ...}
    """
    worker = db.get_worker_by_id(worker_id)
    if not worker:
        raise ValueError(f"Worker {worker_id} not found")

    token = worker.get("qr_token")
    if not token:
        token = generate_token()
        db.set_qr_token(worker_id, token)

    payload = make_qr_payload(worker_id, token)
    qr_b64  = qr_to_base64(payload)
    return {
        "worker_id": worker_id,
        "worker_name": worker["name"],
        "company": worker["company"],
        "token":   token,
        "payload": payload,
        "qr_b64":  qr_b64,
    }

def regenerate_worker_qr(worker_id: str) -> dict:
    """Force-generate a new token (invalidates old QR)"""
    worker = db.get_worker_by_id(worker_id)
    if not worker:
        raise ValueError(f"Worker {worker_id} not found")
    token = generate_token()
    db.set_qr_token(worker_id, token)
    payload = make_qr_payload(worker_id, token)
    return {
        "worker_id":   worker_id,
        "worker_name": worker["name"],
        "company":     worker["company"],
        "token":       token,
        "payload":     payload,
        "qr_b64":      qr_to_base64(payload),
    }
