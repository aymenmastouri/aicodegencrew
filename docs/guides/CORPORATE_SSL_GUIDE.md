# Corporate SSL / Certificate Guide

## Problem

In corporate networks,  HTTPS connections are terminated by a
**TLS-Inspection-Proxy** 
and re-signed with an internal CA certificate. Python uses das `certifi`-Bundle, which does not include these
internal CAs — jeder HTTPS-Call (LLM API, ChromaDB, pip, etc.)
resulting in `SSL: CERTIFICATE_VERIFY_FAILED` errors for every HTTPS call (LLM API, Qdrant, pip, etc).

## Solution: `truststore`

The package [`truststore`](https://github.com/sethmlarson/truststore) replaces
Python's certificate store with the OS certificate store:

| OS      | Store Used                        |
|---------|----------------------------------------|
| Windows | Windows Certificate Store (certmgr)    |
| macOS   | Keychain Access / System Roots         |
| Linux   | `/etc/ssl/certs` bzw. distro-spezifisch|

Since the corporate CA is already trusted in the OS store
(e.g. via GPO on Windows), all HTTPS connections work immediately.

## Implementation

### 1. Dependency (`pyproject.toml`)

```toml
# SSL: inject Windows/macOS system certificate store so corporate CAs are trusted
"truststore>=0.9.0",
```

### 2. Early Injection (`src/aicodegencrew/__init__.py`)

```python
# Inject OS/Windows certificate store FIRST — before any HTTP library loads.
# Corporate environments use self-signed CAs that are not in certifi's bundle.
try:
    import truststore as _truststore
    _truststore.inject_into_ssl()
except ImportError:
    pass  # graceful fallback if truststore is not installed
```

**Why at the top of in `__init__.py`?**
`inject_into_ssl()` must be called **before** `urllib3`, `requests`,
`httpx` oder andere HTTP-Libraries ihre SSL-Kontexte initialisieren. Da
`__init__.py` beim ersten `import aicodegencrew` läuft, ist das der früheste
sichere Zeitpunkt.

### 3. Fallback in `llm_factory.py`

```python
# Inject the OS/Windows certificate store BEFORE any HTTP library is imported
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass  # truststore not installed — fall back to certifi bundle
```

This second call is a **safety net** für den Fall, dass
`llm_factory` direkt importiert wird (z.B. in Tests oder Scripts) ohne
vorher das Package-Level `__init__.py` zu durchlaufen.
`inject_into_ssl()` is idempotent — multiple calls are harmless.

## Debugging

### Check if truststore is active

```python
import ssl
ctx = ssl.create_default_context()
print(ctx.get_ca_certs())  # Should contain corporate CA
```

### Common Errors

| Symptom | Cause | Fix |
|---------|---------|-----|
| `CERTIFICATE_VERIFY_FAILED` | truststore nicht installiert oder nicht injiziert | `pip install truststore` + prüfe Import-Reihenfolge |
| Fehler nur in Tests | Test importiert `llm_factory` direkt | Fallback in `llm_factory.py` greift — sollte funktionieren |
| Fehler nur auf Linux CI | Corporate-CA nicht im System-Store | CA-Cert in `/usr/local/share/ca-certificates/` ablegen + `update-ca-certificates` |

## Alternative: `SSL_CERT_FILE` (not recommended)

You could also manually export a bundle:

```bash
export SSL_CERT_FILE=/path/to/corporate-bundle.pem
```

This is fragile (path must match on every machine, bundle must be kept up to date).
gehalten werden). `truststore` is the cleaner solution.
