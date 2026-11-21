/**
 * Keepwell Browser Media Bridge for Household Call Dialer & Guided Video-Link.
 *
 * - Microphone capture: getUserMedia (echoCancellation + noiseSuppression) ->
 *   AudioWorklet ('pcm_worklet.js') -> 16 kHz mono PCM16 (40 ms / 1,280-byte chunks).
 * - Audio playback: 24 kHz mono PCM16 -> Web Audio AudioContext with 60 ms jitter
 *   buffer, speaker GainNode, and instant flush on barge-in or server interruption.
 * - Live video: getUserMedia rear/default camera -> <video> preview element ->
 *   offscreen <canvas> scaled to <= 640 px long edge -> real JPEG base64 frames.
 */
(function () {
  const stats = {
    sentPcmChunks: 0,
    sentPcmBytes: 0,
    playedPcmChunks: 0,
    playedPcmBytes: 0,
    flushes: 0,
    sentVideoFrames: 0,
    lastVideoWidth: 0,
    lastVideoHeight: 0,
    lastVideoBytes: 0,
    muted: false,
    speakerOn: true,
    echoCancellation: false,
    noiseSuppression: false,
  };
  window.__kwMediaStats = stats;

  let captureCtx = null;
  let captureStream = null;
  let workletNode = null;
  let muted = false;
  let speakerOn = true;

  let playbackCtx = null;
  let playbackGain = null;
  let nextPlayTime = 0;
  const activeSources = new Set();

  let videoStream = null;
  let videoElement = null;
  let offscreenCanvas = null;

  function ensurePlaybackContext() {
    if (!playbackCtx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      playbackCtx = new AudioCtx({ sampleRate: 24000 });
      playbackGain = playbackCtx.createGain();
      playbackGain.gain.value = speakerOn ? 1.0 : 0.0;
      playbackGain.connect(playbackCtx.destination);
    }
    if (playbackCtx.state === 'suspended') {
      playbackCtx.resume().catch(() => {});
    }
    return playbackCtx;
  }

  function flushPlayback() {
    for (const src of activeSources) {
      try {
        src.stop();
        src.disconnect();
      } catch (_) {}
    }
    activeSources.clear();
    nextPlayTime = 0;
    stats.flushes += 1;
  }

  function playPcm24k(uint8) {
    if (!uint8 || uint8.byteLength < 2) return;
    const ctx = ensurePlaybackContext();
    const byteOffset = uint8.byteOffset || 0;
    const sampleCount = Math.floor(uint8.byteLength / 2);
    const view = new DataView(uint8.buffer, byteOffset, sampleCount * 2);
    const audioBuffer = ctx.createBuffer(1, sampleCount, 24000);
    const channel = audioBuffer.getChannelData(0);
    for (let i = 0; i < sampleCount; i++) {
      channel[i] = view.getInt16(i * 2, true) / 32768.0;
    }

    const src = ctx.createBufferSource();
    src.buffer = audioBuffer;
    src.connect(playbackGain);

    const now = ctx.currentTime;
    const jitterLeadSec = 0.06; // 60 ms jitter buffer
    if (nextPlayTime < now + 0.01) {
      nextPlayTime = now + jitterLeadSec;
    }
    src.start(nextPlayTime);
    nextPlayTime += audioBuffer.duration;
    activeSources.add(src);
    src.onended = () => activeSources.delete(src);

    stats.playedPcmChunks += 1;
    stats.playedPcmBytes += uint8.byteLength;
  }

  async function startAudioCapture(onChunk, onRms, onBargeIn) {
    stopAudioCapture();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('getUserMedia unavailable');
    }
    captureStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
      },
      video: false,
    });
    const track = captureStream.getAudioTracks()[0];
    if (track && track.getSettings) {
      const s = track.getSettings();
      stats.echoCancellation = s.echoCancellation !== false;
      stats.noiseSuppression = s.noiseSuppression !== false;
    } else {
      stats.echoCancellation = true;
      stats.noiseSuppression = true;
    }

    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    captureCtx = new AudioCtx();
    if (captureCtx.state === 'suspended') {
      await captureCtx.resume();
    }
    ensurePlaybackContext();

    const source = captureCtx.createMediaStreamSource(captureStream);
    await captureCtx.audioWorklet.addModule('pcm_worklet.js');
    workletNode = new AudioWorkletNode(captureCtx, 'kw-pcm16-processor');
    workletNode.port.onmessage = (event) => {
      const data = event.data;
      if (!data || !data.pcm16) return;
      const rms = typeof data.rms === 'number' ? data.rms : 0;
      if (muted) {
        if (onRms) onRms(0);
        return;
      }
      if (onRms) onRms(Math.min(1, rms * 3.5));
      if (rms > 0.08 && activeSources.size > 0) {
        flushPlayback();
        if (onBargeIn) onBargeIn();
      }
      const bytes = new Uint8Array(data.pcm16);
      stats.sentPcmChunks += 1;
      stats.sentPcmBytes += bytes.byteLength;
      if (onChunk) onChunk(bytes);
    };

    // Route through a silent gain node so the worklet ticks without mic loopback.
    const silentGain = captureCtx.createGain();
    silentGain.gain.value = 0.0;
    source.connect(workletNode);
    workletNode.connect(silentGain);
    silentGain.connect(captureCtx.destination);
    return true;
  }

  function stopAudioCapture() {
    if (workletNode) {
      try {
        workletNode.disconnect();
      } catch (_) {}
      workletNode = null;
    }
    if (captureStream) {
      for (const t of captureStream.getTracks()) t.stop();
      captureStream = null;
    }
    if (captureCtx) {
      captureCtx.close().catch(() => {});
      captureCtx = null;
    }
  }

  function setMuted(isMuted) {
    muted = !!isMuted;
    stats.muted = muted;
    if (captureStream) {
      for (const t of captureStream.getAudioTracks()) {
        t.enabled = !muted;
      }
    }
  }

  function setSpeaker(isOn) {
    speakerOn = !!isOn;
    stats.speakerOn = speakerOn;
    if (playbackGain) {
      playbackGain.gain.value = speakerOn ? 1.0 : 0.0;
    }
  }

  function createVideoElement(elementId) {
    const el = document.createElement('video');
    el.id = elementId;
    el.autoplay = true;
    el.playsInline = true;
    el.muted = true;
    el.style.width = '100%';
    el.style.height = '100%';
    el.style.objectFit = 'cover';
    el.style.backgroundColor = '#101726';
    videoElement = el;
    if (videoStream) {
      el.srcObject = videoStream;
      el.play().catch(() => {});
    }
    return el;
  }

  async function startVideoPreview() {
    stopVideoPreview();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('getUserMedia unavailable');
    }
    videoStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 640 },
        height: { ideal: 480 },
      },
      audio: false,
    });
    if (videoElement) {
      videoElement.srcObject = videoStream;
      await videoElement.play().catch(() => {});
    }
    return true;
  }

  function captureVideoFrameJpeg(maxLongEdge, quality) {
    const el = videoElement;
    if (!el || !videoStream) return null;
    const rawW = el.videoWidth || 640;
    const rawH = el.videoHeight || 480;
    if (rawW === 0 || rawH === 0) return null;

    const maxEdge = maxLongEdge || 640;
    const scale = Math.min(1, maxEdge / Math.max(rawW, rawH));
    const w = Math.max(1, Math.round(rawW * scale));
    const h = Math.max(1, Math.round(rawH * scale));

    if (!offscreenCanvas) {
      offscreenCanvas = document.createElement('canvas');
    }
    offscreenCanvas.width = w;
    offscreenCanvas.height = h;
    const ctx = offscreenCanvas.getContext('2d');
    if (!ctx) return null;
    ctx.drawImage(el, 0, 0, w, h);

    const dataUrl = offscreenCanvas.toDataURL('image/jpeg', quality || 0.72);
    const prefix = 'data:image/jpeg;base64,';
    if (!dataUrl.startsWith(prefix)) return null;
    const base64 = dataUrl.slice(prefix.length);

    stats.sentVideoFrames += 1;
    stats.lastVideoWidth = w;
    stats.lastVideoHeight = h;
    stats.lastVideoBytes = Math.floor((base64.length * 3) / 4);
    return base64;
  }

  function stopVideoPreview() {
    if (videoElement) {
      try {
        videoElement.pause();
        videoElement.srcObject = null;
      } catch (_) {}
    }
    if (videoStream) {
      for (const t of videoStream.getTracks()) t.stop();
      videoStream = null;
    }
  }

  window.kwMediaBridge = {
    startAudioCapture,
    stopAudioCapture,
    playPcm24k,
    flushPlayback,
    setMuted,
    setSpeaker,
    createVideoElement,
    startVideoPreview,
    captureVideoFrameJpeg,
    stopVideoPreview,
  };
})();
