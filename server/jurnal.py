"""Conversatiile, ca text plat in `date/conversatii/`.

DE CE SE SCRIE DUPA FIECARE SCHIMB, nu la inchiderea conversatiei:

  Fiindca nu exista inchidere. Serverul se reporneste deliberat intre
  conversatii, iar o pagina de browser se inchide fara sa
  anunte pe nimeni. Orice format care are nevoie de un moment de final —
  un JSON valid, un array inchis — pierde ultima conversatie exact cand conteaza.
  De-aia: un fisier Markdown, deschis la prima replica, crescut prin adaugare.

DE CE MARKDOWN SI NU JSON: criteriul e "zece fisiere lizibile cu ochiul liber".
Un JSON cu `\\n` in el nu e lizibil cu ochiul liber.

NUMELE fisierului e si id-ul conversatiei: `2026-08-24_141203`. Un id opac ar fi
cerut un tabel de corespondenta — adica stare ascunsa, pe care proiectul o
evita.
"""

import re
from datetime import datetime
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
FOLDER = RADACINA / "date" / "conversatii"

# Id-ul vine de la browser inapoi la server, deci se verifica inainte sa atinga
# calea. Fara randul asta, un id de forma `../../server/app` scrie unde nu trebuie.
FORMA_ID = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{6}$")


def id_nou() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def valid(id_conv: str) -> bool:
    return bool(FORMA_ID.match(id_conv or ""))


def _fisierul(id_conv: str) -> Path:
    if not valid(id_conv):
        raise ValueError(f"id de conversatie invalid: {id_conv!r}")
    return FOLDER / f"{id_conv}.md"


def scrie_schimbul(id_conv: str, intrebare: str, raspuns: str,
                   model: str, versiune_prompt: str) -> Path:
    """Adauga un schimb la conversatie. Creeaza fisierul si antetul la primul."""
    f = _fisierul(id_conv)
    FOLDER.mkdir(parents=True, exist_ok=True)

    bucati = []
    if not f.exists():
        bucati.append(
            f"# Conversatie {id_conv}\n\n"
            f"*{model} · prompt: {versiune_prompt}*\n"
        )
    ora = datetime.now().strftime("%H:%M:%S")
    bucati.append(f"\n## Ana · {ora}\n\n{intrebare.strip()}\n")
    bucati.append(f"\n## Mih.AI\n\n{raspuns.strip()}\n")

    with f.open("a", encoding="utf-8") as fout:
        fout.write("".join(bucati))
    return f


def cate_conversatii() -> int:
    if not FOLDER.is_dir():
        return 0
    return len(list(FOLDER.glob("*.md")))
