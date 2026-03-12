# Corporate SSL / Certificate Guide

## Problem

In Corporate-Netzwerken (z.B. Capgemini) werden HTTPS-Verbindungen durch einen
**TLS-Inspection-Proxy** terminiert und mit einem internen CA-Zertifikat
neu signiert. Python nutzt standardmäßig das `certifi`-Bundle, das diese
internen CAs **nicht** enthält — jeder HTTPS-Call (LLM API, ChromaDB, pip, etc.)
schlägt dann mit `SSL: CERTIFICATE_VERIFY_FAILED` fehl.

## Lösung: `truststore`

Das Package [`truststore`](https://github.com/sethmlarson/truststore) ersetzt
Pythons eigenen Zertifikatspeicher durch den des Betriebssystems:

| OS      | Genutzter Store                        |
|---------|----------------------------------------|
| Windows | Windows Certificate Store (certmgr)    |
| macOS   | Keychain Access / System Roots         |
| Linux   | `/etc/ssl/certs` bzw. distro-spezifisch|

Da die Corporate-CA im OS-Store bereits als vertrauenswürdig hinterlegt ist
(z.B. per GPO auf Windows), funktionieren alle HTTPS-Verbindungen sofort.

## Implementierung

### 1. Dependency (`pyproject.toml`)

```toml
# SSL: inject Windows/macOS system certificate store so corporate CAs are trusted
"truststore>=0.9.0",
```

### 2. Frühe Injektion (`src/aicodegencrew/__init__.py`)

```python
# Inject OS/Windows certificate store FIRST — before any HTTP library loads.
# Corporate environments use self-signed CAs that are not in certifi's bundle.
try:
    import truststore as _truststore
    _truststore.inject_into_ssl()
except ImportError:
    pass  # graceful fallback if truststore is not installed
```

**Warum ganz oben in `__init__.py`?**
`inject_into_ssl()` muss aufgerufen werden **bevor** `urllib3`, `requests`,
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

Dieser zweite Aufruf ist ein **Sicherheitsnetz** für den Fall, dass
`llm_factory` direkt importiert wird (z.B. in Tests oder Scripts) ohne
vorher das Package-Level `__init__.py` zu durchlaufen.
`inject_into_ssl()` ist idempotent — mehrfaches Aufrufen ist harmlos.

## Debugging

### Prüfen ob truststore aktiv ist

```python
import ssl
ctx = ssl.create_default_context()
print(ctx.get_ca_certs())  # Sollte Corporate-CA enthalten
```

### Häufige Fehler

| Symptom | Ursache | Fix |
|---------|---------|-----|
| `CERTIFICATE_VERIFY_FAILED` | truststore nicht installiert oder nicht injiziert | `pip install truststore` + prüfe Import-Reihenfolge |
| Fehler nur in Tests | Test importiert `llm_factory` direkt | Fallback in `llm_factory.py` greift — sollte funktionieren |
| Fehler nur auf Linux CI | Corporate-CA nicht im System-Store | CA-Cert in `/usr/local/share/ca-certificates/` ablegen + `update-ca-certificates` |

## Alternative: `SSL_CERT_FILE` (nicht empfohlen)

Man könnte auch manuell ein Bundle exportieren:

```bash
export SSL_CERT_FILE=/path/to/corporate-bundle.pem
```

Das ist **fragil** (Pfad muss auf jedem Rechner stimmen, Bundle muss aktuell
gehalten werden). `truststore` ist die sauberere Lösung.
