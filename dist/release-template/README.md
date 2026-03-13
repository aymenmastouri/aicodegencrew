# SDLC Pilot - Dashboard

AI-powered Software Development Lifecycle assistant.

---

## Schritt 1: WSL2 + Ubuntu installieren (einmalig)

> WSL2 ist ein eingebautes Linux in Windows. Keine extra Lizenz noetig.
> Sie muessen es nur **einmal** installieren — danach bleibt es auf Ihrem PC.

1. Klicken Sie auf das **Windows-Startmenue** (das Windows-Symbol unten links in der Taskleiste)
2. Tippen Sie **"Microsoft Store"** und klicken Sie auf die App
3. Oben im Store in der Suchleiste **"Ubuntu"** eingeben
4. **"Ubuntu 22.04 LTS"** (oder neuer) anklicken und auf **"Installieren"** klicken
5. Warten bis die Installation fertig ist, dann auf **"Oeffnen"** klicken
6. Es oeffnet sich ein schwarzes Fenster (das ist das Ubuntu-Terminal)
7. Ubuntu fragt nach einem **Benutzernamen** — geben Sie einen ein (z.B. Ihren Vornamen, kleingeschrieben, ohne Leerzeichen)
8. Ubuntu fragt nach einem **Passwort** — geben Sie eines ein und merken Sie es sich
   (Hinweis: beim Tippen des Passworts sehen Sie nichts — das ist normal!)
9. Wenn Sie `$` mit blinkendem Cursor sehen, ist Ubuntu bereit

> **Falls Ubuntu nicht im Store erscheint:**
> Klicken Sie auf das Startmenue, tippen Sie **"PowerShell"**, klicken Sie
> mit der **rechten Maustaste** auf "Windows PowerShell" und waehlen Sie
> **"Als Administrator ausfuehren"**. Geben Sie ein:
> ```
> wsl --install
> ```
> Starten Sie danach den PC neu. Ubuntu erscheint dann im Startmenue.

---

## Schritt 2: Docker in Ubuntu installieren (einmalig)

### Ubuntu-Terminal oeffnen

Wenn das Terminal von Schritt 1 noch offen ist, nutzen Sie es weiter.
Falls Sie es geschlossen haben:

- Klicken Sie auf das **Windows-Startmenue**
- Tippen Sie **"Ubuntu"**
- Klicken Sie auf **"Ubuntu 22.04 LTS"**
- Das schwarze Terminal-Fenster oeffnet sich

### Docker installieren

Geben Sie im Terminal die folgenden Befehle ein.
Kopieren Sie jeweils **eine Zeile**, fuegen Sie sie mit **Rechtsklick** ins
Terminal ein und druecken Sie **Enter**. Warten Sie bis jeder Befehl fertig ist,
bevor Sie den naechsten eingeben:

```
sudo apt-get update
```
(Fragt nach Ihrem Passwort — eingeben und Enter druecken. Sie sehen nichts beim Tippen, das ist normal.)

```
sudo apt-get install -y docker.io docker-compose-plugin unzip
```

```
sudo usermod -aG docker $USER
```

Jetzt **schliessen Sie das Terminal-Fenster** (oben rechts auf X klicken)
und **oeffnen Sie Ubuntu erneut** aus dem Startmenue. Das ist wichtig,
damit die Rechte aktiv werden.

Im neuen Terminal Docker starten:

```
sudo service docker start
```

Pruefen ob Docker laeuft:

```
docker info
```

Wenn viel Text erscheint und irgendwo **"Server Version"** steht — Docker funktioniert!
Falls eine Fehlermeldung kommt, nochmal `sudo service docker start` eingeben.

---

## Schritt 3: ZIP-Datei entpacken

Die ZIP-Datei die Sie erhalten haben liegt vermutlich in Ihrem Downloads-Ordner.
Ubuntu kann auf alle Windows-Dateien zugreifen. Der Pfad dazu beginnt mit `/mnt/c/`.

Geben Sie im Ubuntu-Terminal ein (Zeile fuer Zeile):

```
cd ~
```

```
cp /mnt/c/Users/IhrName/Downloads/sdlc-pilot-v0.7.4.zip .
```

