"""Vorbire → text, local, pe placa grafică integrată.

NU COSTA NICIUN TOKEN. Whisper rulează pe laptop; costul lui e memorie și timp
de calcul, nu contor. Confuzia „model = cost" e reală, de-aia scrie aici.

DE UNDE VINE MODELUL: din cache-ul HuggingFace al utilizatorului, unde e deja
descărcat. Nimic nu se citește la rulare din alt proiect. Pachetele
(`openvino-genai`) sunt în Python-ul global, ca `py` însuși.

DE CE SE PREGATESTE LA PORNIREA SERVERULUI, pe fir de fundal (de la 4 octombrie
2026; inainte, la primul clic):

  Primul clic dupa pornirea masinii a costat 28 s, cu modelul citit la rece.
  O asteptare atat de lunga la microfon strica folosirea; cateva secunde de
  procesor la pornire, cand nimeni nu asteapta, nu. Cu cache-ul de compilare
  (`CACHE_OV`), pregatirea calda e ~0,8 s compilare + ~2,3 s incalzire.
  Microfonul ramane oprit: se pregateste motorul, nu se asculta.

CIFRELE, măsurate 24 august 2026: compilare 3,4–4,7 s; prima transcriere 3,43 s
(încălzirea); apoi **1,12 s pentru un clip de 40 de secunde**. O frază obișnuită
de 5–10 s stă mult sub o secundă.

DACA PLACA NU E, se cade pe procesor cu acelasi model — vezi `DISPOZITIVE`.
Rezerva e mai lenta de sase-noua ori, dar scrie aceleasi cuvinte, si pagina
spune pe ce merge. Teama ca doua conducte OpenVINO pe acelasi iGPU se bat
NU s-a confirmat: masurat pe 25 august, o a doua conducta a compilat in 3,2 s
si a mers la aceeasi viteza cat serverul o tinea pe prima.
"""

import io
import threading
import time
import unicodedata
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

MODEL = "OpenVINO/whisper-large-v3-turbo-int8-ov"

# REZERVA. Acelasi model, alt dispozitiv — nu alt motor si nu alt fisier.
#
# Masurat pe masina asta, 25 august 2026, pe aceleasi trei probe:
#
#   GPU  compilare 3,2 s  →  0,25 / 0,36 / 0,55 s pe rostiri de 1,8 / 7,1 / 13,7 s
#   CPU  compilare 1,2 s  →  2,28 / 2,44 / 2,87 s pe aceleasi
#
# Deci rezerva e de sase-noua ori mai lenta, dar scrie ACELEASI cuvinte: e
# acelasi model, cu aceleasi greseli si aceleasi diacritice. Alternativa —
# `faster-whisper` pe procesor, deja instalat pentru VAD — s-a masurat si a
# picat: `small` e mai rapid (1,5 s) dar sparge jargonul („indpaientul Anton
# Sonjei Son" in loc de „endpointul"), iar `large-v3-turbo` da 5,0 s, adica de
# doua ori mai lent decat aceeasi greutate prin OpenVINO. NPU a picat si el:
# 23 s de compilare, si apoi crapa pe `initial_prompt`.
#
# Ordinea e ordinea de incercare. Ce nu compileaza se noteaza si se trece mai
# departe; ce cade in timpul lucrului se arde si nu se mai incearca in sesiunea
# asta.
DISPOZITIVE = ("GPU", "CPU")
LIMBA = "<|ro|>"
RATA = 16000

# Whisper aude mai bine ce se așteaptă să audă. Numele care apar des în
# conversațiile cu Twin-ul, ca să nu fie sparte în bucăți fără sens.
CONTEXT = ("Discuție cu Mih.AI, un geamăn digital. "
           "Termeni: Twin, corpus, persona, prompt, API, Claude, Sonnet, commit, token.")

