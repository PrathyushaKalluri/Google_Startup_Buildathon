import 'dart:js_interop';
import 'dart:typed_data';
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';

@JS('window.kwMediaBridge')
external _JsMediaBridge? get _jsBridge;

extension type _JsMediaBridge._(JSObject _) implements JSObject {
  external JSPromise<JSBoolean> startAudioCapture(
    JSFunction onChunk,
    JSFunction onRms,
    JSFunction onBargeIn,
  );
  external void stopAudioCapture();
  external void playPcm24k(JSUint8Array bytes);
  external void flushPlayback();
  external void setMuted(JSBoolean muted);
  external void setSpeaker(JSBoolean speakerOn);
  external JSObject createVideoElement(JSString elementId);
  external JSPromise<JSBoolean> startVideoPreview();
  external JSString? captureVideoFrameJpeg(JSNumber maxLongEdge, JSNumber quality);
  external void stopVideoPreview();
}

/// Web implementation of [KwMediaBridge] backed by `web/kw_media_bridge.js`
/// and `web/pcm_worklet.js`.
class KwMediaBridge {
  KwMediaBridge({this.onTestCaptureFrame});

  final String? Function()? onTestCaptureFrame;

  static const String _videoViewType = 'kw-live-camera-video-preview';
  static bool _viewFactoryRegistered = false;

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
    final bridge = _jsBridge;
    if (bridge == null) return false;
    final jsOnChunk = ((JSUint8Array arr) {
      onChunk(arr.toDart);
    }).toJS;
    final jsOnRms = ((JSNumber rms) {
      onRms?.call(rms.toDartDouble);
    }).toJS;
    final jsOnBargeIn = (() {
      onBargeIn?.call();
    }).toJS;
    final ok = await bridge.startAudioCapture(jsOnChunk, jsOnRms, jsOnBargeIn).toDart;
    return ok.toDart;
  }

  void stopAudioCapture() {
    _jsBridge?.stopAudioCapture();
  }

  void playPcm24k(Uint8List pcm16Bytes) {
    if (pcm16Bytes.isEmpty) return;
    _jsBridge?.playPcm24k(pcm16Bytes.toJS);
  }

  void flushPlayback() {
    _flushes += 1;
    _jsBridge?.flushPlayback();
  }

  void setMuted(bool muted) {
    _muted = muted;
    _jsBridge?.setMuted(muted.toJS);
  }

  void setSpeaker(bool speakerOn) {
    _speakerOn = speakerOn;
    _jsBridge?.setSpeaker(speakerOn.toJS);
  }

  Future<bool> startVideoPreview() async {
    final bridge = _jsBridge;
    if (bridge == null) return false;
    final ok = await bridge.startVideoPreview().toDart;
    return ok.toDart;
  }

  String? captureVideoFrameJpeg({int maxLongEdge = 640, double quality = 0.72}) {
    final bridge = _jsBridge;
    if (bridge == null) return null;
    final res = bridge.captureVideoFrameJpeg(maxLongEdge.toJS, quality.toJS);
    return res?.toDart;
  }

  void stopVideoPreview() {
    _jsBridge?.stopVideoPreview();
  }

  Widget buildVideoPreview() {
    if (!_viewFactoryRegistered) {
      _viewFactoryRegistered = true;
      ui_web.platformViewRegistry.registerViewFactory(
        _videoViewType,
        (int viewId) {
          final bridge = _jsBridge!;
          return bridge.createVideoElement('kw-live-video-$viewId'.toJS);
        },
      );
    }
    return const HtmlElementView(viewType: _videoViewType);
  }
}
