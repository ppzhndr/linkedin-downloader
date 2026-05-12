# LinkedIn Post Downloader

Speichert Text, Bilder und Videos aus LinkedIn-Posts als übersichtliche HTML-Datei.

---

## Dateien

```
linkedin-downloader/
├── app.py                   ← startet die Web-Oberfläche
├── linkedin_downloader.py   ← das eigentliche Download-Script
└── README.md                ← diese Anleitung
```

---

## 1. Python installieren

1. Gehe auf **https://python.org/downloads** und lade die neueste Version herunter
2. Starte den Installer
3. **Wichtig:** Setze den Haken bei **„Add Python to PATH"** (ganz unten im ersten Fenster)
4. Klicke „Install Now"

---

## 2. Abhängigkeiten installieren

Öffne die **Windows-Eingabeaufforderung** (Win + R → `cmd` eingeben → Enter) oder **PowerShell**, navigiere zum Ordner mit den Dateien und führe aus:

```
python -m pip install flask requests beautifulsoup4 browser-cookie3
```

Das muss nur **einmalig** gemacht werden.

---

## 3. Programm starten

Doppelklick auf `app.py` – oder im Terminal:

```
python app.py
```

Öffne dann im Browser: **http://localhost:5000**

Das Fenster (Terminal/PowerShell) muss während der Nutzung geöffnet bleiben. Schließen mit `Strg + C`.

---

## 4. Einen Post herunterladen

1. LinkedIn im Browser öffnen und zum gewünschten Post navigieren
2. Die URL aus der Adresszeile kopieren (z.B. `https://www.linkedin.com/posts/...`)
3. URL in das Feld einfügen
4. **Browser auswählen**, in dem du bei LinkedIn eingeloggt bist (z.B. Chrome oder Firefox)
   – nur nötig für Posts, die Login erfordern; bei öffentlichen Posts weglassen
5. **„Download starten"** klicken
6. Nach Abschluss: **„HTML-Report öffnen"** klickt die fertige Datei direkt auf

Die HTML-Datei wird außerdem im Ordner `linkedin_downloads` (im selben Verzeichnis wie `app.py`) gespeichert und kann jederzeit per Doppelklick im Browser geöffnet werden.

---

## Ergebnis

Pro Post wird eine `.html`-Datei erstellt, die enthält:

- **Name** des Autors und **Datum** des Posts
- Den vollständigen **Post-Text** (mit hervorgehobenen Hashtags)
- Alle **Bilder** eingebettet (funktioniert auch ohne Internet)
- Link zurück zum **Original-Post** auf LinkedIn

---

## Häufige Probleme

| Problem | Lösung |
|---|---|
| `python` wird nicht erkannt | Python neu installieren, Haken bei „Add to PATH" setzen |
| `pip` wird nicht erkannt | `python -m pip install ...` statt `pip install ...` verwenden |
| Kein Text gefunden | Post ist möglicherweise privat – Browser mit Login auswählen |
| Chrome-Cookie-Fehler | Chrome komplett schließen, dann erneut versuchen |
| Seite lädt nicht | Sicherstellen dass `app.py` noch läuft (Terminal offen) |