# A TREIA PLASA IMPOTRIVA LINISTII, si singura care chiar tine. Masurat pe
# masina asta, 25 august 2026, prin serverul adevarat: pe zgomot fara vorbire
# Whisper scoate text cu aceeasi siguranta cu care ar scoate adevarul —
# „Sa va multumim pentru vizionare!" la rms 0,002 si 0,008, „Amplified." la
# 0,020 si 0,040. In folosire reala a iesit „Hun er hann." — islandeza, din
# tacere, plecata mai departe la model, adica bani.
#
# Pragurile de energie NU pot separa cazul: zgomotul de camera trece de orice
# prag pus destul de jos cat sa lase vorbirea sopotita sa treaca. Silero VAD il
# separa perfect, si nu pe amplitudine: zgomot pur pana la rms 0,100 da 0,00 s
# de vorbire, iar vorbire coborata pana la rms 0,005 e prinsa intreaga. „Da." de
# 0,38 s trece. Costa 5–10 ms pe rostire, pe procesor.
#
# Modelul vine cu `faster-whisper`, care era deja instalat ca rezerva pe CPU.
# Nu se descarca nimic, nu se cumpara nimic, nu costa niciun token.
PRAG_VORBIRE = 0.20  # secunde de vorbire adevarata sub care nu se transcrie

# A PATRA PLASA: ce trece de VAD si tot nu e vorbire.
#
# Silero prinde tacerea si zgomotul, dar NU prinde sunetele omenesti care nu
# sunt cuvinte: o tuse are corzi vocale, deci e "vorbire". Masurat in folosire
# reala pe 25 august, dupa ce VAD-ul era deja pus: o tuse a iesit „Cough." si
# rostirea urmatoare „Svík, hvað er það?".
#
# Scorul motorului NU ajuta: `scores` da 1.000 si pe vorbire, si pe zgomot pur,
# si pe tuse — masurat. Limba nici atat: e fortata pe romana, deci raportata tot
# romana chiar cand scrie islandeza. Deci se judeca TEXTUL, cu doua reguli care
# nu sunt liste de cuvinte:
#
#   1. LITERELE. Romana nu are ð, þ, á, í, ø, ñ. Cand apar, motorul a plecat in
#      alta limba — semnul clasic al halucinatiei pe sunet fara cuvinte.
#   2. RITMUL. Vorbirea omeneasca sta sub ~4 cuvinte pe secunda de vorbire
#      efectiva; controlul masurat da 3,3, iar „Da." da 1,8. Patru cuvinte
#      islandeze peste o tuse de 0,4 s inseamna 10. Plafonul e pus la 6, adica
#      la aproape dublul vorbirii repezi: taie inventia, nu graba.
#
# NU exista lista neagra care sa judece o rostire intreaga. „Multumim pentru
# vizionare" s-ar prinde, dar lista se potriveste pe ce s-a intamplat deja si
# rateaza restul; iar ce scapa se vede in `date/ureche.log`, care de-aia exista.
PRAG_RITM = 6.0  # cuvinte pe secunda de vorbire, peste care nu e om

_LITERE_ROMANE = set("aăâbcdefghiîjklmnopqrsștțuvwxyzşţ")

# A CINCEA PLASA: coada de subtitrare lipita la o rostire ADEVARATA.
#
# DE CE E ALT CAZ decat cele patru de mai sus, si de ce „fara lista neagra" nu
# se contrazice aici. Pe 30 august, la 20:19, o rostire de 30,6 secunde de
# vorbire curata s-a incheiat cu „Sa va multumim pentru vizionare!". Rostirea a
# trecut, corect, prin toate cele patru plase: energia era vorbire, VAD-ul a
# gasit 28,8 secunde de vorbire, alfabetul e romanesc, ritmul e omenesc. **Prin
# constructie n-aveau cum s-o prinda: toate patru judeca rostirea intreaga, iar
# aici 95% din ea e vorbire adevarata.** Ce se lipise era o coada.
#
# Whisper e antrenat, printre altele, pe subtitrari de pe YouTube, si pe o
# tacere de la capatul unui clip completeaza cu formula de incheiere pe care a
# vazut-o de un milion de ori. Autorul a recunoscut-o din prima: „face chestia
# aia pe care o face el din cand in cand". Odata la 67 de rostiri, in log.
#
# Regula de mai jos e ingusta cu intentie, si fiecare margine e o margine:
#   - se uita NUMAI la ultima propozitie, nu cauta prin text;
#   - taie numai daca ce ramane nu e gol — o rostire care e DOAR atat e alt caz,
#     si il prind plasele de sus;
#   - numai daca ultima propozitie e scurta, sub `MAXIM_COADA` cuvinte: un outro
#     are cinci, o fraza adevarata care pomeneste subiectul are mai multe. In
#     aceeasi conversatie, la 20:20, autorul a spus el insusi cuvintele
#     „vizionare" si „abonati" cand mi-a povestit ce s-a intamplat — si fraza
#     aia NU trebuie taiata;
#   - ce s-a taiat se scrie in `date/ureche.log`, pe rindul rostirii. O taietura
#     nevazuta ar fi mai rea decat halucinatia.
COZI_DE_SUBTITRARE = (
    "multumim pentru vizionare",
    "multumesc pentru vizionare",
    "abonati va",
    "ne vedem data viitoare",
    "subtitrare",
)
MAXIM_COADA = 8       # cuvinte; peste atat, ultima propozitie e vorbire
_SEMNE_DE_FINAL = ".!?…"

