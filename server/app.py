"""Serverul Mih.AI. O pagina, un camp, un raspuns.

PORNIRE:  py -m uvicorn server.app:aplicatie --port 8100
          (sau dublu-clic pe porneste.vbs, care face acelasi lucru fara fereastra)

DE CE FIRUL CONVERSATIEI STA IN MEMORIE, si nu pe disc:

  Fiindca disparitia lui la repornire e comportamentul corect, nu o scapare.
  Serverul se reporneste deliberat intre conversatii: o conversatie incheiata
  e incheiata. Ce trebuie sa supravietuiasca — textul ei — e deja pe
  disc, scris dupa fiecare schimb de `jurnal.py`.

DE CE `/api/viu` NU atinge API-ul: ca sa se poata intreba des si gratis daca
serverul e sus. Un `viu` care costa bani nu se cheama niciodata.

CE NU E AICI, deliberat, pana dupa zece conversatii reale: MCP, cautare, autentificare, istoric in interfata, markdown randat.
"""

import asyncio
import importlib.util
import json
import time
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import (FileResponse, JSONResponse, Response,
                               StreamingResponse)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import fereastra, jurnal, model, prompt, transcriere, voce

RADACINA = Path(__file__).resolve().parent.parent
WEB = Path(__file__).resolve().parent / "web"

@asynccontextmanager
async def viata(_: FastAPI):
    """Ce se face o dată, la pornire.

    Vocea și urechea se încălzesc amândouă aici, pe fire de fundal: oricare
    din ele, rece, se vede ca o așteptare la primul folos (urechea a costat
    28 s pe 4 octombrie 2026). Microfonul rămâne oprit — se pregătește
    motorul, nu se ascultă; vezi `transcriere.pregateste_in_fundal`.
    """
    voce.incalzeste_in_fundal()
    transcriere.pregateste_in_fundal()
    yield


aplicatie = FastAPI(title="Mih.AI", lifespan=viata)
aplicatie.mount("/web", StaticFiles(directory=WEB), name="web")

GAZDE = {"localhost", "127.0.0.1"}


@aplicatie.middleware("http")
async def marginea(cerere: Request, urmatorul):
    """Usile `/api/*` raspund numai paginii de pe masina asta.

    Serverul asculta doar pe 127.0.0.1, dar asta nu ajunge: orice site deschis
    in browser poate trimite un POST catre `localhost:8100` — `/api/transcrie`,
    `/api/fereastra/*` — fara sa-l opreasca nimic. Iar prin DNS rebinding, un
    nume strain care ajunge pe 127.0.0.1 ar putea chema si `/api/mesaj`, care
    costa bani.

    `Host` inchide rebinding-ul: numele din cerere trebuie sa fie al masinii.
    `Origin` inchide POST-ul de pe alt site: browserul il trimite mereu la un
    POST, iar pagina noastra il are egal cu `http://` + `Host`. Fara `Origin`
    (curl, `tests/`) trece — un program local poate oricum mai mult decat atat.
    """
    if cerere.url.path.startswith("/api/"):
        gazda = cerere.headers.get("host", "")
        if gazda.rsplit(":", 1)[0] not in GAZDE:
            return JSONResponse(status_code=403,
                                content={"eroare": f"Host strain: {gazda!r}"})
        origine = cerere.headers.get("origin")
        if cerere.method != "GET" and origine is not None \
                and origine != f"http://{gazda}":
            return JSONResponse(status_code=403,
                                content={"eroare": f"Origin strain: {origine!r}"})
    return await urmatorul(cerere)

# Firele deschise: id de conversatie -> lista de mesaje in forma ceruta de API.
FIRE: dict[str, list[dict]] = {}


class Mesaj(BaseModel):
    id: str
    text: str


@aplicatie.get("/")
async def pagina():
    return FileResponse(WEB / "index.html")


@aplicatie.get("/api/viu")
async def viu():
    return {"viu": True}


