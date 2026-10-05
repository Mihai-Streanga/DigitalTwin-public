// Microfonul, tamponul, WAV-ul, trimiterea. Ce decide unde începe și unde se
// termină o rostire stă în `ureche-worklet.js`.
//
// DE CE WAV BRUT SI NU MediaRecorder/webm:
//
//   În JA.S.Mine, cel mai urât defect al dictării a fost aici: cu un vector
//   comun, `stop()` mai emitea un `dataavailable` final, iar coada aia ateriza
//   PRIMA în blob-ul frazei următoare — fragment fără antet EBML, respins de
//   ffmpeg. Prima frază mergea, restul nu; arăta ca intermitență și nu era.
//   Un WAV construit din tamponul propriu nu are container per fragment, deci
//   defectul nu are unde să apară. Necomprimat costă zero pe localhost.
//
// DE CE AudioContext LA 16000 Hz: Whisper vrea 16 kHz. Cerut aici, browserul
// face conversia cu filtrele lui; o resamplare naivă în JS ar adăuga artefacte
// exact în banda vorbirii.

const RATA = 16000;

export class Ureche {
  constructor({ laText, laStare, laVolum, praguri = {} }) {
    this.laText = laText;     // (text, info) => ...
    this.laStare = laStare;   // ("ascult" | "vorbesti" | "transcriu" | "oprit" | eroare)
    this.laVolum = laVolum;   // (volum) => ... , de ~10 ori pe secundă, pentru chip
    this.praguri = praguri;
    this.context = null;
    this.flux = null;
    this.nod = null;
    this.pornita = false;
    // Sub atâtea secunde de vorbire, rostirea se transcrie dar NU pleacă mai
    // departe.
    // Implicitul e plasă, nu comandă: fără el, `vorbire < undefined` e mereu
    // fals și filtrul ar dispărea tăcut. Cifra e aceeași cu cea din `pagina.js`.
    this.incredere = praguri.incredere ?? 0.15;
  }

  async porneste() {
    if (this.pornita) return;

    this.flux = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    this.context = new AudioContext({ sampleRate: RATA });
    await this.context.audioWorklet.addModule("/web/ureche-worklet.js");

    const sursa = this.context.createMediaStreamSource(this.flux);
    this.nod = new AudioWorkletNode(this.context, "ureche", {
      numberOfInputs: 1,
      numberOfOutputs: 1,
      processorOptions: this.praguri,
    });

    this.nod.port.onmessage = (e) => this.primeste(e.data);

    // CAPCANA: nodul trebuie legat mai departe, către destinație, altfel graful
    // audio îl consideră mort și `process()` nu mai e chemat NICIODATĂ. Se leagă
    // printr-un GainNode pe zero: nu se aude nimic, dar urechea trăiește.
    // Fără rândurile astea tace, și tace fără să se plângă.
    const mut = this.context.createGain();
    mut.gain.value = 0;
    sursa.connect(this.nod);
    this.nod.connect(mut);
    mut.connect(this.context.destination);

    this.pornita = true;
    this.laStare("ascult");
  }

  opreste() {
    if (!this.pornita) return;
    this.nod?.disconnect();
    this.context?.close();
    this.flux?.getTracks().forEach((t) => t.stop());
    this.context = this.flux = this.nod = null;
    this.pornita = false;
    this.laStare("oprit");
  }

  pauza(valoare) {
    this.nod?.port.postMessage({ tip: "pauza", valoare });
  }

  /** Cat vorbeste Mih.AI, urechea nu aude nimic — si ce apucase sa adune se
   *  arunca. Altfel microfonul prinde difuzorul, sau o tuse, si raspunsul lui
   *  e taiat la mijloc de un mesaj pe care nu l-ai trimis. */
  surd(valoare) {
    this.nod?.port.postMessage({ tip: "surd", valoare });
  }

  async primeste(mesaj) {
    if (mesaj.tip === "volum") { this.laVolum?.(mesaj.volum); return; }
    if (mesaj.tip === "vorbeste") { this.laStare("vorbesti"); return; }
    if (mesaj.tip !== "rostire") return;

    this.laStare("transcriu");
    this.pauza(true);
    try {
      const wav = catreWav(mesaj.pcm, mesaj.rata);
      const raspuns = await fetch("/api/transcrie", {
        method: "POST",
        headers: { "Content-Type": "audio/wav" },
        body: wav,
      });
      const r = await raspuns.json();
      if (r.eroare) { this.laStare("eroare: " + r.eroare); return; }

      const text = (r.text || "").trim();
      // Ce nu conține vorbire nu pleacă mai departe — acolo un apel costă bani.
      // Serverul răspunde cu text gol și cu motivul („fara vorbire", „liniste"),
      // fiindcă el are măsura adevărată: câte secunde de vorbire a găsit VAD-ul.
      // Rămâne în consolă, ca urmă — o rostire aruncată în tăcere arată exact ca
      // un microfon stricat.
      if (mesaj.vorbire < this.incredere || !text) {
        console.debug("[ureche] nu pleacă:", r.motiv || "text gol",
                      "· energie", mesaj.vorbire.toFixed(2), "s",
                      "· vorbire", r.vorbire ?? "?", "s", text);
        this.laStare("ascult");
        return;
      }
      this.laText(text, r);
    } catch (e) {
      this.laStare("eroare: " + e.message);
    } finally {
      this.pauza(false);
      if (this.pornita) this.laStare("ascult");
    }
  }
}

// Float32 [-1,1] → WAV PCM 16 biți, mono.
function catreWav(esantioane, rata) {
  const octeti = new ArrayBuffer(44 + esantioane.length * 2);
  const v = new DataView(octeti);
  const text = (la, s) => { for (let i = 0; i < s.length; i++) v.setUint8(la + i, s.charCodeAt(i)); };

  text(0, "RIFF");
  v.setUint32(4, 36 + esantioane.length * 2, true);
  text(8, "WAVEfmt ");
  v.setUint32(16, 16, true);        // lungimea blocului fmt
  v.setUint16(20, 1, true);         // PCM
  v.setUint16(22, 1, true);         // mono
  v.setUint32(24, rata, true);
  v.setUint32(28, rata * 2, true);  // octeți pe secundă
  v.setUint16(32, 2, true);         // aliniere
  v.setUint16(34, 16, true);        // biți pe eșantion
  text(36, "data");
  v.setUint32(40, esantioane.length * 2, true);

  let la = 44;
  for (let i = 0; i < esantioane.length; i++, la += 2) {
    const x = Math.max(-1, Math.min(1, esantioane[i]));
    v.setInt16(la, x < 0 ? x * 0x8000 : x * 0x7fff, true);
  }
  return octeti;
}
