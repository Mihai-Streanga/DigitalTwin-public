"""Înlocuitor pentru `piper.espeakbridge`, peste `espeak-ng.dll`, prin ctypes.

DE CE EXISTA FISIERUL ASTA: pe 2 septembrie 2026 vocea a murit cu
`ImportError: DLL load failed while importing espeakbridge: An Application
Control policy has blocked this file`. **Smart App Control** — pornit în mod
enforcement pe mașina asta — refuză `espeakbridge.pyd` din `piper-tts`, fiindcă
e nesemnat și n-are reputație în cloud-ul Microsoft. Jurnalul CodeIntegrity
scrie evenimentele 3033/3077/3118 la fiecare încercare.

NU E UN DEFECT AL PIPER-ULUI si nu se repara cu alta voce: blocajul e pe
binarul însuși. Restul stivei native trece — `onnxruntime` fiindcă e semnat,
`ctranslate2` și `av` fiindcă au căpătat reputație (`av\\audio\\frame.pyd` a fost
și el blocat pe 17 august, iar azi se încarcă). `espeakbridge` e prea rar
descărcat ca să ajungă acolo, deci așteptarea nu e un plan.

DE CE NU SE OPRESTE SMART APP CONTROL: oprirea e ireversibilă — repornirea lui
cere reinstalarea Windows-ului. Un strat de protecție pe toată mașina nu se dă
jos pentru un DLL de 400 KB.

CE FACE INLOCUITORUL: `espeak-ng.dll` din pachetul `espeakng-loader` e alt binar,
cu alt hash, și **trece** prin politică — verificat cu `ctypes.CDLL`. Peste el
stau exact cele trei funcții ale bridge-ului, cu aceleași semnături, iar
`voce.py` îl pune în `sys.modules` înainte de importul piper. Datele espeak
rămân aceleași: dicționarul peticit al Lianei din `modele/espeak-ng-data`.

CE SE PIERDE: `espeak_ng_TextToPhonemesWithTerminator` nu există în espeak-ng
oficial — e din fork-ul rhasspy pe care îl împachetează piper. Deci tăierea în
clauze și terminatorul se fac aici, în Python, pe punctuație. Măsurat pe
cuvintele din `voce.py`, fonemele ies aceleași:

    docker   -> dokkˈer      (identic)
    merge    -> mˈerdʒe      (identic)
    endpoint -> ˌendpoˈint   (identic)
    weekend  -> wˈikend      (dicționarul Lianei, citit corect)
    branch   -> brˈank       (era bɾˈank: alt „r", altă versiune espeak-ng)
"""

import ctypes
import re
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
CALE_DLL = RADACINA / "modele" / "espeak-ng" / "espeak-ng.dll"

_AUDIO_OUTPUT_SYNCHRONOUS = 2
_INITIALIZE_DONT_EXIT = 0x8000     # altfel espeak-ng cheamă exit() peste server
_CHARS_UTF8 = 1
_PHONEMES_IPA = 0x02

# Punctuația pe care espeak-ng o tratează ca sfârșit de clauză. Se păstrează în
# rezultat: piper o lipește la foneme, iar modelul o are în vocabular.
_CLAUZE = re.compile(r"([.?!,:;])")
_SFARSIT_DE_PROPOZITIE = (".", "?", "!")

_dll = None


def _incarca():
    if not CALE_DLL.exists():
        raise RuntimeError(f"lipsește {CALE_DLL} — se aduce cu: py scripts\\adu-vocea.py")
    d = ctypes.CDLL(str(CALE_DLL))
    d.espeak_Initialize.restype = ctypes.c_int
    d.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    d.espeak_SetVoiceByName.restype = ctypes.c_int
    d.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
    d.espeak_TextToPhonemes.restype = ctypes.c_char_p
    d.espeak_TextToPhonemes.argtypes = [ctypes.POINTER(ctypes.c_void_p),
                                        ctypes.c_int, ctypes.c_int]
    return d


def initialize(data_dir: str) -> None:
    """Pornește espeak-ng pe datele date.

    ATENTIE LA CALE: `espeak_Initialize` primește **părintele** folderului
    `espeak-ng-data`, nu folderul. Dat greșit, întoarce -1 și pronunția cade
    tăcut pe engleză.
    """
    global _dll
    if _dll is None:
        _dll = _incarca()
    parinte = str(Path(data_dir).resolve().parent)
    if _dll.espeak_Initialize(_AUDIO_OUTPUT_SYNCHRONOUS, 0,
                              parinte.encode("utf-8"), _INITIALIZE_DONT_EXIT) < 0:
        raise RuntimeError(f"espeak-ng nu a găsit datele în {parinte}")


def set_voice(voice: str) -> None:
    if _dll.espeak_SetVoiceByName(voice.encode("utf-8")) != 0:
        raise RuntimeError(f"espeak-ng nu are vocea {voice}")


def _foneme(bucata: str) -> str:
    """Un apel consumă textul clauză cu clauză, mutând pointerul până la capăt."""
    tampon = ctypes.create_string_buffer(bucata.encode("utf-8"))
    p = ctypes.cast(tampon, ctypes.c_void_p)
    parti = []
    while p and p.value:
        r = _dll.espeak_TextToPhonemes(ctypes.byref(p), _CHARS_UTF8, _PHONEMES_IPA)
        if r:
            parti.append(r.decode("utf-8"))
    return " ".join(parti)


def get_phonemes(text: str) -> list[tuple[str, str, bool]]:
    """Text → [(foneme, terminator, sfârșit_de_propoziție)], ca bridge-ul original."""
    bucati = _CLAUZE.split(text)
    iesire: list[tuple[str, str, bool]] = []
    for i in range(0, len(bucati), 2):
        continut = bucati[i].strip()
        terminator = bucati[i + 1] if i + 1 < len(bucati) else ""
        if not continut:
            continue
        foneme = _foneme(continut)
        if not foneme:
            continue
        # Fără terminator = capătul textului: tot sfârșit de propoziție e.
        iesire.append((foneme, terminator,
                       terminator in _SFARSIT_DE_PROPOZITIE or not terminator))
    return iesire