> **Wichtig:** Ersetzen Sie `IhrName` durch Ihren Windows-Benutzernamen.
> Um Ihren Benutzernamen herauszufinden: oeffnen Sie im Windows Explorer
> den Ordner `C:\Users\` — dort sehen Sie Ihren Benutzernamen als Ordner.
>
> Beispiel: Wenn Ihr Benutzername `mmustermann` ist:
> `cp /mnt/c/Users/mmustermann/Downloads/sdlc-pilot-v0.7.4.zip .`

Dann entpacken:

```
unzip sdlc-pilot-v0.7.4.zip
```

In den Ordner wechseln:

```
cd sdlc-pilot-v0.7.4
```

---

## Schritt 4: Konfiguration

Sie muessen nur **zwei Werte** einstellen: den Pfad zu Ihrem Repository
und Ihren API-Key.

Zuerst die Vorlage kopieren:

```
cp .env.example .env
```

Dann die Datei oeffnen:

```
nano .env
```

Es oeffnet sich ein einfacher Texteditor im Terminal. Navigieren Sie mit den
**Pfeiltasten** nach unten.

### PROJECT_PATH aendern

Suchen Sie die Zeile:

```
PROJECT_PATH=C:\path\to\your\repo
```

Loeschen Sie den alten Wert und schreiben Sie Ihren Repository-Pfad.
Windows-Pfade werden in Ubuntu so umgewandelt:

| Windows-Pfad | Ubuntu-Pfad |
|-------------|-------------|
| `C:\projects\myapp` | `/mnt/c/projects/myapp` |
| `D:\repos\backend` | `/mnt/d/repos/backend` |

Beispiel — aendern Sie die Zeile zu:

```
PROJECT_PATH=/mnt/c/projects/mein-projekt
```

### OPENAI_API_KEY aendern

Suchen Sie die Zeile:

```
OPENAI_API_KEY=sk-your-api-key-here
```

Ersetzen Sie `sk-your-api-key-here` durch Ihren echten API-Key.

### Speichern und schliessen

1. Druecken Sie **Strg+O** (Buchstabe O, nicht Null) — das speichert die Datei
2. Druecken Sie **Enter** um den Dateinamen zu bestaetigen
3. Druecken Sie **Strg+X** um den Editor zu schliessen

> **API_BASE** ist bereits voreingestellt und muss **nicht** geaendert werden.
> Sie muessen nur **PROJECT_PATH** und **OPENAI_API_KEY** setzen.

---

## Schritt 5: Dashboard starten

Geben Sie im Terminal ein:

```
chmod +x start.sh clean.sh
```

```
./start.sh
```

Beim **ersten Start** werden Docker-Images geladen. Das dauert 1-2 Minuten.
Danach startet das Dashboard in ca. 5 Sekunden.

Wenn Sie diese Meldung sehen:

```
[OK] Dashboard is ready!
[OK] Open: http://localhost
```

Dann oeffnen Sie Ihren **Windows-Browser** (Chrome, Edge oder Firefox)
und geben Sie in die Adressleiste ein:

```
http://localhost
```

Das Dashboard erscheint.

---

## Taegliche Nutzung

Nach einem PC-Neustart muessen Sie Ubuntu und Docker erneut starten:

1. **Startmenue** > **"Ubuntu"** oeffnen
2. Im Terminal eingeben:
   ```
   sudo service docker start
   ```
3. In den Ordner wechseln:
   ```
   cd ~/sdlc-pilot-v0.7.4
   ```
4. Dashboard starten:
   ```
   ./start.sh
   ```
5. Im Browser **http://localhost** oeffnen

### Befehle

| Was Sie tun wollen | Befehl im Ubuntu-Terminal |
|---------------------|---------------------------|
| Dashboard starten | `./start.sh` |
| Dashboard stoppen | `./start.sh stop` |
| Logs anzeigen | `./start.sh logs` |
| Alles zuruecksetzen | `./clean.sh` |

> Nach `./clean.sh` koennen Sie mit `./start.sh` alles neu starten.
> Ihre Konfiguration (`.env`) und Pipeline-Einstellungen (`config/`) bleiben erhalten.

---

## Haeufige Probleme

| Problem | Loesung |
|---------|---------|
| "Docker is not running" | Im Ubuntu-Terminal: `sudo service docker start` |
| "API key not configured" | `.env` oeffnen (`nano .env`) und `OPENAI_API_KEY` setzen |
| "Repository path not configured" | `.env` oeffnen (`nano .env`) und `PROJECT_PATH` setzen |
| Browser zeigt nichts an | 30 Sekunden warten, dann http://localhost neu laden |
| Port 80 belegt | Andere Programme stoppen die Port 80 nutzen (IIS, XAMPP, Skype) |
| "permission denied" bei start.sh | `chmod +x start.sh clean.sh` eingeben |
| "Cannot connect to Docker daemon" | `sudo service docker start` eingeben |
| Passwort wird nicht angezeigt | Das ist normal bei Linux — einfach tippen und Enter druecken |
| "unzip: command not found" | `sudo apt-get install -y unzip` eingeben |

---

## Update auf neue Version

1. Dashboard stoppen: `./start.sh stop`
2. Neue ZIP-Datei nach Ubuntu kopieren und entpacken (wie Schritt 3)
3. Alte Konfiguration uebernehmen: `cp ../sdlc-pilot-v0.7.4/.env .`
4. Starten: `./start.sh`

---

## LLM-Modell-Konfiguration (optional, fuer Fortgeschrittene)

Die `.env`-Datei enthaelt Modell-Einstellungen. Die Standardwerte funktionieren
sofort — nur aendern wenn Ihr Team andere Modell-Aliase verwendet:

| Variable | Standard | Zweck |
|----------|----------|-------|
| `MODEL` | `openai/complex_tasks` | Architektur-Analyse, Planung |
| `FAST_MODEL` | `openai/chat` | Schnelle Aufgaben (Triage, Reviews) |
| `CODEGEN_MODEL` | `openai/code` | Code-Generierung |
| `VISION_MODEL` | `openai/vision` | OCR, Dokumenten-Analyse |
| `EMBED_MODEL` | `embed` | Semantische Suche |
