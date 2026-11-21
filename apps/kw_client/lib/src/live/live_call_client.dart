import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../config.dart';
import '../models/models.dart';

/// Factory for creating a [WebSocketChannel], overridable in tests.
typedef WebSocketChannelFactory = WebSocketChannel Function(Uri uri);

/// Typed server-to-client messages for `WS /v1/live/call` (Contract §7).
sealed class LiveServerMessage {
  const LiveServerMessage();

  /// Parses either a binary PCM16 24kHz audio frame or a JSON text frame.
  static LiveServerMessage fromWire(Object? raw) {
    if (raw is Uint8List) {
      return LiveAudioChunkMessage(pcm16Bytes: raw);
    }
    if (raw is List<int>) {
      return LiveAudioChunkMessage(pcm16Bytes: Uint8List.fromList(raw));
    }
    if (raw is String) {
      final decoded = jsonDecode(raw);
      if (decoded is Map) {
        final json = decoded.map((k, v) => MapEntry(k.toString(), v));
        return fromJson(json);
      }
    }
    return LiveUnknownMessage(type: 'unrecognized', raw: {'value': raw});
  }

  /// Parses a decoded JSON text frame into a typed [LiveServerMessage].
  static LiveServerMessage fromJson(Map<String, dynamic> json) {
    final type = (json['type'] ?? '').toString();
    switch (type) {
      case 'ready':
        return LiveReadyMessage(
          conversationId: (json['conversation_id'] ?? '').toString(),
          sessionId: (json['session_id'] ?? '').toString(),
          centreName: (json['centre_name'] ?? '').toString(),
          recordingNotice: (json['recording_notice'] ?? '').toString(),
        );
      case 'transcript':
        return LiveTranscriptMessage(
          speaker: (json['speaker'] ?? 'agent').toString(),
          text: (json['text'] ?? '').toString(),
          isFinal: json['final'] == true,
          lang: (json['lang'] ?? 'en').toString(),
        );
      case 'video_link':
        return LiveVideoLinkMessage(
          url: (json['url'] ?? '').toString(),
          expiresAt: (json['expires_at'] ?? '').toString(),
        );
      case 'modality':
        return LiveModalityMessage(
          value: (json['value'] ?? 'voice').toString(),
        );
      case 'ui_hint':
        return LiveUiHintMessage(
          kind: (json['kind'] ?? 'hold_steady').toString(),
          text: (json['text'] ?? '').toString(),
        );
      case 'event':
        return LiveEventMessage(
          event: LiveEvent.fromJson(json),
        );
      case 'go_away':
        final secs = json['seconds'];
        return LiveGoAwayMessage(
          seconds: secs is num ? secs.toInt() : int.tryParse('$secs') ?? 30,
        );
      case 'ended':
        return LiveEndedMessage(
          reason: (json['reason'] ?? 'completed').toString(),
          ticketId: json['ticket_id']?.toString(),
        );
      case 'error':
        return LiveErrorMessage(
          code: (json['code'] ?? 'ws_error').toString(),
          message: (json['message'] ?? 'Live call error').toString(),
        );
      default:
        return LiveUnknownMessage(type: type, raw: json);
    }
  }
}

final class LiveReadyMessage extends LiveServerMessage {
  const LiveReadyMessage({
    required this.conversationId,
    required this.sessionId,
    required this.centreName,
    required this.recordingNotice,
  });

  final String conversationId;
  final String sessionId;
  final String centreName;
  final String recordingNotice;
}

final class LiveTranscriptMessage extends LiveServerMessage {
  const LiveTranscriptMessage({
    required this.speaker,
    required this.text,
    required this.isFinal,
    required this.lang,
  });

  final String speaker;
  final String text;
  final bool isFinal;
  final String lang;
}

final class LiveVideoLinkMessage extends LiveServerMessage {
  const LiveVideoLinkMessage({
    required this.url,
    required this.expiresAt,
  });

  final String url;
  final String expiresAt;
}

final class LiveModalityMessage extends LiveServerMessage {
  const LiveModalityMessage({required this.value});

  final String value;
}

final class LiveUiHintMessage extends LiveServerMessage {
  const LiveUiHintMessage({
    required this.kind,
    required this.text,
  });

  final String kind;
  final String text;
}

final class LiveEventMessage extends LiveServerMessage {
  const LiveEventMessage({required this.event});

  final LiveEvent event;
}

final class LiveGoAwayMessage extends LiveServerMessage {
  const LiveGoAwayMessage({required this.seconds});

  final int seconds;
}

final class LiveEndedMessage extends LiveServerMessage {
  const LiveEndedMessage({
    required this.reason,
    this.ticketId,
  });

  final String reason;
  final String? ticketId;
}

final class LiveErrorMessage extends LiveServerMessage {
  const LiveErrorMessage({
    required this.code,
    required this.message,
  });

  final String code;
  final String message;
}

final class LiveAudioChunkMessage extends LiveServerMessage {
  const LiveAudioChunkMessage({required this.pcm16Bytes});

  /// Raw PCM16 little-endian, 24 kHz, mono agent voice bytes.
  final Uint8List pcm16Bytes;
}

final class LiveUnknownMessage extends LiveServerMessage {
  const LiveUnknownMessage({
    required this.type,
    required this.raw,
  });

  final String type;
  final Map<String, dynamic> raw;
}

/// WebSocket client for Keepwell Live Voice & Video calls (`WS /v1/live/call`, Contract §7).
class LiveCallClient {
  LiveCallClient({
    required this.config,
    WebSocketChannelFactory? channelFactory,
    this.autoReconnectOnGoAway = true,
  }) : _channelFactory = channelFactory ?? WebSocketChannel.connect;

