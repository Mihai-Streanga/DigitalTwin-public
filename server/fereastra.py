"""Fereastra proprie a lui Mih.AI, vazuta din server.

DE CE EXISTA FISIERUL ASTA. Pagina porneste pe tot ecranul, fara bara de titlu
(`porneste.vbs`), deci nu are butonul de minimizare. ESC trebuie sa o bage in
bara. O pagina nu se poate minimiza singura: `window.minimize` nu exista
si nici nu va exista — ar insemna ca orice site iti poate muta ferestrele. Deci
gestul il face serverul, care e local si e al nostru.

CE MINIMIZEAZA, EXACT. Numai ferestre care trec DOUA site: clasa
`Chrome_WidgetWin_1` (Edge si Chrome) SI titlul care contine „Mih.AI". Filtrul
dublu nu e prudenta de prisos: VS Code are proiectul deschis, deci are „Mih.AI"
in titlu, iar pe titlu singur ESC ar minimiza editorul autorului. VS Code are
alta clasa de fereastra.

NU RIDICA NICIODATA fereastra inapoi si nu o inchide. Un server local care poate
scoate ferestre in fata e o unealta de furat atentia; inapoi se vine cu un clic
in bara, adica cu mana omului.
"""

import ctypes
import sys
from ctypes import wintypes

SW_MINIMIZE = 6

# Fereastra de dictare a autorului: Iris, alt program, o ferestruica Tk de
# 200x278, pornita cu „mereu deasupra". Cand pagina Mih.AI ia focus, Iris ajunge
# dedesubt si nu mai ai pe ce apasa ca sa transmiti dictarea. `ridica_dictarea()`
# il pune la loc deasupra, FARA sa-i dea focus.
#
# Codul de aici nu citeste, nu scrie, nu porneste si nu opreste Iris. Tot ce
# face e sa ceara Windows-ului sa reaseze o fereastra care deja exista si care
# e deja topmost.
DICTARE = "Iris"

HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010

# Edge si Chrome folosesc aceeasi clasa de fereastra de nivel inalt, si in modul
# `--app`, si normal. Firefox („MozillaWindowClass") ar intra aici daca ar fi
# vreodata browserul de pornire.
CLASE = {"Chrome_WidgetWin_1"}


def _pe_windows() -> bool:
    return sys.platform == "win32"


def _user32():
    """user32 CU TIPURI DECLARATE.

    Fara `argtypes`, ctypes trece handle-urile ca int de 32 de biti, iar pe
    Windows pe 64 de biti unele se taie la jumatate. Efectul e insidios: pe
    handle-uri mici merge, pe cele mari `SetWindowPos` intoarce eroarea 1400
    (fereastra inexistenta) fara sa arunce nimic. S-a lovit pe 25 august.
    """
    u = ctypes.WinDLL("user32", use_last_error=True)
    u.IsWindowVisible.argtypes = [wintypes.HWND]
    u.IsWindowVisible.restype = wintypes.BOOL
    u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    u.ShowWindow.restype = wintypes.BOOL
    u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                               ctypes.c_int, ctypes.c_int, ctypes.c_int,
                               ctypes.c_uint]
    u.SetWindowPos.restype = wintypes.BOOL
    u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    return u


def _ferestre(potrivire) -> list[int]:
    """Ferestrele vizibile pentru care `potrivire(titlu, clasa)` spune da."""
    user32 = _user32()
    tampon = ctypes.create_unicode_buffer(512)
    gasite: list[int] = []

    def _text(hwnd, functie) -> str:
        functie(hwnd, tampon, len(tampon))
        return tampon.value

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def la_fiecare(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            titlu = _text(hwnd, user32.GetWindowTextW)
            clasa = _text(hwnd, user32.GetClassNameW)
            if titlu and potrivire(titlu, clasa):
                gasite.append(hwnd)
        return True

    user32.EnumWindows(la_fiecare, 0)
    return gasite


def ridica_dictarea(titlu: str = DICTARE) -> int:
    """Pune fereastra de dictare inapoi deasupra. Intoarce cate a gasit.

    `SWP_NOACTIVATE` e esential: fereastra urca in fata, dar focusul ramane in
    campul in care scrii. Fara el, fiecare clic in caseta ti-ar muta cursorul in
    alta aplicatie — adica fix pe dos.

    Titlul se compara EXACT, nu „contine": „Iris" ca subsir ar prinde si un
    document deschis cu numele asta, si i-ar schimba altcuiva ferestrele.
    """
    if not _pe_windows():
        return 0
    user32 = _user32()
    gasite = _ferestre(lambda t, _c: t.strip().lower() == titlu.strip().lower())
    for hwnd in gasite:
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    return len(gasite)


def minimizeaza(titlu_contine: str = "Mih.AI") -> int:
    """Baga in bara ferestrele Mih.AI. Intoarce cate a gasit.

    Zero nu e eroare: inseamna ca pagina e deschisa intr-un tab normal, sau ca
    fereastra are alt titlu. Cine cheama decide ce face cu cifra.
    """
    if not _pe_windows():
        return 0
    user32 = _user32()
    gasite = _ferestre(
        lambda t, c: c in CLASE and titlu_contine.lower() in t.lower())
    for hwnd in gasite:
        user32.ShowWindow(hwnd, SW_MINIMIZE)
    return len(gasite)
