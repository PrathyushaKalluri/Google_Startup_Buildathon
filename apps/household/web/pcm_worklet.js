/**
 * Keepwell AudioWorkletProcessor: downsamples microphone Float32 audio from
 * AudioContext.sampleRate (typically 48 kHz) to 16 kHz mono PCM16 (little-endian)
 * and emits 40 ms chunks (640 samples = 1,280 bytes, within 20-100 ms contract).
 */
class KwPcm16Processor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._targetRate = 16000;
    this._chunkSamples = 640; // 40 ms @ 16 kHz
    this._out = new Int16Array(this._chunkSamples);
    this._outIdx = 0;
    this._phase = 0;
    this._sumSq = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0] || input[0].length === 0) {
      return true;
    }
    const ch = input[0];
    const ratio = sampleRate / this._targetRate;

    let pos = this._phase;
    while (pos < ch.length) {
      const i0 = Math.floor(pos);
      const i1 = Math.min(i0 + 1, ch.length - 1);
      const frac = pos - i0;
      const sample = ch[i0] + (ch[i1] - ch[i0]) * frac;
      const clamped = Math.max(-1, Math.min(1, sample));
      this._sumSq += clamped * clamped;
      this._out[this._outIdx++] =
          clamped < 0 ? Math.round(clamped * 32768) : Math.round(clamped * 32767);

      if (this._outIdx >= this._chunkSamples) {
        const rms = Math.sqrt(this._sumSq / this._chunkSamples);
        const buf = this._out.buffer;
        this.port.postMessage({ pcm16: buf, rms }, [buf]);
        this._out = new Int16Array(this._chunkSamples);
        this._outIdx = 0;
        this._sumSq = 0;
      }
      pos += ratio;
    }
    this._phase = pos - ch.length;
    return true;
  }
}

registerProcessor('kw-pcm16-processor', KwPcm16Processor);
