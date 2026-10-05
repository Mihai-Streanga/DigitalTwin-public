' Porneste Mih.AI pe http://localhost:8100 si deschide fereastra lui.
'
' DE CE .vbs si nu .bat: un .bat lasa o fereastra neagra deschisa cat timp merge
' serverul, iar inchisa din greseala opreste serverul la mijlocul unei
' conversatii. `Run` cu 0 il porneste fara nicio fereastra.
'
' DE CE FARA --reload: uvicorn cu --reload reporneste tacut la fiecare scriere
' in folder. Firul conversatiei sta in memoria procesului — o repornire tacuta
' in timp ce vorbesti sterge conversatia fara sa spuna nimic.
'
' DE CE CHROME IN MOD --app: asa Mih.AI se
' deschide in fereastra lui, pe tot ecranul, fara bara de adrese si fara taburi,
' cu iconita proprie in bara de jos. ESC il baga in bara — tasta e prinsa in
' `pagina.js`, iar minimizarea o face serverul, in `server/fereastra.py`.
'
' DE CE MAXIMIZAT SI NU FULLSCREEN (tot 25 august, dupa ce s-a lovit):
' `--start-fullscreen` acopera TOT, inclusiv ferestrele mici care stau „mereu
' deasupra". Iris, unealta de dictare a autorului, e exact asta: 200x278 pixeli,
' topmost. Sub o fereastra fullscreen dispare, si nu mai ai pe ce apasa ca sa
' transmiti dictarea. Maximizat, fereastra tine tot ecranul mai putin bara de
' jos, iar Iris ramane deasupra — masurat cu clic real, nu presupus.
' Fullscreen adevarat se ia oricand cu F11, cat timp nu e nevoie de dictare.
'
' DE CE PE PROFILUL OBISNUIT, fara --user-data-dir separat: permisiunea de
' microfon e legata de profil. Pe un profil nou, urechea ar cere din nou voie la
' fiecare pornire, intr-o fereastra fara bara de adrese, unde bula de permisiune
' e greu de gasit. ATENTIE: permisiunea data in Edge NU se mosteneste in Chrome —
' prima pornire cere din nou voie pentru microfon, o singura data.
'
' Cheia ANTHROPIC_API_KEY se mosteneste din mediul utilizatorului. Nu e scrisa
' aici si nu trebuie sa fie.

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

radacina = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = radacina

shell.Run "py -m uvicorn server.app:aplicatie --port 8100", 0, False

' Serverul are nevoie de o secunda pana asculta pe port. Deschiderea paginii
' inainte de asta da o eroare de conexiune in browser, si omul crede ca s-a rupt.
WScript.Sleep 2500

adresa = "http://localhost:8100"
browser = shell.ExpandEnvironmentStrings("%ProgramFiles%") & _
          "\Google\Chrome\Application\chrome.exe"
If Not fso.FileExists(browser) Then
  browser = shell.ExpandEnvironmentStrings("%ProgramFiles(x86)%") & _
            "\Google\Chrome\Application\chrome.exe"
End If
' Fara Chrome, Edge face acelasi lucru cu aceleasi argumente.
If Not fso.FileExists(browser) Then
  browser = shell.ExpandEnvironmentStrings("%ProgramFiles(x86)%") & _
            "\Microsoft\Edge\Application\msedge.exe"
End If

If fso.FileExists(browser) Then
  shell.Run """" & browser & """ --app=" & adresa & " --start-maximized", 1, False
Else
  ' Fara Edge, pagina se deschide oricum — in browserul implicit, ca inainte.
  ' Mih.AI nu depinde de un anume browser; fereastra proprie e un lux, nu o
  ' conditie de functionare.
  shell.Run adresa, 1, False
End If
