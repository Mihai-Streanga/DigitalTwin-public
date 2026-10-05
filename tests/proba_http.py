"""Contractul HTTP server↔pagină, pe rutele care nu costă.

`TestClient` fără `with`: `viata` nu rulează, deci vocea și urechea nu se
încarcă — proba ține câteva secunde, nu un minut. Pornirea adevărată e în
`proba_pornire.py`.

Lăsate afară, deliberat: `/api/fereastra/*` (minimizează ferestre reale pe
ecranul autorului) și `/api/mesaj` pe ramura bună (costă bani).
"""
import io
import sys
import wave
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))

# Cheile pe care le citește `pagina.js`, în `arataStarea`.
CHEI_STARE = {"model", "conversatii", "consum_luna_dolari", "consum_randuri_stricate",
              "ureche", "ureche_dispozitiv"}


def wav(rata: int, latime: int, secunde: float = 0.2) -> bytes:
    """Un WAV de liniște, construit anume greșit — rata sau lățimea."""
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(latime)
        w.setframerate(rata)
        w.writeframes(b"\x00" * int(rata * secunde) * latime)
    return b.getvalue()


def probe():
    from fastapi.testclient import TestClient
    from server import app, jurnal

    c = TestClient(app.aplicatie, base_url="http://localhost:8100")
    rez = []

    def p(nume, ok, detaliu=""):
        rez.append((f"http: {nume}", bool(ok), detaliu))

    r = c.get("/")
    p("GET / dă pagina", r.status_code == 200 and "text/html" in r.headers["content-type"],
      r.status_code)
    r = c.get("/api/viu")
    p("GET /api/viu", r.status_code == 200 and r.json() == {"viu": True}, r.text)
    r = c.get("/api/stare")
    lipsa = CHEI_STARE - set(r.json())
    p("GET /api/stare are cheile paginii", r.status_code == 200 and not lipsa,
      f"lipsesc {sorted(lipsa)}" if lipsa else "")
    r = c.get("/api/conversatie-noua")
    p("GET /api/conversatie-noua dă un id valid", jurnal.valid(r.json().get("id", "")), r.text)

    r = c.post("/api/mesaj", json={"id": "../afara", "text": "x"})
    p("POST /api/mesaj cu id invalid: eroare, fără apel",
      r.status_code == 200 and "event: eroare" in r.text and "invalid" in r.text,
      r.text.strip().replace(chr(10), " | ")[:80])
    # Fără cheie, apelul nu pleacă: o singură eroare, cea adevărată. Cheia se scoate
    # numai din procesul ăsta și se pune la loc; nicio cerere nu iese de pe mașină.
    from server import model
    cheie, client = model.os.environ.pop("ANTHROPIC_API_KEY", None), model._client
    model._client = None
    try:
        id_conv = c.get("/api/conversatie-noua").json()["id"]
        r = c.post("/api/mesaj", json={"id": id_conv, "text": "x"})
    finally:
        model._client = client
        if cheie is not None:
            model.os.environ["ANTHROPIC_API_KEY"] = cheie
    p("POST /api/mesaj fără cheie: o singură eroare, cu motivul",
      r.text.count("event: eroare") == 1 and "ANTHROPIC_API_KEY" in r.text,
      r.text.strip().replace(chr(10), " | ")[:120])
    r = c.post("/api/vorbeste", json={"text": "   "})
    p("POST /api/vorbeste cu text gol: 400", r.status_code == 400, r.text)
    r = c.post("/api/transcrie", content=b"")
    p("POST /api/transcrie cu corp gol: 400", r.status_code == 400, r.text)
    r = c.post("/api/transcrie", content=wav(8000, 2))
    p("POST /api/transcrie pe 8 kHz: 500 cu motivul",
      r.status_code == 500 and "astept 16000 Hz" in r.text, r.text)
    r = c.post("/api/transcrie", content=wav(16000, 1))
    p("POST /api/transcrie pe 8 biți: 500 cu motivul",
      r.status_code == 500 and "astept PCM pe 16 biti" in r.text, r.text)

    # Marginea: `marginea` din `server/app.py`.
    r = c.get("/api/stare", headers={"host": "evil.example:8100"})
    p("margine: Host străin → 403", r.status_code == 403, r.text)
    r = c.get("/", headers={"host": "evil.example:8100"})
    p("margine: pagina rămâne deschisă", r.status_code == 200, r.status_code)
    r = c.post("/api/vorbeste", json={"text": " "}, headers={"origin": "http://evil.example"})
    p("margine: POST cu Origin străin → 403", r.status_code == 403, r.text)
    r = c.post("/api/vorbeste", json={"text": " "}, headers={"origin": "http://localhost:9999"})
    p("margine: POST cu Origin pe alt port → 403", r.status_code == 403, r.text)
    r = c.post("/api/vorbeste", json={"text": " "}, headers={"origin": "http://localhost:8100"})
    p("margine: POST cu Origin propriu trece", r.status_code == 400, r.text)
    c2 = TestClient(app.aplicatie, base_url="http://127.0.0.1:8100")
    r = c2.get("/api/viu")
    p("margine: 127.0.0.1 trece", r.status_code == 200, r.status_code)
    return rez
