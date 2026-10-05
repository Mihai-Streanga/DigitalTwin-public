"""Toate probele mecanice, cu o comandă: `py tests/ruleaza.py`.

Ce se verifică mecanic: costul,
contractul HTTP, pornirea, transcrierea. Nimic de aici nu cheamă API-ul plătit.

Fără pytest, deliberat: s-ar instala în Python-ul global, comun cu JA.S.Mine.

Ce nu acoperă: calitatea transcrierii pe vocea autorului (corpusul lipsește),
efectul rutelor `/api/fereastra/*`, ramura plătită a lui `/api/mesaj`. „Toate OK”
înseamnă că plasa asta n-a prins nimic.

Cod de ieșire: 0 dacă nu cade nimic, 1 altfel.
"""
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import proba_cost      # noqa: E402
import proba_http      # noqa: E402
import proba_pornire   # noqa: E402


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.perf_counter()
    cazute = sarite = trecute = 0
    for modul in (proba_cost, proba_http, proba_pornire):
        try:
            rezultate = modul.probe()
        except Exception:
            rezultate = [(modul.__name__, False, traceback.format_exc(limit=3))]
        for nume, ok, detaliu in rezultate:
            semn = "SARIT" if ok is None else ("OK  " if ok else "CADE")
            print(f"{semn}  {nume}" + (f" — {detaliu}" if detaliu != "" else ""))
            if ok is None:
                sarite += 1
            elif ok:
                trecute += 1
            else:
                cazute += 1
    print(f"\n{trecute} trecute, {cazute} căzute, {sarite} sărite — "
          f"{time.perf_counter() - t0:.1f} s")
    return 1 if cazute else 0


if __name__ == "__main__":
    sys.exit(main())
