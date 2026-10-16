import os
import sys
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
    main_url = os.getenv("MAIN_URL")
    if not main_url:
        raise ValueError("MAIN_URL environment variable is required to generate SSL certificates. Silent fallback to 127.0.0.1 is disabled.")
    parsed_host = urlparse(main_url).hostname
    if not parsed_host:
        raise ValueError(f"Could not parse a valid hostname or IP from MAIN_URL: '{main_url}'")

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

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=valid_days))
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

    # Immediately verify generated certificate
    verify_ssl_certificate(output_dir=output_dir, expected_host=parsed_host)
    return key_path, cert_path

def verify_ssl_certificate(output_dir: str = None, expected_host: str = None) -> bool:
    """
    Validates certificate and private key consistency, validity dates, and SAN coverage.
    """
    if not output_dir or output_dir == "certs":
        output_dir = str(Path(__file__).parent / "certs")
    key_path = os.path.join(output_dir, "privkey.pem")
    cert_path = os.path.join(output_dir, "fullchain.pem")

    if not os.path.exists(key_path):
        raise FileNotFoundError(f"SSL Private key not found: {key_path}")
    if not os.path.exists(cert_path):
        raise FileNotFoundError(f"SSL Certificate not found: {cert_path}")

    with open(key_path, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    with open(cert_path, "rb") as f:
        cert = x509.load_pem_x509_certificate(f.read())

    # 1. Key consistency check (public numbers must match)
    if cert.public_key().public_numbers() != key.public_key().public_numbers():
        raise ValueError("SSL Verification Error: Certificate public key does not match private key!")

    # 2. Expiration check
    now = datetime.datetime.now(datetime.timezone.utc)
    if now < cert.not_valid_before_utc or now > cert.not_valid_after_utc:
        raise ValueError(f"SSL Verification Error: Certificate is expired or not yet valid (valid: {cert.not_valid_before_utc} to {cert.not_valid_after_utc})")

    # 3. Subject Alternative Name (SAN) coverage
    if expected_host is None:
        main_url = os.getenv("MAIN_URL", "")
        if main_url:
            expected_host = urlparse(main_url).hostname

    if expected_host:
        san_ext = cert.extensions.get_extension_for_oid(x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        san_names = [str(n.value) for n in san_ext.value]
        if expected_host not in san_names:
            raise ValueError(f"SSL Verification Error: Certificate SANs {san_names} do not cover expected host '{expected_host}'!")
        print(f"[SSL Verification] Certificate covers expected host '{expected_host}'.")

    print("[SSL Verification] Certificate & Key consistency, validity dates, and SANs verified.")
    return True

if __name__ == "__main__":
    if "--verify" in sys.argv:
        try:
            verify_ssl_certificate()
            sys.exit(0)
        except Exception as e:
            print(f"[SSL Error] {e}", file=sys.stderr)
            sys.exit(1)
    else:
        try:
            generate_self_signed_cert()
            sys.exit(0)
        except Exception as e:
            print(f"[SSL Error] {e}", file=sys.stderr)
            sys.exit(1)
