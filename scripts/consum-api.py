"""Cat a cheltuit proiectul din bugetul de API, luna asta.

DE CE EXISTA, mai ales cand bugetul e comun cu alt proiect:

  Tocmai fiindca e comun. Un buget impartit fara contor pe program da un semnal
  ilizibil: vezi ca s-a depasit, nu vezi cine. Iar regula spune ca depasirea de
  ritm e semnal de CONFIGURARE gresita, nu motiv de suplimentare — deci trebuie
  sa stii care din doua s-a stricat.

  O unealta care ruleaza si da o cifra incompleta e mai rea decat una care
  lipseste — de-aia contorul citeste doar registrul scris de server.

DE UNDE VINE CIFRA: din `date/consum/AAAA-LL.jsonl`, scris de server la FIECARE
raspuns al API-ului, cu `usage` copiat ca atare din raspuns. Nu e estimare din
octeti si nu e citita din consola Anthropic — e ce a raportat chiar API-ul.

Un rand din registru:

  {"ora": "2026-08-23T14:02:11+03:00", "model": "claude-sonnet-5",
   "unde": "pagina", "input": 1234, "cache_write": 0, "cache_read": 8000,
   "output": 512, "cache_ttl": "5m"}

`unde` spune care parte a programului a cheltuit (pagina, unealta, autopsie),
ca sa se vada nu doar cat, ci pe ce.

Folosire:
    py scripts/consum-api.py            (luna curenta)
    py scripts/consum-api.py 2026-09    (o luna anume)
    py scripts/consum-api.py «cale».jsonl   (un registru anume — `tests/`)

Cod de iesire: 0 bine, 2 model fara pret, 3 randuri stricate.
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
REGISTRU = RADACINA / "date" / "consum"
NUME = "Mih.AI"
BUGET = "de completat: bugetul tău lunar"

# Preturi in dolari pe MILION de tokeni de intrare/iesire.
#
# CITITE, NU AMINTITE — reverificate 31 august 2026 si reconfirmate pe 3
# septembrie la `platform.claude.com/docs/en/about-claude/pricing`, adica dupa
# data la care scumpirea anuntata ar fi trebuit sa intre. Tabelul e neschimbat. Se reverifica inainte de
# orice decizie care costa bani; un pret vechi de trei luni e o presupunere.
#
# SONNET 5: pretul de introducere 2 / 10 A DEVENIT PRETUL STANDARD. Cresterea la
# 3 / 15, anuntata pentru 1 septembrie 2026, a fost anulata — scrie negru pe alb
# in nota de pe pagina de preturi, citita pe 31 august. Mecanismul `introducere`
# ramane in cod, nefolosit: e ieftin si urmatoarea oferta pe termen se scrie
# intr-un rand. Preturile de august se calculeaza la fel ca inainte, 2 / 10,
# deci niciun raport vechi nu se rescrie.
PRETURI = {
    "claude-sonnet-5": {"intrare": 2.00, "iesire": 10.00},
    "claude-opus-5": {"intrare": 5.00, "iesire": 25.00},
    "claude-opus-4-8": {"intrare": 5.00, "iesire": 25.00},
    "claude-fable-5": {"intrare": 10.00, "iesire": 50.00},
    "claude-haiku-4-5": {"intrare": 1.00, "iesire": 5.00},
}

# Multiplicatorii cache-ului, fata de pretul de INTRARE al modelului.
# Aceeasi data, aceeasi sursa. Citirea din cache costa 10% — de-aia un prefix
# stabil e ieftin de tinut, dar NU gratis: se plateste la fiecare replica.
CACHE_SCRIS = {"5m": 1.25, "1h": 2.00}
CACHE_CITIT = 0.10


def pretul(model: str, cand: date | None) -> tuple[float, float] | None:
    p = PRETURI.get(model)
    if p is None:
        for nume, val in PRETURI.items():
            if model.startswith(nume):
                p = val
                break
    if p is None:
        return None
    intro = p.get("introducere")
    if intro and cand and cand <= intro[0]:
        return intro[1], intro[2]
    return p["intrare"], p["iesire"]


def ziua(rand: dict) -> date | None:
    try:
        return datetime.fromisoformat(rand["ora"]).date()
    except Exception:
        return None


def costul(rand: dict) -> tuple[float, bool]:
    """Costul unui apel, in dolari. Al doilea intors: s-a stiut pretul?"""
    p = pretul(rand.get("model", ""), ziua(rand))
    if p is None:
        return 0.0, False
    intrare, iesire = p
    scris = CACHE_SCRIS.get(rand.get("cache_ttl", "5m"), 1.25)
    total = (
        rand.get("input", 0) * intrare
        + rand.get("cache_write", 0) * intrare * scris
        + rand.get("cache_read", 0) * intrare * CACHE_CITIT
        + rand.get("output", 0) * iesire
    )
    return total / 1_000_000, True


def citeste(fisier: Path) -> dict:
    """Un registru intreg: cost, apeluri, pe model, pe `unde`, ce nu s-a putut citi.

    Calea vine ca parametru, nu din luna curenta: `/api/stare` si `tests/` cheama
    aceeasi functie, pe registre diferite. Un rand stricat NU se sare in tacere —
    intra in `stricate`, cu numarul lui, ca cifra mica sa nu para doar mica.
    """
    r = {"cost": 0.0, "apeluri": 0, "pe_model": {}, "pe_unde": {},
         "necunoscute": set(), "stricate": []}
    for n, linie in enumerate(fisier.read_text(encoding="utf-8").splitlines(), 1):
        linie = linie.strip()
        if not linie:
            continue
        try:
            rand = json.loads(linie)
            if not isinstance(rand, dict):
                raise ValueError("nu e obiect")
        except Exception:
            r["stricate"].append(n)
            continue
        r["apeluri"] += 1
        model = rand.get("model", "?")
        cost, stiut = costul(rand)
        if not stiut:
            r["necunoscute"].add(model)
        r["cost"] += cost
        m = r["pe_model"].setdefault(model, {"apeluri": 0, "tok": 0, "cost": 0.0})
        m["apeluri"] += 1
        m["tok"] += (rand.get("input", 0) + rand.get("cache_write", 0)
                     + rand.get("cache_read", 0) + rand.get("output", 0))
        m["cost"] += cost
        unde = rand.get("unde", "?")
        r["pe_unde"][unde] = r["pe_unde"].get(unde, 0.0) + cost
    return r


def mii(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    arg = sys.argv[1] if len(sys.argv) > 1 else date.today().strftime("%Y-%m")
    # O luna (`2026-09`) sau o cale de registru — a doua e pentru `tests/`.
    if arg.endswith(".jsonl"):
        fisier, luna = Path(arg), Path(arg).stem
        print(f"consum {NUME} - registru: {arg}")
    else:
        luna = arg
        fisier = REGISTRU / f"{luna}.jsonl"
        print(f"consum {NUME} - {luna}   (registru: date/consum/{luna}.jsonl)")

    if not fisier.exists():
        print("  0 apeluri. Registrul nu exista inca.")
        return 0

    r = citeste(fisier)
    pe_model, pe_unde = r["pe_model"], r["pe_unde"]
    total_cost, apeluri = r["cost"], r["apeluri"]
    necunoscute, stricate = r["necunoscute"], r["stricate"]

    if stricate:
        print(f"  RANDURI STRICATE: {len(stricate)} — r." + ", r.".join(map(str, stricate)))
        print("  N-au intrat in total. Cifra de jos e mai mica decat cheltuiala reala.")
        print()

    if apeluri == 0:
        print("  0 apeluri. Registrul e gol.")
        return 3 if stricate else 0

    for model, m in sorted(pe_model.items(), key=lambda x: -x[1]["cost"]):
        print(f"  {m['cost']:8.4f} $  {m['apeluri']:>4} apeluri  "
              f"{mii(m['tok']):>12} tok  {model}")
    if len(pe_unde) > 1:
        print()
        for unde, c in sorted(pe_unde.items(), key=lambda x: -x[1]):
            print(f"  {c:8.4f} $  {unde}")
    print()
    print(f"  {total_cost:8.4f} $  TOTAL {NUME}, {apeluri} apeluri")
    print()
    print(f"  Buget: {BUGET}.")
    print(f"  Cifra de sus e partea lui {NUME}, in dolari. Cursul nu se inventeaza")
    print("  aici; se pune cand se face analiza de costuri.")

    if necunoscute:
        print()
        print("  PRET NECUNOSCUT pentru: " + ", ".join(sorted(necunoscute)))
        print("  Apelurile alea au intrat cu 0 $. Adauga modelul in PRETURI.")
        return 2
    return 3 if stricate else 0


if __name__ == "__main__":
    sys.exit(main())