  final KwConfig config;
  final WebSocketChannelFactory _channelFactory;
  final bool autoReconnectOnGoAway;

  final StreamController<LiveServerMessage> _messagesController =
      StreamController<LiveServerMessage>.broadcast();

  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  bool _isConnected = false;
  bool _manuallyEnded = false;
  bool _isReconnecting = false;

  String? _centreKey;
  String? _callerNumber;
  String? _languageHint;
  String? _authToken;
  String? _conversationId;

  /// Broadcast stream of typed messages emitted by the Live Call server.
  Stream<LiveServerMessage> get messages => _messagesController.stream;

  /// Whether a WebSocket connection is currently active.
  bool get isConnected => _isConnected;

  /// Active conversation ID returned by the server's `ready` frame.
  String? get currentConversationId => _conversationId;

  /// Opens the WebSocket and sends the Contract §7 `start` frame.
  Future<void> start({
    required String centreKey,
    required String callerNumber,
    String? languageHint,
    String? resumeConversationId,
    String? authToken,
  }) async {
    _centreKey = centreKey;
    _callerNumber = callerNumber;
    _languageHint = languageHint;
    _authToken = authToken;
    if (resumeConversationId != null && resumeConversationId.isNotEmpty) {
      _conversationId = resumeConversationId;
    }
    _manuallyEnded = false;

    await _connectAndSendStart();
  }

  Future<void> _connectAndSendStart() async {
    await _closeChannelOnly();

    final baseUri = config.liveWsUri;
    final uri = (_authToken != null && _authToken!.isNotEmpty)
        ? baseUri.replace(
            queryParameters: {
              ...baseUri.queryParameters,
              'token': _authToken!,
            },
          )
        : baseUri;

    final channel = _channelFactory(uri);
    _channel = channel;
    await channel.ready;
    _isConnected = true;

    _subscription = channel.stream.listen(
      _handleIncomingFrame,
      onError: (Object err) {
        if (!_messagesController.isClosed) {
          _messagesController.add(
            LiveErrorMessage(
              code: 'ws_stream_error',
              message: err.toString(),
            ),
          );
        }
      },
      onDone: () {
        _isConnected = false;
      },
    );

    _sendJson({
      'type': 'start',
      'centre_key': _centreKey ?? 'c_fw',
      'caller_number': _callerNumber ?? '',
      'language_hint': _languageHint,
      'resume_conversation_id': _conversationId,
    });
  }

  void _handleIncomingFrame(dynamic raw) {
    final msg = LiveServerMessage.fromWire(raw);

    if (msg is LiveReadyMessage && msg.conversationId.isNotEmpty) {
      _conversationId = msg.conversationId;
    }

    if (!_messagesController.isClosed) {
      _messagesController.add(msg);
    }

    if (msg is LiveGoAwayMessage &&
        autoReconnectOnGoAway &&
        !_manuallyEnded &&
        !_isReconnecting) {
      unawaited(_reconnectAfterGoAway());
    }
  }

  Future<void> _reconnectAfterGoAway() async {
    _isReconnecting = true;
    try {
      await Future<void>.delayed(const Duration(milliseconds: 150));
      if (!_manuallyEnded && !_messagesController.isClosed) {
        await _connectAndSendStart();
      }
    } catch (e) {
      if (!_messagesController.isClosed) {
        _messagesController.add(
          LiveErrorMessage(
            code: 'reconnect_failed',
            message: e.toString(),
          ),
        );
      }
    } finally {
      _isReconnecting = false;
    }
  }

  /// Sends raw PCM16 little-endian, 16 kHz, mono microphone audio chunk.
  void sendAudioPcm16(Uint8List pcmBytes) {
    final ch = _channel;
    if (ch == null || !_isConnected) return;
    ch.sink.add(pcmBytes);
  }

  /// Sends a base64 JPEG video frame (~1 fps, max 640px long edge).
  void sendVideoFrame(
    String base64Jpeg,
    int ts, {
    String mime = 'image/jpeg',
  }) {
    _sendJson({
      'type': 'video_frame',
      'mime': mime,
      'data': base64Jpeg,
      'ts': ts,
    });
  }

  /// Sends a still JPEG image (e.g. model sticker or display error code).
  void sendImage(
    String base64Jpeg, {
    String caption = 'sticker',
    String mime = 'image/jpeg',
  }) {
    _sendJson({
      'type': 'image',
      'mime': mime,
      'data': base64Jpeg,
      'caption': caption,
    });
  }

  /// Sends client modality (`voice` or `video`) and microphone mute state.
  void sendClientState({
    required String modality,
    required bool muted,
  }) {
    _sendJson({
      'type': 'client_state',
      'modality': modality,
      'muted': muted,
    });
  }

  /// Gracefully ends the call session.
  Future<void> end() async {
    _manuallyEnded = true;
    if (_isConnected) {
      _sendJson({'type': 'end'});
    }
    await _closeChannelOnly();
  }

  void _sendJson(Map<String, dynamic> payload) {
    final ch = _channel;
    if (ch == null || !_isConnected) return;
    ch.sink.add(jsonEncode(payload));
  }

  Future<void> _closeChannelOnly() async {
    _isConnected = false;
    await _subscription?.cancel();
    _subscription = null;
    await _channel?.sink.close();
    _channel = null;
  }

  Future<void> dispose() async {
    _manuallyEnded = true;
    await _closeChannelOnly();
    await _messagesController.close();
  }
}
