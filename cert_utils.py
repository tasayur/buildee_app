# cert_utils.py -- Self-signed TLS certificate generator for BuildeeMgr
# Uses cryptography library (pure Python, no openssl binary needed)
import os
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import ipaddress

CERT_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certs')
CERT_FILE = os.path.join(CERT_DIR, 'buildee.crt')
KEY_FILE  = os.path.join(CERT_DIR, 'buildee.key')
DAYS_VALID = 3650   # 10 years for dev/self-signed

def certs_exist():
    return os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE)

def generate_self_signed():
    """Generate a 2048-bit RSA self-signed certificate and save to certs/."""
    os.makedirs(CERT_DIR, exist_ok=True)

    # --- Private key ---
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # --- Subject / Issuer ---
    name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,             "JP"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME,   "Tokyo"),
        x509.NameAttribute(NameOID.LOCALITY_NAME,            "Shinjuku"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME,        "BuildeeMgr"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Construction"),
        x509.NameAttribute(NameOID.COMMON_NAME,              "localhost"),
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=DAYS_VALID))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("*.localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv6Address("::1")),
            ]),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )

    # --- Write key (PEM, no passphrase) ---
    with open(KEY_FILE, 'wb') as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    os.chmod(KEY_FILE, 0o600)   # owner read-only

    # --- Write certificate (PEM) ---
    with open(CERT_FILE, 'wb') as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"[TLS] Self-signed certificate generated ({DAYS_VALID}d):")
    print(f"      CRT  -> {CERT_FILE}")
    print(f"      KEY  -> {KEY_FILE}")
    return CERT_FILE, KEY_FILE


def get_or_create_certs(custom_cert=None, custom_key=None):
    """
    Returns (cert_path, key_path).
    Priority: 1) custom paths  2) existing certs/  3) auto-generate
    """
    if custom_cert and custom_key:
        if not os.path.exists(custom_cert):
            raise FileNotFoundError(f"CERT_FILE not found: {custom_cert}")
        if not os.path.exists(custom_key):
            raise FileNotFoundError(f"KEY_FILE not found: {custom_key}")
        print(f"[TLS] Using custom certificate: {custom_cert}")
        return custom_cert, custom_key

    if certs_exist():
        print(f"[TLS] Using existing certificate: {CERT_FILE}")
        return CERT_FILE, KEY_FILE

    print("[TLS] No certificate found. Generating self-signed...")
    return generate_self_signed()


def get_cert_info():
    """Return dict with cert expiry and CN (for admin display)."""
    if not certs_exist():
        return {'exists': False}
    try:
        from cryptography import x509 as _x509
        with open(CERT_FILE, 'rb') as f:
            cert = _x509.load_pem_x509_certificate(f.read())
        return {
            'exists':     True,
            'cn':         cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
            'not_after':  cert.not_valid_after_utc.strftime('%Y-%m-%d'),
            'serial':     str(cert.serial_number)[:12],
            'cert_file':  CERT_FILE,
            'key_file':   KEY_FILE,
        }
    except Exception as e:
        return {'exists': True, 'error': str(e)}
