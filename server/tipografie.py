"""Ghilimelele, aduse la convenția casei de cod, nu cerute în prompt.

CARE E CONVENTIA CASEI, masurata inainte de a scrie fisierul asta: `„text"` —
deschidere românească, închidere dreaptă. Nu e ce scrie în manual (acolo e
`„text”`), dar e ce scrie peste tot aici: **145 de închideri în documentele
proiectului, în dosarul de probe și în tot promptul, toate drepte, niciuna românească** — inclusiv exemplul din fișa de stil, care cerea
ghilimele românești scriind chiar `„așa"`.

CE A GASIT PRIMA EVALUARE A REPLICILOR, si ce a gresit prima citire: Twin-ul deschide
corect de fiecare dată — zero deschideri drepte în opt replici. La închidere a
folosit `”` în primele două replici și `"` în ultimele patru. Prima citire a
numit asta „regula se erodează". Măsurătoarea pe documentele proiectului a
întors verdictul: replicile de la urmă respectau convenția casei, cele de la
început se abăteau de la ea. **Defectul era în citire, nu în replici.**

DECI CE FACE CODUL: normalizează în ambele sensuri, la `„` + `"`. Ghilimeaua
dreaptă la început de citat devine `„`; `”` și `“` devin ce trebuie. Ce era deja
bine trece neatins. Costul e plătit o dată, aici, nu la fiecare replică într-un
rând de prompt — regula proiectului: funcțiile sunt cod determinist.

CE NU ATINGE: ce stă între accente grave. Un `print("x")` scris de Twin trebuie
să rămână cod care rulează, nu proză cu ghilimele frumoase. Trei accente grave
la rând comută starea de trei ori, deci un bloc întreg se rezolvă cu aceeași
regulă simplă ca un fragment din rând.
"""

DESCHIDERE = "„"
INCHIDERE = '"'          # dreaptă, ca în tot restul depozitului
_DE_INLOCUIT = ('"', "“", "”")


class Ghilimele:
    """Automat cu stare, ca să treacă peste bucățile de flux.

    Ghilimeaua de închidere ajunge în altă bucată decât cea de deschidere —
    de-aia starea nu poate sta într-o funcție pură peste un text întreg.
    """

    def __init__(self) -> None:
        self.deschis = False   # am o ghilimea deschisă, neînchisă
        self.in_cod = False    # sunt între accente grave

    def treci(self, bucata: str) -> str:
        iesire = []
        for ch in bucata:
            if ch == "`":
                self.in_cod = not self.in_cod
                iesire.append(ch)
            elif self.in_cod:
                iesire.append(ch)
            elif ch == DESCHIDERE:
                self.deschis = True
                iesire.append(ch)
            elif ch in _DE_INLOCUIT:
                iesire.append(INCHIDERE if self.deschis else DESCHIDERE)
                self.deschis = not self.deschis
            else:
                iesire.append(ch)
        return "".join(iesire)


def indreapta(text: str) -> str:
    """Varianta pentru un text întreg, pentru probe și pentru ce nu e flux."""
    return Ghilimele().treci(text)
