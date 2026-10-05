"""Costul: recalcul independent, nu valori scrise de mână.

`consum-api.costul()` adună pe rânduri. Proba de aici adună întâi tokenii pe
categorii — model, durata cache-ului — și înmulțește o singură dată, la sfârșit.
Două drumuri prin aceleași cifre; dacă formula de pe rând greșește un
multiplicator sau o categorie, totalurile se despart.

Prețurile sunt date, nu formulă: se iau din `PRETURI`. Dacă un preț e greșit
față de pagina Anthropic, proba asta nu-l vede — se reverifică cu data lui,
pe pagina de prețuri.
"""
import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

R = Path(__file__).resolve().parent.parent
STRICAT = R / "tests" / "date" / "consum-stricat.jsonl"


def _modul():
    spec = importlib.util.spec_from_file_location("consum_api", R / "scripts" / "consum-api.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def recalcul(fisier: Path, preturi: dict, scris: dict, citit: float) -> float:
    """Pe categorii, apoi înmulțit. Criteriile vin ca parametri (regula de izolare)."""
    sume: dict[tuple, dict] = {}
    for linie in fisier.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(linie)
        except ValueError:
            continue
        if not isinstance(r, dict):
            continue
        model = next((n for n in preturi if r.get("model", "").startswith(n)), None)
        if model is None:
            continue
        s = sume.setdefault((model, r.get("cache_ttl", "5m")),
                            {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0})
        for k in s:
            s[k] += r.get(k, 0)
    total = 0.0
    for (model, ttl), s in sume.items():
        p_in, p_out = preturi[model]["intrare"], preturi[model]["iesire"]
        total += (s["input"] * p_in + s["cache_write"] * p_in * scris.get(ttl, 1.25)
                  + s["cache_read"] * p_in * citit + s["output"] * p_out)
    return total / 1_000_000


def probe():
    m = _modul()
    rez = []

    registre = sorted((R / "date" / "consum").glob("*.jsonl"))
    if not registre:
        rez.append(("cost: registrele reale", None, "date/consum/ lipsește — sărit"))
    for f in registre + [STRICAT]:
        pe_rand = m.citeste(f)["cost"]
        independent = recalcul(f, m.PRETURI, m.CACHE_SCRIS, m.CACHE_CITIT)
        rez.append((f"cost: recalcul {f.name}", abs(pe_rand - independent) < 1e-9,
                    f"pe rânduri {pe_rand:.6f} $, pe categorii {independent:.6f} $"))

    c = m.citeste(STRICAT)
    rez.append(("cost: registrul stricat, citit",
                c["apeluri"] == 3 and c["stricate"] == [2]
                and c["necunoscute"] == {"claude-necunoscut-9"},
                f"apeluri {c['apeluri']}, stricate {c['stricate']}, necunoscute {sorted(c['necunoscute'])}"))

    p = subprocess.run([sys.executable, str(R / "scripts" / "consum-api.py"), str(STRICAT)],
                       capture_output=True, text=True, encoding="utf-8", cwd=R)
    rez.append(("cost: registrul stricat, spus de unealtă",
                p.returncode == 2 and "RANDURI STRICATE: 1" in p.stdout
                and "claude-necunoscut-9" in p.stdout,
                f"cod {p.returncode}"))

    luna = R / "date" / "consum" / f"{date.today():%Y-%m}.jsonl"
    if luna.exists():
        sys.path.insert(0, str(R))
        from server import app
        cost, stricate = app._costul_lunii()
        c = m.citeste(luna)
        rez.append(("cost: /api/stare = consum-api",
                    cost == round(c["cost"], 4) and stricate == len(c["stricate"]),
                    f"server {cost} $, unealta {c['cost']:.4f} $, stricate {stricate}"))
    return rez