@aplicatie.post("/api/fereastra/dictarea-deasupra")
async def dictarea_deasupra():
    """Pune fereastra de dictare (Iris) inapoi peste pagina, fara sa-i dea focus.

    Chemata cand pagina primeste focus. Nu porneste si nu opreste nimic la vecin
    — vezi `server/fereastra.py`.
    """
    return {"ridicate": fereastra.ridica_dictarea()}


@aplicatie.post("/api/fereastra/ascunde")
async def ascunde_fereastra():
    """ESC din pagina. Nu atinge conversatia si nu costa nimic — vezi
    `server/fereastra.py` pentru ce anume minimizeaza si de ce atat."""
    return {"minimizate": fereastra.minimizeaza()}


@aplicatie.get("/api/conversatie-noua")
async def conversatie_noua():
    id_conv = jurnal.id_nou()
    FIRE[id_conv] = []
    return {"id": id_conv}


def _costul_lunii() -> tuple[float, int]:
    """Cat s-a cheltuit luna asta si cate randuri n-au putut fi citite.

    Se importa `citeste` din `scripts/consum-api.py`, nu se copiaza: o formula de
    pret scrisa in doua locuri ramane in urma intr-unul, si atunci doua unelte dau
    doua cifre despre aceiasi bani. Randurile stricate se numara si pleaca spre
    pagina — sarite in tacere, ar face cifra mai mica fara ca cineva sa vada.
    """
    cale = RADACINA / "scripts" / "consum-api.py"
    registru = RADACINA / "date" / "consum" / f"{date.today():%Y-%m}.jsonl"
    if not cale.exists() or not registru.exists():
        return 0.0, 0
    spec = importlib.util.spec_from_file_location("consum_api", cale)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    r = modul.citeste(registru)
    return round(r["cost"], 4), len(r["stricate"])


@aplicatie.get("/api/stare")
async def stare():
    cost, stricate = _costul_lunii()
    return {
        "model": model.MODEL,
        "prompt": prompt.versiunea(),
        "conversatii": jurnal.cate_conversatii(),
        "consum_luna_dolari": cost,
        "consum_randuri_stricate": stricate,
        "fire_deschise": len(FIRE),
        "ureche": transcriere.pregatit(),
        "ureche_dispozitiv": transcriere.dispozitivul(),
    }


@aplicatie.post("/api/ureche")
async def porneste_urechea():
    """Așteaptă motorul de transcriere. Chemată la primul clic pe buton.

    Motorul se pregătește deja de la pornire (`viata`); clicul îl găsește gata
    sau așteaptă la zăvor cât a mai rămas. Așteptarea blochează firul, de-aia
    pleacă în executor: altfel serverul n-ar răspunde la nimic cât durează.

    Răspunsul spune ȘI pe ce dispozitiv a pornit: dacă placa n-a fost, motorul
    merge pe procesor, de șase-nouă ori mai lent. Diferența se simte, deci se
    scrie — altfel arată ca un microfon stricat.
    """
    bucla = asyncio.get_running_loop()
    try:
        await bucla.run_in_executor(None, transcriere.pregateste)
        return {"pregatit": True, "dispozitiv": transcriere.dispozitivul()}
    except Exception as e:
        return JSONResponse(status_code=503,
                            content={"pregatit": False, "eroare": f"{type(e).__name__}: {e}"})


@aplicatie.post("/api/transcrie")
async def transcrie(cerere: Request):
    """WAV 16 kHz mono în corpul cererii, text afară. Nu costă niciun token."""
    octeti = await cerere.body()
    if not octeti:
        return JSONResponse(status_code=400, content={"eroare": "corp gol"})
    bucla = asyncio.get_running_loop()
    try:
        return await bucla.run_in_executor(None, transcriere.transcrie, octeti)
    except Exception as e:
        return JSONResponse(status_code=500,
                            content={"eroare": f"{type(e).__name__}: {e}"})