JURNAL = Path(__file__).resolve().parent.parent / "date" / "ureche.log"


def _straina(text: str) -> str | None:
    """Prima litera care nu exista in alfabetul roman, daca exista vreuna."""
    for c in text.lower():
        if unicodedata.category(c).startswith("L") and c not in _LITERE_ROMANE:
            return c
    return None


def _gol(s: str) -> str:
    """Textul redus la cuvinte, fara diacritice si fara semne, pentru comparat."""
    desfacut = unicodedata.normalize("NFD", s.lower())
    litere = "".join(c for c in desfacut if not unicodedata.combining(c))
    return " ".join("".join(c if c.isalnum() else " " for c in litere).split())


def _fara_coada(text: str) -> tuple[str, str | None]:
    """Textul fara ultima propozitie, daca aia e un outro de subtitrare.

    Intoarce (ce ramane, ce s-a taiat). Vezi `COZI_DE_SUBTITRARE` pentru de ce.
    """
    intreg = text.strip()
    if not intreg:
        return text, None
    # Ultimul semn de final care NU e chiar ultimul caracter: acolo incepe
    # ultima propozitie. Fara excluderea ultimului caracter, punctul de la
    # capatul textului ar fi mereu granita si ultima propozitie ar iesi goala.
    taietura = max(intreg.rfind(s, 0, len(intreg) - 1) for s in _SEMNE_DE_FINAL)
    if taietura < 0:
        return text, None  # o singura propozitie: aia e rostirea, nu o coada
    ultima = intreg[taietura + 1:].strip()
    inainte = intreg[:taietura + 1].strip()
    if not ultima or not inainte:
        return text, None
    cuvinte = _gol(ultima)
    if len(cuvinte.split()) > MAXIM_COADA:
        return text, None
    if any(f in cuvinte for f in COZI_DE_SUBTITRARE):
        return inainte, ultima
    return text, None


def _noteaza(r: dict) -> None:
    """Fiecare rostire, cu verdictul ei, pe un rand.

    Exista fiindca o rostire aruncata in tacere arata exact ca un microfon
    stricat, iar o halucinatie scapata nu lasa nicio urma pe disc — s-a vazut
    pe 25 august, cand singura proba a fost conversatia insasi.
    """
    try:
        JURNAL.parent.mkdir(parents=True, exist_ok=True)
        campuri = [
            f"{datetime.now():%Y-%m-%d %H:%M:%S}",
            f"audio {r.get('durata_audio', 0):.2f}s",
            f"vorbire {r.get('vorbire', 0):.2f}s",
            r.get("motiv") or "trecut",
            (r.get("refuzat") or r.get("text") or "").replace(chr(9), " "),
        ]
        if r.get("taiat"):
            campuri.append("taiat: " + r["taiat"].replace(chr(9), " "))
        with JURNAL.open("a", encoding="utf-8") as f:
            f.write(chr(9).join(campuri) + chr(10))
    except Exception as e:  # jurnalul nu are voie sa rupa urechea
        print(f"[ureche] jurnalul n-a putut fi scris: {e}")

# CACHE-UL DE COMPILARE, in afara depozitului (`.gitignore` il prinde daca
# apare inauntru). Masurat 4 octombrie 2026: compilarea pe GPU 3,9 s fara el,
# 0,83 s cu el. Ocupa ~800 MB; daca dispare, prima pornire il reface singura.
CACHE_OV = Path.home() / "AppData" / "Local" / "Mih.AI" / "cache-openvino"

_motor = None
_dispozitiv: str | None = None   # pe ce merge acum: "GPU" sau "CPU"
_arse: set[str] = set()          # ce a cazut in timpul lucrului, in sesiunea asta
_vad_optiuni = None
_zavor = threading.Lock()
_eroare: str | None = None


