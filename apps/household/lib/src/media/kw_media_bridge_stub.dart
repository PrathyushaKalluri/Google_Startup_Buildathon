import 'dart:typed_data';

import 'package:flutter/material.dart';

/// Platform-neutral media bridge (VM / widget test stub).
///
/// On Flutter Web, `kw_media_bridge_web.dart` binds `getUserMedia`,
/// `AudioWorklet` (16 kHz PCM16), Web Audio 24 kHz playback, and real
/// `<video>` + `<canvas>` JPEG frame capture.
class KwMediaBridge {
  KwMediaBridge({this.onTestCaptureFrame});

  /// Optional test hook for VM widget tests where no browser camera exists.
  final String? Function()? onTestCaptureFrame;

  bool _muted = false;
  bool _speakerOn = true;
  int _flushes = 0;

  bool get isMuted => _muted;
  bool get isSpeakerOn => _speakerOn;
  int get flushCount => _flushes;

  Future<bool> startAudioCapture({
    required void Function(Uint8List pcm16Chunk) onChunk,
    void Function(double rms)? onRms,
    VoidCallback? onBargeIn,
  }) async {
    return true;
  }

  void stopAudioCapture() {}

  void playPcm24k(Uint8List pcm16Bytes) {}

  void flushPlayback() {
    _flushes += 1;
  }

  void setMuted(bool muted) {
    _muted = muted;
  }

  void setSpeaker(bool speakerOn) {
    _speakerOn = speakerOn;
  }

  Future<bool> startVideoPreview() async => true;

  /// Captures a live video frame as base64 JPEG (<=640 px long edge).
  /// Returns null on non-web VM unless [onTestCaptureFrame] is supplied.
  String? captureVideoFrameJpeg({int maxLongEdge = 640, double quality = 0.72}) {
    return onTestCaptureFrame?.call();
  }

  void stopVideoPreview() {}

  Widget buildVideoPreview() {
    return const ColoredBox(color: Color(0xFF101726));
  }
}