class Rostire(BaseModel):
    text: str


@aplicatie.post("/api/vorbeste")
async def vorbeste(r: Rostire):
    """Text în corp, WAV afară. Local, pe procesor — nu costă niciun token.

    Prima cerere plătește încărcarea vocii (~1,8 s pentru `high`); pe urmă
    sinteza merge de vreo șapte ori mai repede decât timpul real. Ca și la
    ureche, munca pleacă în executor: ONNX blochează firul care o cheamă.
    """
    if not r.text.strip():
        return JSONResponse(status_code=400, content={"eroare": "text gol"})
    bucla = asyncio.get_running_loop()
    try:
        t = time.perf_counter()
        wav = await bucla.run_in_executor(None, voce.sintetizeaza, r.text)
        print(f"[voce] {len(r.text)} caractere in {time.perf_counter() - t:.2f} s", flush=True)
        return Response(content=wav, media_type="audio/wav")
    except Exception as e:
        return JSONResponse(status_code=500,
                            content={"eroare": f"{type(e).__name__}: {e}"})


def _sse(eveniment: str, date_: dict) -> str:
    return f"event: {eveniment}\ndata: {json.dumps(date_, ensure_ascii=False)}\n\n"


@aplicatie.post("/api/mesaj")
async def trimite(m: Mesaj):
    if not jurnal.valid(m.id):
        return StreamingResponse(
            iter([_sse("eroare", {"text": "id de conversatie invalid"})]),
            media_type="text/event-stream",
        )
    fir = FIRE.setdefault(m.id, [])

    async def flux():
        intrebare = m.text.strip()
        fir.append({"role": "user", "content": intrebare})
        bucati: list[str] = []
        raport: dict = {}
        gol: str | None = None
        try:
            async for fel, bucata in model.raspunde(fir, prompt.compune(),
                                                    raport=raport):
                if fel == "gand":
                    # Gindirea pleaca spre pagina, dar NU intra in `bucati`:
                    # ce se pune in fir si in jurnal e replica, nu ciorna ei.
                    yield _sse("gand", {"text": bucata})
                    continue
                bucati.append(bucata)
                yield _sse("text", {"text": bucata})
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # Ce s-a stricat se spune, nu se ascunde intr-un "a aparut o eroare".
            yield _sse("eroare", {"text": f"{type(e).__name__}: {e}"})
        finally:
            raspuns = "".join(bucati)
            if raspuns:
                fir.append({"role": "assistant", "content": raspuns})
                jurnal.scrie_schimbul(m.id, intrebare, raspuns,
                                      model.MODEL, prompt.versiunea())
            else:
                # Fara raspuns, intrebarea nu ramane in fir: altfel urmatorul
                # apel pleaca cu doua mesaje `user` la rand si API-ul il refuza.
                fir.pop()
                # DAR NU SE TACE. Pe 30 august, de doua ori, apelul a plecat, a
                # fost platit (output 2000, adica exact plafonul) si n-a scos
                # nicio litera — iar pagina a aratat o bula goala. Autorul a
                # crezut ca s-a pierdut dictarea si a redictat un paragraf de
                # sase randuri, degeaba. O replica pierduta se SPUNE, cu motivul
                # venit de la API, nu se deduce.
                if raport:
                    blocuri = ", ".join(raport.get("blocuri") or ["niciunul"])
                    gol = (f"modelul nu a scris nimic — s-a oprit la "
                           f"{raport.get('stop')}, blocuri: {blocuri}")
                    if raport.get("stop") == "max_tokens":
                        gol += (f"; plafonul e {model.MAX_TOKENI} de tokeni si "
                                "s-a dus tot pe continut care nu e text")
                    gol += ". Textul tau e inca in cimp."
        if gol:
            yield _sse("eroare", {"text": gol})
        yield _sse("gata", {})

    return StreamingResponse(flux(), media_type="text/event-stream")
