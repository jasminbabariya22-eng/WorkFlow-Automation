import os
import datetime
import ipaddress
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def generate_self_signed_cert(output_dir: str = "certs", valid_days: int = 730):
    os.makedirs(output_dir, exist_ok=True)
    key_path = os.path.join(output_dir, "privkey.pem")
    cert_path = os.path.join(output_dir, "fullchain.pem")

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
        x509.NameAttribute(NameOID.COMMON_NAME, "192.168.1.191"),
    ])

    san_list = [
        x509.DNSName("localhost"),
        x509.DNSName("*.localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        x509.IPAddress(ipaddress.IPv4Address("192.168.1.191")),
        x509.IPAddress(ipaddress.IPv4Address("192.168.1.247")),
        x509.IPAddress(ipaddress.IPv4Address("192.168.1.161")),
    ]

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
    print(f"      - Private Key: {key_path}")
    print(f"      - Certificate: {cert_path}")
    return key_path, cert_path

if __name__ == "__main__":
    generate_self_signed_cert()