def _secunde_de_vorbire(semnal: np.ndarray) -> float:
    """Cate secunde de vorbire omeneasca sunt in semnal, dupa Silero."""
    global _vad_optiuni
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    if _vad_optiuni is None:
        _vad_optiuni = VadOptions(threshold=0.5, min_speech_duration_ms=200,
                                  min_silence_duration_ms=200)
    felii = get_speech_timestamps(semnal, _vad_optiuni, sampling_rate=RATA)
    return sum(f["end"] - f["start"] for f in felii) / RATA


def pregatit() -> bool:
    return _motor is not None


def pregateste_in_fundal() -> None:
    """Pregateste motorul la pornirea serverului, pe fir separat.

    Pe 4 octombrie 2026, primul clic pe ureche dupa pornirea masinii a costat
    28 s (5,7 compilare + 22,2 incalzire), cu modelul citit la rece de pe
    disc. Platit la pornire, nu-l mai asteapta nimeni: clicul gaseste motorul
    gata, sau asteapta la zavor doar cat a mai ramas.

    MICROFONUL RAMANE OPRIT. Se pregateste motorul, nu se asculta nimic.
    Un motor care nu porneste nu opreste serverul: clicul o va spune.
    """
    def munca() -> None:
        try:
            pregateste()
        except Exception:
            pass  # `pregateste` a scris deja motivul; clicul il va da paginii

    threading.Thread(target=munca, daemon=True, name="pregatire-ureche").start()


def dispozitivul() -> str | None:
    """Pe ce merge urechea acum. `None` cat nu e pornita.

    Iese pana in pagina fiindca diferenta se SIMTE — 0,3 s devin 2,5 s — iar o
    ureche lenta arata exact ca un microfon stricat. Starea nu are voie sa
    ramana doar in log-ul serverului.
    """
    return _dispozitiv


def eroarea() -> str | None:
    return _eroare


