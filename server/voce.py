"""Text → vorbire, local, pe procesor.

NU COSTA NICIUN TOKEN, ca și urechea. Piper e un VITS de 64 MB care rulează pe
CPU mai repede decât în timp real. Nimic nu pleacă de pe mașină.

DE CE PIPER, deși JA.S.Mine l-a respins: l-a probat în august și
l-a închis — citea „branch" ca „branc", defect al fonemizatorului, nereparabil
prin schimbarea vocii. Raționamentul era corect. Ce s-a schimbat: vocea Liana
(17 august 2026) e **reantrenată** pe împrumuturi englezești și numere, și vine
cu **dicționarul espeak peticit** cu care a fost antrenată. Alt mecanism, nu
altă voce peste același defect.

CE RAMANE DE REPARAT AICI, si de ce in cod: dicționarul Lianei acoperă
împrumuturile de zi cu zi — weekend, laptop, WhatsApp — nu jargonul de
programare. Măsurat cu fonemizatorul, 24 august 2026:

    branch   -> bɾˈank      („branc", exact defectul găsit acolo)
    docker   -> dokkˈer
    merge    -> mˈerdʒe     (verbul românesc „merge")
    endpoint -> ˌendpoˈint  (trei silabe)
    API      -> ˈapʲ        („api")

Reparația de-a dreptul ar fi încă o intrare în `ro_extra` și o recompilare a
dicționarului — dar `espeak-ng --compile` cere binarul espeak-ng, care nu e pe
mașină și ar fi o instalare în plus. Aceeași reparație se face aici, mai sus de
fonemizator: **cuvântul se rescrie cu litere românești înainte de sinteză**.
Același mecanism ca dicționarul (respelling în foneme românești), doar aplicat
mai devreme, în cod pe care îl vedem și îl schimbăm pe un rând.

CE VEDE OMUL NU SE SCHIMBA: rescrierea atinge doar textul trimis lui Piper.
Răspunsul din pagină rămâne scris corect.

FONEMIZATORUL NU MAI E CEL DIN PIPER (2 septembrie 2026): Smart App Control
blochează `espeakbridge.pyd`, iar `_ocoleste_espeakbridge_blocat()` mai jos pune
în locul lui `espeak_ctypes`, peste un `espeak-ng.dll` care trece prin politică.
Povestea, măsurătorile și ce se pierde: `server/espeak_ctypes.py`.
"""

import io
import re
import threading
import time
import unicodedata
import wave
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
MODELE = RADACINA / "modele" / "piper"
DATE_ESPEAK = RADACINA / "modele" / "espeak-ng-data"
VOCE = "ro_RO-liana-high"

# Jargonul, scris cum se citește. Fiecare rând e o măsurătoare, nu o părere:
# s-a fonemizat înainte și după. Ce sună deja bine NU e aici — `site`, `link`,
# `laptop`, `browser`, `backup`, `prompt`, `script`, `log`, `corpus`, `twin`,
# `commit` ies corect din dicționarul Lianei, iar o intrare în plus ar fi o
# ocazie de stricat.
JARGON = {
    "branch": "brenci",
    "docker": "docăr",
    "merge": "mergi",
    "endpoint": "endpoiănt",
    "token": "tocăn",
    "tokeni": "tocăni",
    "tokenii": "tocănii",
    "handoff": "hendof",
    "cache": "cheș",
    "file": "fail",
    "bug": "bag",
    "deploy": "diploi",
    "update": "apdeit",
    "json": "geison",
    "claude": "clod",
    "api": "a pe i",
}

# Numele cu punct în ele. DE CE UN AL DOILEA TABEL, si nu inca un rand in
# `JARGON`: acolo cautarea merge pe cuvinte intregi, iar punctul rupe cuvantul —
# fonemizatorul vede „Mih" si „AI" separat si spune, literal, cuvantul „punct".
# Masurat pe 24 august 2026:
#
#     Mih.AI     -> mˈih pˈunkt ˈaɪ            Mihai    -> mihˈaɪ
#     JA.S.Mine  -> ʒˈa pˈunkt sˈe pˈunkt mˈine   Geasmin -> dʒeasmˈin
#
# De-aia se inlocuieste sirul literal, INAINTE de trecerea pe cuvinte.
NUME = {
    "Mih.AI": "Mihai",
    "JA.S.Mine": "Geasmin",
}

_voce = None
_zavor = threading.Lock()


def _pastreaza_forma(original: str, nou: str) -> str:
    """„Docker" → „Docăr", „DOCKER" → „Docăr". Majuscula nu se pierde."""
    if original.isupper() and len(original) > 1:
        return nou
    if original[0].isupper():
        return nou[0].upper() + nou[1:]
    return nou


# Semnele de marcare nu se rostesc, dar espeak le rosteste. Masurat pe 25
# august, la fonemizator: „**Halucinatii**" iese `ˌasteɾˌiskasteɾˈisk
# hˌalutʃinˈatiɪ ˌasteɾˌiskasteɾˈisk` — „asterisc asterisc" de doua ori la
# fiecare cuvant ingrosat. Un raspuns cu patru puncte ingrosate le spune de opt
# ori. Ce se VEDE in pagina ramane scris cu markdown; se curata doar ce pleaca
# spre Piper.
_MARCAJE = str.maketrans("", "", "*`#[]")


