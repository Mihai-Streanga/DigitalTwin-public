"""Pornirea și transcrierea, pe un server adevărat.

Pornește uvicorn pe 8199, ca să nu atingă serverul de pe 8100 pe care îl
folosește autorul. Cu `sys.executable`, nu cu `py`: lansatorul `py` ține un
proces copil, iar oprirea lansatorului lasă copilul agățat de port.

Transcrierea are un reper, nu un corpus: `tests/date/liana-16k.wav`, o frază rostită
de vocea Lianei. Proba spune că lanțul merge cap-coadă — WAV, motor, text — nu
cât de bine aude vocea autorului; aia cere corpusul, care lipsește.

Efect colateral: transcrierea reușită lasă un rând în `date/ureche.log`, ca orice
rostire. Rândul e adevărat; nu se șterge.
"""
import re
import subprocess
import sys
import time
from pathlib import Path

import httpx

R = Path(__file__).resolve().parent.parent
PORT = 8199
REPER = R / "tests" / "date" / "liana-16k.wav"
# Ce se aude în reper. „Mih.AI” se rostește „Mihai”, deci asta e și textul.
TEXT_REPER = "Astăzi verificăm dacă Mihai mai vorbește și mai aude înainte de actualizare"
JURNAL_SERVER = R / "tmp-proba-pornire.log"


def normal(t: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", t.lower()).split())


def lipsa_ureche() -> str | None:
    """Motivul pentru care probele urechii se sar, sau `None` dacă modelul e pe disc.

    Fără model, urechea nu are cum să pornească: probele ar cădea după două minute
    de așteptare, fără să spună de ce. Se sar, cu motivul și cu comanda care-l aduce.
    """
    sys.path.insert(0, str(R))
    from server.transcriere import MODEL
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(MODEL, local_files_only=True)
    except Exception as e:
        return (f"modelul {MODEL} nu e în cache-ul HuggingFace ({type(e).__name__}) — sărit; "
                f"se aduce cu snapshot_download('{MODEL}')")
    return None


def probe(asteptare_ureche: float = 120.0):
    rez = []
    with JURNAL_SERVER.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server.app:aplicatie", "--port", str(PORT)],
            cwd=R, stdout=log, stderr=subprocess.STDOUT)
    c = httpx.Client(base_url=f"http://localhost:{PORT}", timeout=60)
    try:
        t0 = time.perf_counter()
        viu = None
        while time.perf_counter() - t0 < 60 and proc.poll() is None:
            try:
                viu = c.get("/api/viu").json()
                break
            except httpx.HTTPError:
                time.sleep(0.25)
        t_viu = time.perf_counter() - t0
        rez.append(("pornire: /api/viu răspunde", viu == {"viu": True},
                    f"{t_viu:.1f} s" if viu else f"nimic în 60 s; vezi {JURNAL_SERVER.name}"))
        if viu is None:
            return rez

        lipsa = lipsa_ureche()
        if lipsa:
            rez.append(("pornire: urechea gata singură, fără clic", None, lipsa))
            rez.append(("ureche: reperul transcris exact", None, lipsa))
            return rez

        s = {}
        while time.perf_counter() - t0 < asteptare_ureche:
            s = c.get("/api/stare").json()
            if s.get("ureche"):
                break
            time.sleep(0.5)
        rez.append(("pornire: urechea gata singură, fără clic", bool(s.get("ureche")),
                    f"{time.perf_counter() - t0:.1f} s de la pornire, pe {s.get('ureche_dispozitiv')}"))

        r = c.post("/api/transcrie", content=REPER.read_bytes())
        text = r.json().get("text", "") if r.status_code == 200 else r.text
        rez.append(("ureche: reperul transcris exact", normal(text) == normal(TEXT_REPER),
                    f"„{text.strip()}”"))
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
        c.close()
    return rez