def pregateste() -> None:
    """Compilează motorul, pe primul dispozitiv care merge. A doua oară, nimic.

    Zăvorul e aici fiindcă două cereri sosite în aceeași secundă ar compila
    amândouă pe aceeași placă — adică exact cazul pentru care compilarea e lentă.
    """
    global _motor, _dispozitiv, _eroare
    if _motor is not None:
        return
    with _zavor:
        if _motor is not None:
            return
        try:
            import openvino_genai
            from huggingface_hub import snapshot_download
            cale = snapshot_download(MODEL, local_files_only=True)
        except Exception as e:
            _eroare = f"{type(e).__name__}: {e}"
            print(f"[ureche] modelul nu e pe disc: {_eroare}")
            raise

        motive = []
        for disp in DISPOZITIVE:
            if disp in _arse:
                continue
            try:
                t = time.perf_counter()
                CACHE_OV.mkdir(parents=True, exist_ok=True)
                motor = openvino_genai.WhisperPipeline(cale, disp,
                                                       CACHE_DIR=str(CACHE_OV))
                compilat = time.perf_counter() - t
                # Incalzirea: prima transcriere costa 2,5 s, urmatoarele 0,3 s.
                # Platita aici, pe liniste, prima FRAZA a omului vine rapid. Ce
                # halucineaza modelul pe liniste se arunca — de-aia nu se citeste.
                t = time.perf_counter()
                motor.generate(np.zeros(RATA // 2, dtype=np.float32),
                               language=LIMBA, task="transcribe")
                # Primul apel VAD incarca modelul ONNX: 250 ms. Platit aici, pe
                # liniste, nu pe prima fraza a omului.
                _secunde_de_vorbire(np.zeros(RATA, dtype=np.float32))
            except Exception as e:
                # Se spune pe litere, nu se ascunde intr-un "nu merge
                # microfonul". Cazul asteptat: iGPU-ul luat de alt program.
                motive.append(f"{disp}: {type(e).__name__}: {e}")
                print(f"[ureche] {disp} nu merge — {type(e).__name__}: {e}")
                continue
            _motor, _dispozitiv, _eroare = motor, disp, None
            print(f"[ureche] motor gata: {compilat:.2f} s compilare + "
                  f"{time.perf_counter() - t:.2f} s incalzire, pe {disp}")
            return

        _eroare = " | ".join(motive) or "toate dispozitivele sunt arse"
        print(f"[ureche] motorul NU a pornit: {_eroare}")
        raise RuntimeError(_eroare)


def _cade_pe_rezerva(e: Exception) -> None:
    """Dispozitivul a cazut CU motorul deja compilat: se arde si se ia urmatorul.

    Compilarea reusita nu e o garantie pe toata sesiunea: o placa se poate
    reseta din driver, sau ramane fara memorie cand alt program incarca ceva
    mare pe ea. Fara randul asta, urechea moare pana la repornirea serverului,
    desi rezerva sta compilabila in 1,2 s.

    Ridica mai departe daca nu mai are pe ce sa cada — nu inghite eroarea.
    """
    global _motor, _dispozitiv
    print(f"[ureche] {_dispozitiv} a cazut in timpul lucrului — "
          f"{type(e).__name__}: {e}")
    _arse.add(_dispozitiv)
    _motor, _dispozitiv = None, None
    pregateste()


def _din_wav(octeti: bytes) -> np.ndarray:
    """WAV 16 kHz mono, PCM 16 biți → float32 în [-1, 1]."""
    with wave.open(io.BytesIO(octeti)) as w:
        if w.getsampwidth() != 2:
            raise ValueError(f"astept PCM pe 16 biti, am primit {w.getsampwidth()*8}")
        cadre = w.readframes(w.getnframes())
        semnal = np.frombuffer(cadre, dtype=np.int16).astype(np.float32) / 32768.0
        if w.getnchannels() == 2:
            semnal = semnal.reshape(-1, 2).mean(axis=1)
        if w.getframerate() != RATA:
            raise ValueError(f"astept {RATA} Hz, am primit {w.getframerate()}")
    return semnal


def transcrie(octeti_wav: bytes) -> dict:
    """Textul rostirii, plus cât a durat. Blocant — se cheamă într-un fir."""
    r = _transcrie(octeti_wav)
    _noteaza(r)
    return r


def _transcrie(octeti_wav: bytes) -> dict:
    semnal = _din_wav(octeti_wav)
    durata = round(len(semnal) / RATA, 2)

    # A DOUA PLASA IMPOTRIVA LINISTII. Prima e in worklet, pe ferestre de 8 ms.
    # Asta prinde cazul patologic: liniste curata ajunsa aici dintr-o greseala.
    # Nu e teorie — probat pe masina asta, 24 august: trei secunde de tacere
    # digitala au produs „Sa va multumim pentru vizionare!". Un model care nu
    # poate spune „n-am auzit nimic" va spune altceva, cu aceeasi siguranta.
    rms = float(np.sqrt((semnal * semnal).mean())) if len(semnal) else 0.0
    if rms < 0.001:
        return {"text": "", "secunde": 0.0, "durata_audio": durata,
                "vorbire": 0.0, "motiv": "liniste"}

    # Poarta sta INAINTEA motorului, nu dupa: o rostire fara vorbire nu atinge
    # placa grafica deloc. Costa 5 ms si scuteste 300.
    pregateste()
    vorbire = _secunde_de_vorbire(semnal)
    if vorbire < PRAG_VORBIRE:
        return {"text": "", "secunde": 0.0, "durata_audio": durata,
                "vorbire": round(vorbire, 2), "motiv": "fara vorbire"}

    t = time.perf_counter()
    try:
        rezultat = _motor.generate(semnal, language=LIMBA, task="transcribe",
                                   initial_prompt=CONTEXT)
    except Exception as e:
        _cade_pe_rezerva(e)  # ridica daca nu mai e nimic sub el
        rezultat = _motor.generate(semnal, language=LIMBA, task="transcribe",
                                   initial_prompt=CONTEXT)
    text = str(rezultat).strip()

    # Coada de subtitrare se taie INAINTEA celorlalte doua reguli: ele judeca
    # textul care chiar pleaca mai departe. Un outro lipit ar strica si numarul
    # de cuvinte din care iese ritmul.
    text, taiat = _fara_coada(text)

    raspuns = {
        "text": text,
        "secunde": round(time.perf_counter() - t, 2),
        "durata_audio": durata,
        "vorbire": round(vorbire, 2),
    }
    if taiat:
        raspuns["taiat"] = taiat

    litera = _straina(text)
    cuvinte = len(text.split())
    ritm = cuvinte / vorbire if vorbire else 0.0
    if litera:
        raspuns.update(text="", motiv=f"alta limba ({litera})", refuzat=text)
    elif ritm > PRAG_RITM:
        raspuns.update(text="", motiv=f"ritm {ritm:.1f} cuv/s", refuzat=text)
    return raspuns