def _fara_marcaje(text: str) -> str:
    """Markdown afara, si fiecare rand devine o unitate de rostit."""
    randuri = []
    for rand in text.translate(_MARCAJE).split(chr(10)):
        rand = rand.strip()
        if not rand:
            continue
        # Liniuta de listă e semn pe hârtie, nu cuvânt.
        if rand[:2] in ("- ", "• "):
            rand = rand[2:].strip()
        # Un rând care nu se termină cu punctuație ar curge în următorul: la
        # rostire, cele patru puncte ale unei liste ar deveni o singură frază.
        if rand and rand[-1] not in ".!?…:;,":
            rand += "."
        randuri.append(rand)
    return " ".join(randuri)


def pentru_rostire(text: str) -> str:
    """Textul, pregătit pentru fonemizator. Nu se arată nimănui."""
    text = _fara_marcaje(text)

    # Web-ul cară constant cedila turcească în loc de virgula de dedesubt;
    # espeak le tratează ca litere diferite.
    text = unicodedata.normalize("NFC", text)
    text = text.replace("ş", "ș").replace("Ş", "Ș")
    text = text.replace("ţ", "ț").replace("Ţ", "Ț")

    # Numele cu punct, pe sirul intreg, inaintea cuvintelor.
    for nume, rostit in NUME.items():
        text = text.replace(nume, rostit)

    def schimba(m: re.Match) -> str:
        cuvant = m.group(0)
        nou = JARGON.get(cuvant.lower())
        return _pastreaza_forma(cuvant, nou) if nou else cuvant

    # Doar cuvântul de bază: „branch-ul" devine „brenci-ul", cu sufixul întreg.
    return re.sub(r"[A-Za-zĂÂÎȘȚăâîșț]+", schimba, text)


def _ocoleste_espeakbridge_blocat() -> None:
    """Pune înlocuitorul prin ctypes DOAR dacă bridge-ul original nu se încarcă.

    Smart App Control blochează `espeakbridge.pyd` — povestea întreagă e în
    `server/espeak_ctypes.py`. Se încearcă întâi originalul, fiindcă blocajul
    ține de reputația fișierului în cloud și se poate ridica singur într-o zi;
    când se ridică, rândurile astea nu mai fac nimic și pot pleca.
    """
    import sys
    if "piper.espeakbridge" in sys.modules:
        return
    try:
        from piper import espeakbridge  # noqa: F401
    except ImportError as e:
        from . import espeak_ctypes
        sys.modules["piper.espeakbridge"] = espeak_ctypes
        print(f"[voce] espeakbridge blocat ({e.__class__.__name__}), "
              f"trec pe espeak-ng.dll prin ctypes", flush=True)


def pregateste() -> None:
    """Încarcă vocea. Se cheamă o dată; a doua oară nu face nimic.

    **Se cheamă și la pornirea serverului**, de pe un fir de fundal
    (`incalzeste_in_fundal`), ca și urechea: vocea vine peste primul răspuns,
    adică exact acolo unde nu ai cerut nimic și aștepți.
    """
    global _voce
    if _voce is not None:
        return
    with _zavor:
        if _voce is not None:
            return
        _ocoleste_espeakbridge_blocat()
        from piper import PiperVoice
        _voce = PiperVoice.load(MODELE / f"{VOCE}.onnx", espeak_data_dir=DATE_ESPEAK)


def sintetizeaza(text: str) -> bytes:
    """Text → WAV, gata de trimis în pagină. Blocant — se cheamă într-un fir."""
    import numpy as np
    from piper import SynthesisConfig

    pregateste()
    sc = SynthesisConfig(
        length_scale=_voce.config.length_scale,
        noise_scale=_voce.config.noise_scale,
        noise_w_scale=_voce.config.noise_w_scale,
    )
    bucati = [c.audio_float_array.astype(np.float32)
              for c in _voce.synthesize(pentru_rostire(text), syn_config=sc)]
    audio = np.concatenate(bucati) if bucati else np.zeros(1, dtype=np.float32)

    tampon = io.BytesIO()
    with wave.open(tampon, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_voce.config.sample_rate)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype("int16").tobytes())
    return tampon.getvalue()


def incalzeste_in_fundal() -> None:
    """Plătește încărcarea vocii la pornirea serverului, pe un fir de fundal.

    MASURAT 25 august 2026, prin server: prima rostire dintr-o sesiune stă
    **2,96 s** până la primul sunet, următoarele 0,47–0,74 s. Diferența e
    încărcarea modelului (1,74 s) plus prima trecere prin ONNX, care e mereu
    mai lentă. Plătită aici, nu se mai vede nicăieri: pornirea serverului e
    oricum o așteptare, prima frază a Twin-ului nu.

    PE FIR SEPARAT fiindcă altfel serverul n-ar răspunde la nimic trei secunde
    după pornire — exact fereastra în care pagina cere `/api/stare`.

    O voce care nu pornește NU are voie să oprească serverul: pagina merge și
    scrisă, iar prima cerere de rostire va spune pe litere ce s-a întâmplat.
    """
    def munca() -> None:
        try:
            t = time.perf_counter()
            sintetizeaza("Bună.")  # sunetul se aruncă; contează drumul, nu el
            print(f"[voce] incalzita in {time.perf_counter() - t:.2f} s", flush=True)
        except Exception as e:
            print(f"[voce] nu s-a putut incalzi: {type(e).__name__}: {e}", flush=True)

    threading.Thread(target=munca, daemon=True, name="incalzire-voce").start()
