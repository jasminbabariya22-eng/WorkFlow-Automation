"""
Production Environment & Secret Validator for WorkFlow-Automation.
Validates all required production credentials and settings before deployment.
Never prints secret values in output or logs.
"""

import os
import sys
import tempfile
import shutil
from urllib.parse import urlparse
from cryptography.fernet import Fernet

def validate_environment(env_vars: dict = None) -> dict:
    """
    Validates all required environment variables and secrets.
    Returns cleaned, validated dictionary. Raises ValueError on any invalid setting.
    """
    if env_vars is None:
        env_vars = os.environ

    validated = {}
    errors = []

    # 1. WORKFLOW_DATABASE_URL
    db_url = env_vars.get("WORKFLOW_DATABASE_URL", "").strip()
    if not db_url:
        errors.append("WORKFLOW_DATABASE_URL is missing or empty.")
    elif "replace_with_" in db_url:
        errors.append("WORKFLOW_DATABASE_URL contains placeholder value.")
    else:
        try:
            parsed_db = urlparse(db_url)
            if parsed_db.scheme not in ("postgresql", "postgresql+psycopg2"):
                errors.append(f"WORKFLOW_DATABASE_URL must use 'postgresql' or 'postgresql+psycopg2' scheme (found: '{parsed_db.scheme}').")
            if not parsed_db.hostname:
                errors.append("WORKFLOW_DATABASE_URL missing hostname or IP.")
            if not parsed_db.username:
                errors.append("WORKFLOW_DATABASE_URL missing database user.")
            if not parsed_db.path or parsed_db.path == "/":
                errors.append("WORKFLOW_DATABASE_URL missing database name.")
        except Exception as e:
            errors.append(f"WORKFLOW_DATABASE_URL failed URL parsing: {e}")
    validated["WORKFLOW_DATABASE_URL"] = db_url

    # 2. SECRET_KEY (JWT Auth Secret)
    secret_key = env_vars.get("SECRET_KEY", "").strip()
    if not secret_key:
        errors.append("SECRET_KEY is missing or empty.")
    elif len(secret_key) < 32:
        errors.append(f"SECRET_KEY must be at least 32 characters long for cryptographic security (found: {len(secret_key)}).")
    elif "replace_with_" in secret_key:
        errors.append("SECRET_KEY contains placeholder value.")
    validated["SECRET_KEY"] = secret_key

    # 3. FERNET_KEY (Symmetric encryption key)
    fernet_key = env_vars.get("FERNET_KEY", "").strip()
    if not fernet_key:
        errors.append("FERNET_KEY is missing or empty.")
    elif "replace_with_" in fernet_key:
        errors.append("FERNET_KEY contains placeholder value.")
    else:
        try:
            # Validates that it is a 32-byte url-safe base64-encoded key
            Fernet(fernet_key.encode("utf-8"))
        except Exception as e:
            errors.append(f"FERNET_KEY is not a valid 32-byte URL-safe base64 Fernet key: {e}")
    validated["FERNET_KEY"] = fernet_key

    # 4. MAIN_URL (Target host and scheme for CORS & SSL)
    main_url = env_vars.get("MAIN_URL", "").strip()
    if not main_url:
        errors.append("MAIN_URL is missing or empty.")
    elif "replace_with_" in main_url:
        errors.append("MAIN_URL contains placeholder value.")
    else:
        try:
            parsed_url = urlparse(main_url)
            if parsed_url.scheme not in ("http", "https"):
                errors.append(f"MAIN_URL must have http or https scheme (found: '{parsed_url.scheme}').")
            if not parsed_url.hostname:
                errors.append("MAIN_URL has invalid or missing hostname/IP.")
        except Exception as e:
            errors.append(f"MAIN_URL failed URL parsing: {e}")
    validated["MAIN_URL"] = main_url

    # 5. GRAFANA_ADMIN_PASSWORD
    grafana_pass = env_vars.get("GRAFANA_ADMIN_PASSWORD", "").strip()
    if not grafana_pass:
        errors.append("GRAFANA_ADMIN_PASSWORD is missing or empty. A configured password is required.")
    elif len(grafana_pass) < 8:
        errors.append(f"GRAFANA_ADMIN_PASSWORD must be at least 8 characters long (found: {len(grafana_pass)}).")
    elif "replace_with_" in grafana_pass:
        errors.append("GRAFANA_ADMIN_PASSWORD contains placeholder value.")
    validated["GRAFANA_ADMIN_PASSWORD"] = grafana_pass

    # Optional / defaulted variables
    validated["WORKFLOW_DB_SCHEMA"] = env_vars.get("WORKFLOW_DB_SCHEMA", "workflow").strip() or "workflow"
    validated["ALGORITHM"] = env_vars.get("ALGORITHM", "HS256").strip() or "HS256"
    validated["ACCESS_TOKEN_EXPIRE_MINUTES"] = env_vars.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60").strip() or "60"
    validated["GRAFANA_ADMIN_USER"] = env_vars.get("GRAFANA_ADMIN_USER", "admin").strip() or "admin"

    if errors:
        print("ENVIRONMENT VALIDATION FAILED:")
        for err in errors:
            print(f"  - [FAIL] {err}", file=sys.stderr)
        raise ValueError(f"Environment validation failed with {len(errors)} error(s).")

    print("ENVIRONMENT VALIDATION SUCCESS:")
    print("  - [PASS] WORKFLOW_DATABASE_URL: Valid PostgreSQL connection configuration.")
    print("  - [PASS] SECRET_KEY: Valid cryptographic secret length.")
    print("  - [PASS] FERNET_KEY: Valid 32-byte URL-safe Fernet encryption key.")
    print(f"  - [PASS] MAIN_URL: Valid URL with target host '{urlparse(main_url).hostname}'.")
    print("  - [PASS] GRAFANA_ADMIN_PASSWORD: Valid password length provided.")
    return validated


