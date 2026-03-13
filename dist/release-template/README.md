# SDLC Pilot - Dashboard

AI-powered Software Development Lifecycle assistant.

---

## Schritt 1: WSL2 + Ubuntu installieren (einmalig)

> WSL2 ist ein eingebautes Linux in Windows. Keine extra Lizenz noetig.

1. **Windows-Taste** druecken, **"Microsoft Store"** eingeben, oeffnen
2. Im Store nach **"Ubuntu"** suchen
3. **"Ubuntu 22.04 LTS"** (oder neuer) installieren und **"Oeffnen"** klicken
4. Beim ersten Start: **Benutzername** und **Passwort** festlegen (merken!)

> Falls "Ubuntu" nicht im Store erscheint:
> **PowerShell als Administrator** oeffnen und eingeben:
> ```
> wsl --install
> ```
> Danach PC neu starten und Ubuntu aus dem Startmenue oeffnen.

---

## Schritt 2: Docker in Ubuntu installieren (einmalig)

Ubuntu oeffnen (aus dem Startmenue) und diese 4 Zeilen **nacheinander** eingeben:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
```

Danach Ubuntu **schliessen und neu oeffnen** (damit die Rechte aktiv werden).

Docker starten:

```bash
sudo service docker start
```

Pruefen ob Docker laeuft:

```bash
docker info
```

Wenn eine Ausgabe mit "Server Version" erscheint, funktioniert Docker.

---

## Schritt 3: ZIP-Datei nach Ubuntu kopieren

Die ZIP-Datei liegt z.B. unter `C:\Users\IhrName\Downloads\`.
Ubuntu kann auf Windows-Dateien zugreifen ueber `/mnt/c/`.

In Ubuntu eingeben:

```bash
cd ~
cp /mnt/c/Users/IhrName/Downloads/sdlc-pilot-v0.7.4.zip .
unzip sdlc-pilot-v0.7.4.zip
cd sdlc-pilot-v0.7.4
```

> **Wichtig:** Ersetzen Sie `IhrName` durch Ihren Windows-Benutzernamen.
> Den Benutzernamen finden Sie z.B. in `C:\Users\` im Windows Explorer.

---

## Schritt 4: Konfiguration

```bash
cp .env.example .env
nano .env
```

In der Datei diese zwei Zeilen aendern:

```
PROJECT_PATH=/mnt/c/Pfad/zu/Ihrem/Repository
OPENAI_API_KEY=sk-Ihr-echter-API-Key
```

Beispiel:

```
PROJECT_PATH=/mnt/c/projects/mein-projekt
OPENAI_API_KEY=sk-abc123def456
```

Speichern: **Strg+O**, Enter, **Strg+X**

> **PROJECT_PATH** = Pfad zu dem Repository das analysiert werden soll.
> Windows-Pfad `C:\projects\myapp` wird in Ubuntu zu `/mnt/c/projects/myapp`.
>
> **API_BASE** ist bereits voreingestellt und muss nicht geaendert werden.
> Nur **PROJECT_PATH** und **OPENAI_API_KEY** muessen gesetzt werden.

---

## Schritt 5: Dashboard starten

```bash
chmod +x start.sh clean.sh
./start.sh
```

Beim **ersten Start** werden Docker-Images geladen (dauert 1-2 Minuten).
Danach startet das Dashboard in ca. 5 Sekunden.

Wenn Sie diese Meldung sehen:

```
[OK] Dashboard is ready!
[OK] Open: http://localhost
```

Dann oeffnen Sie **http://localhost** im Windows-Browser (Chrome, Edge, Firefox).

---

## Dashboard bedienen

| Aktion | Befehl |
|--------|--------|
| **Starten** | `./start.sh` |
| **Stoppen** | `./start.sh stop` |
| **Logs anzeigen** | `./start.sh logs` |
| **Komplett zuruecksetzen** | `./clean.sh` |

> Nach `clean.sh` koennen Sie mit `./start.sh` alles neu starten.
> Ihre `.env`-Konfiguration und `config/` bleiben erhalten.

---

## Haeufige Probleme

| Problem | Loesung |
|---------|---------|
| "Docker is not running" | `sudo service docker start` in Ubuntu eingeben |
| "API key not configured" | `.env` oeffnen und `OPENAI_API_KEY` setzen |
| "Repository path not configured" | `.env` oeffnen und `PROJECT_PATH` setzen |
| Browser zeigt nichts an | 30 Sekunden warten, http://localhost neu laden |
| Port 80 belegt | Andere Webserver stoppen (IIS, XAMPP, Skype) |
| "permission denied" bei start.sh | `chmod +x start.sh clean.sh` eingeben |
| "Cannot connect to Docker daemon" | `sudo service docker start` eingeben |
| Ubuntu vergisst Docker nach Neustart | Nach jedem Windows-Neustart einmal `sudo service docker start` eingeben |

---

## Update auf neue Version

1. `./start.sh stop`
2. Neue ZIP-Datei nach Ubuntu kopieren und entpacken (wie Schritt 3)
3. Alte `.env` in den neuen Ordner kopieren: `cp ../sdlc-pilot-v0.7.4/.env .`
4. `./start.sh`

---

## LLM-Modell-Konfiguration (optional)

Die `.env`-Datei enthaelt Modell-Einstellungen. Die Standardwerte funktionieren sofort — nur aendern wenn noetig:

| Variable | Standard | Zweck |
|----------|----------|-------|
| `MODEL` | `openai/complex_tasks` | Architektur-Analyse, Planung |
| `FAST_MODEL` | `openai/chat` | Schnelle Aufgaben (Triage, Reviews) |
| `CODEGEN_MODEL` | `openai/code` | Code-Generierung |
| `VISION_MODEL` | `openai/vision` | OCR, Dokumenten-Analyse |
| `EMBED_MODEL` | `embed` | Semantische Suche |

---

## Architektur

```
Windows-Browser (http://localhost)
    |
    v
+-----------------------+
|  Frontend (nginx)     |  Port 80
|  Angular Dashboard    |
|  /api/* --------------|---> Backend
+-----------------------+
                              |
                         +----v--------------------+
                         |  Backend (FastAPI)       |
                         |  Python 3.12             |
                         |  /project --> Ihr Repo   |
                         +-------------------------+
                                    |
                                    v
                         LLM API (Sovereign AI Platform)
```
