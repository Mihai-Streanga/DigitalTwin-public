"""Aduce vocea pe mașină. Se rulează o dată, la instalare sau la restaurare.

DE CE EXISTA FISIERUL ASTA: modelele nu intră în git (`.gitignore`, rândul
`modele/`), deci după o restaurare din depozit `mih.AI` rămâne mut, cu o
eroare abia la primul clic pe „ascultă". Ce nu e versionat dispare
tăcut. Aici, măcar, se aduce înapoi cu o comandă.

CE ADUCE, toate gratuite:
  1. vocea numită în `server/voce.py` (`ro_RO-liana-high`, 114 MB),
     licență CC-BY-NC-4.0 — se potrivește cu „proiect personal"; dacă proiectul
     ajunge comercial, vocea se schimbă;
  2. dicționarul espeak peticit al Lianei (`ro_dict`, 200+ împrumuturi
     englezești respelling-uite), pus într-o COPIE LOCALA a datelor espeak;
  3. `espeak-ng.dll` (410 KB), scos din wheel-ul `espeakng-loader` de pe PyPI —
     fonemizatorul de rezervă. Motivul e în `server/espeak_ctypes.py`: Smart App
     Control blochează `espeakbridge.pyd` din piper. **Se descarcă, nu se
     instalează**: un `pip install` în Python-ul global e văzut și de JA.S.Mine.

DE CE O COPIE, si nu inlocuirea in site-packages: `espeak-ng-data` din Python-ul
global e văzut și de JA.S.Mine. Un fișier schimbat acolo i-ar schimba tăcut
pronunția. Copia locală costă 19 MB și nu atinge pe nimeni.

    py scripts\\adu-vocea.py
"""

import shutil
import sys
from pathlib import Path

DEPOZIT = "eduardem/piper-liana-romanian"
RADACINA = Path(__file__).resolve().parent.parent
MODELE = RADACINA / "modele" / "piper"
DATE = RADACINA / "modele" / "espeak-ng-data"
DLL = RADACINA / "modele" / "espeak-ng" / "espeak-ng.dll"
# Versiune fixă: e cea probată că trece prin Smart App Control. Alt wheel
# înseamnă alt hash, deci altă reputație, deci alt verdict al politicii.
WHEEL_ESPEAK = "espeakng-loader==0.2.4"


def voce_ceruta() -> str:
    """Numele vocii se citește din cod, nu se repetă aici."""
    sys.path.insert(0, str(RADACINA))
    from server.voce import VOCE
    return VOCE


def adu(cale_depozit: str, tinta: Path) -> None:
    from huggingface_hub import hf_hub_download
    tinta.parent.mkdir(parents=True, exist_ok=True)
    sursa = hf_hub_download(DEPOZIT, cale_depozit)
    shutil.copyfile(sursa, tinta)
    print(f"  {tinta.name}  {tinta.stat().st_size / 1e6:.1f} MB")


def adu_dll_espeak() -> None:
    """Scoate `espeak-ng.dll` din wheel-ul de pe PyPI, fără să instaleze nimic."""
    if DLL.exists():
        print(f"  {DLL.name}  era deja acolo")
        return
    import subprocess
    import tempfile
    import zipfile
    DLL.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        subprocess.run([sys.executable, "-m", "pip", "download", WHEEL_ESPEAK,
                        "--dest", temp, "--no-deps", "-q"], check=True)
        wheel = next(Path(temp).glob("*.whl"))
        with zipfile.ZipFile(wheel) as z:
            nume = next(n for n in z.namelist() if n.endswith("espeak-ng.dll"))
            DLL.write_bytes(z.read(nume))
    print(f"  {DLL.name}  {DLL.stat().st_size / 1e3:.0f} KB  (din {wheel.name})")


def main() -> None:
    # Prin pipe, consola Windows e cp1252 si crapa la primul „ă" (4 octombrie 2026).
    sys.stdout.reconfigure(encoding="utf-8")
    voce = voce_ceruta()
    scurt = voce.replace("ro_RO-", "")     # „ro_RO-liana-high" -> „liana-high"
    print(f"vocea: {voce}")
    adu(f"voices/{scurt}/{voce}.onnx", MODELE / f"{voce}.onnx")
    adu(f"voices/{scurt}/{voce}.onnx.json", MODELE / f"{voce}.onnx.json")
    adu("espeak/ro_dict", MODELE / "ro_dict")
    adu("espeak/ro_extra", MODELE / "ro_extra")   # sursa, pentru cine vrea s-o citească

    print("fonemizatorul de rezervă:")
    adu_dll_espeak()

    print("dicționarul espeak, în copie locală:")
    from piper.phonemize_espeak import ESPEAK_DATA_DIR
    if not DATE.exists():
        shutil.copytree(ESPEAK_DATA_DIR, DATE)
    shutil.copyfile(MODELE / "ro_dict", DATE / "ro_dict")
    print(f"  {DATE}  ({sum(f.stat().st_size for f in DATE.rglob('*') if f.is_file()) / 1e6:.0f} MB)")

    # Proba, nu declarația: dacă dicționarul peticit n-a ajuns unde trebuie,
    # `weekend` iese „wˌeekˈend" în loc de „wˈikend". Proba trece prin același
    # ocol ca serverul, altfel crapă chiar ea pe bridge-ul blocat.
    from server.voce import _ocoleste_espeakbridge_blocat
    _ocoleste_espeakbridge_blocat()
    from piper.phonemize_espeak import EspeakPhonemizer
    foneme = "".join(EspeakPhonemizer(DATE).phonemize("ro", "weekend")[0])
    print(f"probă: weekend -> {foneme}  "
          f"{'(bun)' if foneme == 'wˈikend' else '(DICTIONARUL NU E CEL PETICIT)'}")


if __name__ == "__main__":
    main()