def write_env_file_atomically(validated: dict, target_paths: list[str]) -> None:
    """
    Writes the validated environment variables to target file paths atomically.
    Never overwrites target files unless all values have completely passed validation.
    """
    env_content = (
        f"WORKFLOW_DATABASE_URL={validated['WORKFLOW_DATABASE_URL']}\n"
        f"WORKFLOW_DB_SCHEMA={validated['WORKFLOW_DB_SCHEMA']}\n"
        f"SECRET_KEY={validated['SECRET_KEY']}\n"
        f"ALGORITHM={validated['ALGORITHM']}\n"
        f"ACCESS_TOKEN_EXPIRE_MINUTES={validated['ACCESS_TOKEN_EXPIRE_MINUTES']}\n"
        f"FERNET_KEY={validated['FERNET_KEY']}\n"
        f"MAIN_URL={validated['MAIN_URL']}\n"
        f"GRAFANA_ADMIN_USER={validated['GRAFANA_ADMIN_USER']}\n"
        f"GRAFANA_ADMIN_PASSWORD={validated['GRAFANA_ADMIN_PASSWORD']}\n"
    )

    for target in target_paths:
        target_dir = os.path.dirname(os.path.abspath(target)) or "."
        os.makedirs(target_dir, exist_ok=True)
        # Write to temporary file in the same directory for atomic rename
        with tempfile.NamedTemporaryFile("w", dir=target_dir, delete=False, encoding="ascii") as tmp:
            tmp.write(env_content)
            tmp_path = tmp.name
        shutil.move(tmp_path, target)
        print(f"  - Atomically provisioned: {target}")


if __name__ == "__main__":
    try:
        # Load .env if exists to test existing file
        from dotenv import load_dotenv
        load_dotenv("backend/.env")
        load_dotenv(".env")
    except ImportError:
        pass

    try:
        validated_vars = validate_environment()
        if "--write" in sys.argv:
            targets = [".env", "backend/.env"]
            write_env_file_atomically(validated_vars, targets)
            print("Successfully provisioned production environment files.")
        sys.exit(0)
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
