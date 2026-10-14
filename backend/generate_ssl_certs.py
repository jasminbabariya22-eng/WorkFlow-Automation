import os
import datetime
import ipaddress
import socket
from urllib.parse import urlparse
from pathlib import Path

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    # Look for .env in current folder or backend/
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def _get_local_ip() -> str:
    """Auto-detect the machine's primary local LAN IP."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def generate_self_signed_cert(output_dir: str = None, valid_days: int = 730):
    if not output_dir or output_dir == "certs":
        output_dir = str(Path(__file__).parent / "certs")
    os.makedirs(output_dir, exist_ok=True)
    key_path = os.path.join(output_dir, "privkey.pem")
    cert_path = os.path.join(output_dir, "fullchain.pem")

    # Extract target host/IP from MAIN_URL in .env
    main_url = os.getenv("MAIN_URL", "https://127.0.0.1")
    parsed_host = urlparse(main_url).hostname or "127.0.0.1"
    local_lan_ip = _get_local_ip()

    # Collect all unique candidate hosts / IPs
    candidate_hosts = {
        "localhost",
        "*.localhost",
        "127.0.0.1",
        parsed_host,
        local_lan_ip,
    }

    # Also support optional extra comma-separated SANs from .env
    extra_sans = os.getenv("SSL_SAN_HOSTS", "")
    if extra_sans:
        for item in extra_sans.split(","):
            cleaned = item.strip()
            if cleaned:
                candidate_hosts.add(cleaned)

    print(f"[SSL] Resolved Target Common Name from .env: {parsed_host}")
    print(f"[SSL] All Subject Alternative Names (SANs): {sorted(candidate_hosts)}")

    print("[SSL] Generating 2048-bit RSA Private Key...")
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    print("[SSL] Generating X.509 Certificate with SAN...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Maharashtra"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "BPCL Workflow Automation"),
        x509.NameAttribute(NameOID.COMMON_NAME, parsed_host),
    ])

    san_list = []
    for host in candidate_hosts:
        try:
            ip_obj = ipaddress.ip_address(host)
            san_list.append(x509.IPAddress(ip_obj))
        except ValueError:
            san_list.append(x509.DNSName(host))

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=valid_days))
        .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"[SSL] Success! Certificate and Key generated in '{output_dir}':")
    print(f"      - Common Name: {parsed_host}")
    print(f"      - Private Key: {key_path}")
    print(f"      - Certificate: {cert_path}")
    return key_path, cert_path

if __name__ == "__main__":
    generate_self_signed_cert()
