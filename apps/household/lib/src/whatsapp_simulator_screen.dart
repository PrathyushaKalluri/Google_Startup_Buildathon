import 'dart:async';

import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

import 'household_l10n.dart';

/// Delivery tick state for simulator chat bubbles.
enum _DeliveryTick { sending, sent, delivered, read }

class _SimChatMessage {
  const _SimChatMessage({
    required this.id,
    required this.isFromHousehold,
    required this.kind,
    required this.text,
    required this.at,
    this.tick = _DeliveryTick.read,
    this.attachmentLabel,
    this.deepLinkRoute,
  });

  final String id;
  final bool isFromHousehold;

  /// `text`, `audio`, `image`, or `location`.
  final String kind;
  final String text;
  final DateTime at;
  final _DeliveryTick tick;
  final String? attachmentLabel;
  final String? deepLinkRoute;

  _SimChatMessage copyWith({_DeliveryTick? tick}) {
    return _SimChatMessage(
      id: id,
      isFromHousehold: isFromHousehold,
      kind: kind,
      text: text,
      at: at,
      tick: tick ?? this.tick,
      attachmentLabel: attachmentLabel,
      deepLinkRoute: deepLinkRoute,
    );
  }
}

/// Surface 1: Phone-framed Material 3 Expressive WhatsApp simulator.
///
/// Uses Material 3 tonal palette (no WhatsApp logo or green trade dress),
/// lets presenters switch across all 9 service centres and seeded households,
/// creates a zero-sign-in public session, and posts inbound messages to
/// `POST /v1/channels/whatsapp/simulator/inbound`.
class WhatsAppSimulatorScreen extends StatefulWidget {
  const WhatsAppSimulatorScreen({
    super.key,
    required this.apiClient,
    required this.activeCentre,
    required this.onCentreChanged,
    this.activeHousehold,
    required this.onHouseholdChanged,
    this.onOpenRoute,
  });

  final KwApiClient apiClient;
  final KwCentreIdentity activeCentre;
  final ValueChanged<KwCentreIdentity> onCentreChanged;
  final DemoHousehold? activeHousehold;
  final ValueChanged<DemoHousehold?> onHouseholdChanged;
  final ValueChanged<String>? onOpenRoute;

  @override
  State<WhatsAppSimulatorScreen> createState() =>
      _WhatsAppSimulatorScreenState();
}

class _WhatsAppSimulatorScreenState extends State<WhatsAppSimulatorScreen> {
  final TextEditingController _composerController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  List<DemoHousehold> _households = const [];
  DemoHousehold? _selectedHousehold;
  bool _loadingHouseholds = false;
  bool _sessionActive = false;
  bool _sending = false;
  bool _recordingVoice = false;
  int _voiceSeconds = 0;
  Timer? _voiceTimer;
  String? _statusNotice;

  final List<_SimChatMessage> _messages = <_SimChatMessage>[];

  static const List<String> _quickReplies = <String>[
    'Yes, try safe fix',
    'Switch to video',
    'Confirm slot',
    'Send a technician',
  ];

  @override
  void initState() {
    super.initState();
    _selectedHousehold = widget.activeHousehold;
    _seedCentreGreeting();
    unawaited(_loadHouseholdsForCentre(widget.activeCentre.key));
  }

  @override
  void didUpdateWidget(covariant WhatsAppSimulatorScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.activeCentre.key != widget.activeCentre.key) {
      _messages.clear();
      _seedCentreGreeting();
      unawaited(_loadHouseholdsForCentre(widget.activeCentre.key));
    }
  }

  @override
  void dispose() {
    _voiceTimer?.cancel();
    _composerController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _seedCentreGreeting() {
    _messages.add(
      _SimChatMessage(
        id: 'welcome-${widget.activeCentre.key}',
        isFromHousehold: false,
        kind: 'text',
        text:
            'Hello from ${widget.activeCentre.name}. Tell us which appliance needs help — you can type, send a voice note, or share a photo of the model sticker.',
        at: DateTime.now(),
      ),
    );
  }

  Future<void> _loadHouseholdsForCentre(String centreKey) async {
    setState(() {
      _loadingHouseholds = true;
      _statusNotice = null;
    });

    try {
      final paged =
          await widget.apiClient.listDemoHouseholds(centreKey: centreKey);
      if (!mounted) return;
      final items = paged.items;
      DemoHousehold? chosen = _selectedHousehold;
      if (chosen == null ||
          !items.any((h) => h.householdId == chosen!.householdId)) {
        chosen = items.isNotEmpty ? items.first : null;
      }
      setState(() {
        _households = items;
        _selectedHousehold = chosen;
        _loadingHouseholds = false;
      });
      widget.onHouseholdChanged(chosen);
      if (chosen != null && chosen.magicToken.isNotEmpty) {
        await _activatePublicSession(chosen.magicToken);
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _households = const [];
        _loadingHouseholds = false;
        _statusNotice =
            'Using offline simulator preview — live households will appear when the API server is reachable.';
      });
    }
  }

  Future<void> _activatePublicSession(String magicToken) async {
    try {
      await widget.apiClient.createPublicSession(magicToken);
      if (!mounted) return;
      setState(() {
        _sessionActive = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _sessionActive = false;
      });
    }
  }

  Future<void> _selectHousehold(DemoHousehold? household) async {
    setState(() {
      _selectedHousehold = household;
      _sessionActive = false;
    });
    widget.onHouseholdChanged(household);
    if (household != null && household.magicToken.isNotEmpty) {
      await _activatePublicSession(household.magicToken);
    }
  }

  String _centreServiceNumber(String centreKey) {
    final index = KwAuthHelper.demoCentres
        .indexWhere((c) => c.key == centreKey)
        .clamp(0, 8);
    return '+91404000010${index + 1}';
  }

  Future<void> _sendMessagePayload({
    required String kind,
    required String displayText,
    required Map<String, dynamic> wireMessage,
    String? attachmentLabel,
  }) async {
    if (_sending) return;

    final now = DateTime.now();
    final msgId = 'msg-${now.microsecondsSinceEpoch}';
    final outbound = _SimChatMessage(
      id: msgId,
      isFromHousehold: true,
      kind: kind,
      text: displayText,
      at: now,
      tick: _DeliveryTick.sending,
      attachmentLabel: attachmentLabel,
    );

    setState(() {
      _messages.add(outbound);
      _sending = true;
      _statusNotice = null;
    });
    _scrollToBottom();

    final household = _selectedHousehold;
    final fromPhone = household?.phoneMasked ?? '+919848000001';
    final profileName = household?.displayName ?? 'Household Caller';

    try {
      final response = await widget.apiClient.sendWhatsAppSimulatorInbound(
        toNumber: _centreServiceNumber(widget.activeCentre.key),
        fromPhone: fromPhone,
        senderProfileName: profileName,
        messages: <Map<String, dynamic>>[wireMessage],
      );

      if (!mounted) return;
      _updateTick(msgId, _DeliveryTick.read);

      final replies = _extractVerbatimReplies(response);
      setState(() {
        for (var i = 0; i < replies.length; i++) {
          final replyText = replies[i];
          _messages.add(
            _SimChatMessage(
              id: 'reply-${now.microsecondsSinceEpoch}-$i',
              isFromHousehold: false,
              kind: 'text',
              text: replyText,
              at: DateTime.now(),
              deepLinkRoute: _detectDeepLink(replyText),
            ),
          );
        }
        _sending = false;
      });
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      _updateTick(msgId, _DeliveryTick.sent);
      setState(() {
        _sending = false;
        _statusNotice =
            'Could not reach simulator backend. Check API_BASE_URL and try again.';
      });
    }
  }

  void _updateTick(String id, _DeliveryTick tick) {
    final idx = _messages.indexWhere((m) => m.id == id);
    if (idx != -1) {
      _messages[idx] = _messages[idx].copyWith(tick: tick);
    }
  }

  List<String> _extractVerbatimReplies(Map<String, dynamic> response) {
    final results = <String>[];
    final rawReplies = response['replies'] ??
        response['outbound_messages'] ??
        response['messages'];
    if (rawReplies is List) {
      for (final item in rawReplies) {
        if (item is String && item.trim().isNotEmpty) {
          results.add(item);
        } else if (item is Map) {
          final text = item['text'] ?? item['body'] ?? item['message'];
          if (text != null && text.toString().trim().isNotEmpty) {
            results.add(text.toString());
          }
        }
      }
    }
    if (results.isEmpty) {
      final single = response['reply'] ?? response['text'] ?? response['message'];
      if (single != null && single.toString().trim().isNotEmpty) {
        results.add(single.toString());
      }
    }
    return results;
  }

  String? _detectDeepLink(String text) {
    final match = RegExp(r'(/(?:v|home|quotes|otp)/[A-Za-z0-9._-]+)')
        .firstMatch(text);
    return match?.group(1);
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent + 120,
        duration: KwMotion.durationFor(context, KwMotion.fastDuration),
        curve: KwMotion.curveFor(context),
      );
    });
  }

  Future<void> _handleSendText([String? overrideText]) async {
    final text = (overrideText ?? _composerController.text).trim();
    if (text.isEmpty) return;
    if (overrideText == null) {
      _composerController.clear();
    }
    await _sendMessagePayload(
      kind: 'text',
      displayText: text,
      wireMessage: <String, dynamic>{
        'type': 'text',
        'text': text,
      },
    );
  }

  void _toggleVoiceNote() {
    if (_recordingVoice) {
      _voiceTimer?.cancel();
      final durationSec = _voiceSeconds < 1 ? 3 : _voiceSeconds;
      setState(() {
        _recordingVoice = false;
        _voiceSeconds = 0;
      });
      unawaited(
        _sendMessagePayload(
          kind: 'audio',
          displayText: 'Voice note (${durationSec}s) · Hindi / English audio',
          attachmentLabel: 'Audio · 0:${durationSec.toString().padLeft(2, '0')}',
          wireMessage: <String, dynamic>{
            'type': 'audio',
            'duration_sec': durationSec,
            'mime_type': 'audio/ogg',
            'transcript_hint':
                'My washing machine stopped spinning and shows an error code.',
          },
        ),
      );
    } else {
      setState(() {
        _recordingVoice = true;
        _voiceSeconds = 0;
      });
      _voiceTimer?.cancel();
      _voiceTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (!mounted) return;
        setState(() {
          _voiceSeconds += 1;
        });
      });
    }
  }

  Future<void> _attachSampleImage() async {
    await _sendMessagePayload(
      kind: 'image',
      displayText: 'Attached model sticker photo (Frostline / Wavecrest)',
      attachmentLabel: 'JPEG · Model sticker',
      wireMessage: <String, dynamic>{
        'type': 'image',
        'mime_type': 'image/jpeg',
        'caption': 'Model sticker photo',
        'media_ref': 'sim://sample-model-sticker.jpg',
      },
    );
  }

  Future<void> _shareLocationPin() async {
    final locality = widget.activeCentre.locality;
    await _sendMessagePayload(
      kind: 'location',
      displayText: 'Shared location pin · $locality, Hyderabad',
      attachmentLabel: 'Pin · 17.4486, 78.3908',
      wireMessage: <String, dynamic>{
        'type': 'location',
        'lat': 17.4486,
        'lon': 78.3908,
        'label': '$locality, Hyderabad',
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;
    final hStrings = HouseholdStrings.of(context);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: Padding(
          padding: const EdgeInsets.all(KwSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildSelectorCard(context, hStrings),
              const SizedBox(height: KwSpacing.sm),
              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    color: cs.surfaceContainerLowest,
                    borderRadius: KwShapes.radiusExtraLarge,
                    border: Border.all(color: cs.outlineVariant, width: 1.5),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: Column(
                    children: [
                      _buildPhoneHeader(context, hStrings, cs, kw),
                      if (_statusNotice != null)
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.symmetric(
                            horizontal: KwSpacing.md,
                            vertical: KwSpacing.xs,
                          ),
                          color: kw.needsChecking.container,
                          child: Text(
                            _statusNotice!,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: kw.needsChecking.onContainer,
                            ),
                          ),
                        ),
                      Expanded(
                        child: ListView.separated(
                          controller: _scrollController,
                          padding: const EdgeInsets.all(KwSpacing.md),
                          itemCount: _messages.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: KwSpacing.xs),
                          itemBuilder: (context, index) =>
                              _buildBubble(context, _messages[index]),
                        ),
                      ),
                      _buildQuickReplies(context),
                      _buildComposer(context, hStrings),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSelectorCard(BuildContext context, HouseholdStrings hStrings) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final kw = theme.kwColors;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(KwSpacing.sm),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.store_mall_directory_rounded,
                    size: 18, color: cs.primary),
                const SizedBox(width: KwSpacing.xs),
                Expanded(
                  child: Text(
                    hStrings.whatsappSimulatorTitle,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                if (_sessionActive)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: KwSpacing.xs,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: kw.verified.container,
                      borderRadius: KwShapes.radiusFull,
                    ),
                    child: Text(
                      hStrings.sessionActiveLabel,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: kw.verified.onContainer,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: KwSpacing.xs),
            Wrap(
              spacing: KwSpacing.xs,
              runSpacing: KwSpacing.xs,
              children: [
                SizedBox(
                  width: 230,
                  child: DropdownButtonFormField<String>(
                    value: widget.activeCentre.key,
                    isExpanded: true,
                    decoration: InputDecoration(
                      labelText: hStrings.serviceCentreLabel,
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: KwSpacing.sm,
                        vertical: KwSpacing.xs,
                      ),
                    ),
                    items: [
                      for (final centre in KwAuthHelper.demoCentres)
                        DropdownMenuItem<String>(
                          value: centre.key,
                          child: Text(
                            centre.name,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                    ],
                    onChanged: (key) {
                      if (key == null) return;
                      final chosen = KwAuthHelper.demoCentres.firstWhere(
                        (c) => c.key == key,
                        orElse: () => widget.activeCentre,
                      );
                      widget.onCentreChanged(chosen);
                    },
                  ),
                ),
                SizedBox(
                  width: 220,
                  child: _loadingHouseholds
                      ? const Padding(
                          padding: EdgeInsets.symmetric(vertical: KwSpacing.xs),
                          child: KwSkeletonLoader(lines: 1, height: 36),
                        )
                      : DropdownButtonFormField<String>(
                          value: _selectedHousehold?.householdId,
                          isExpanded: true,
                          decoration: InputDecoration(
                            labelText: hStrings.householdLabel,
                            isDense: true,
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: KwSpacing.sm,
                              vertical: KwSpacing.xs,
                            ),
                          ),
                          hint: const Text('Select seeded household'),
                          items: [
                            for (final h in _households)
                              DropdownMenuItem<String>(
                                value: h.householdId,
                                child: Text(
                                  '${h.displayName} (${h.language.toUpperCase()})',
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                          ],
                          onChanged: (id) {
                            if (id == null) return;
                            final found = _households.firstWhere(
                              (h) => h.householdId == id,
                            );
                            unawaited(_selectHousehold(found));
                          },
                        ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPhoneHeader(
    BuildContext context,
    HouseholdStrings hStrings,
    ColorScheme cs,
    KwSemanticColors kw,
  ) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: KwSpacing.md,
        vertical: KwSpacing.sm,
      ),
      color: cs.primaryContainer,
      child: Row(
        children: [
          CircleAvatar(
            backgroundColor: cs.primary,
            foregroundColor: cs.onPrimary,
            child: const Icon(Icons.home_repair_service_rounded, size: 20),
          ),
          const SizedBox(width: KwSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.activeCentre.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: cs.onPrimaryContainer,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  '${hStrings.whatsappSimulatorTitle} · ${widget.activeCentre.locality}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: cs.onPrimaryContainer.withValues(alpha: 0.85),
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: cs.surface,
              borderRadius: KwShapes.radiusFull,
            ),
            child: Text(
              _centreServiceNumber(widget.activeCentre.key),
              style: KwTheme.monoStyle(
                context,
                fontSize: 11,
                color: cs.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBubble(BuildContext context, _SimChatMessage msg) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final isMe = msg.isFromHousehold;

    final bubbleBg = isMe ? cs.primaryContainer : cs.surfaceContainerHigh;
    final fg = isMe ? cs.onPrimaryContainer : cs.onSurface;

    return Semantics(
      liveRegion: !isMe,
      label: '${isMe ? "You" : widget.activeCentre.name}: ${msg.text}',
      child: Align(
        alignment: isMe ? Alignment.centerRight : Alignment.centerLeft,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 370),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: KwSpacing.sm,
              vertical: KwSpacing.xs,
            ),
            decoration: BoxDecoration(
              color: bubbleBg,
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(KwShapes.medium),
                topRight: const Radius.circular(KwShapes.medium),
                bottomLeft: Radius.circular(
                  isMe ? KwShapes.medium : KwShapes.extraSmall,
                ),
                bottomRight: Radius.circular(
                  isMe ? KwShapes.extraSmall : KwShapes.medium,
                ),
              ),
              border: Border.all(color: cs.outlineVariant.withValues(alpha: 0.5)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (msg.attachmentLabel != null) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: KwSpacing.xs,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: cs.surface.withValues(alpha: 0.7),
                      borderRadius: KwShapes.radiusSmall,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          switch (msg.kind) {
                            'audio' => Icons.graphic_eq_rounded,
                            'image' => Icons.photo_camera_rounded,
                            'location' => Icons.location_on_rounded,
                            _ => Icons.attach_file_rounded,
                          },
                          size: 16,
                          color: cs.primary,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          msg.attachmentLabel!,
                          style: theme.textTheme.labelSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 6),
                ],
                Text(
                  msg.text,
                  style: theme.textTheme.bodyMedium?.copyWith(color: fg),
                ),
                if (msg.deepLinkRoute != null && widget.onOpenRoute != null) ...[
                  const SizedBox(height: KwSpacing.xs),
                  FilledButton.tonalIcon(
                    onPressed: () => widget.onOpenRoute!(msg.deepLinkRoute!),
                    icon: const Icon(Icons.open_in_new_rounded, size: 16),
                    label: Text('Open ${msg.deepLinkRoute}'),
                  ),
                ],
                const SizedBox(height: 4),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      formatIstDateTime(
                        msg.at,
                        includeDate: false,
                        includeTzLabel: false,
                      ),
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: fg.withValues(alpha: 0.72),
                      ),
                    ),
                    if (isMe) ...[
                      const SizedBox(width: 4),
                      Icon(
                        switch (msg.tick) {
                          _DeliveryTick.sending => Icons.schedule_rounded,
                          _DeliveryTick.sent => Icons.done_rounded,
                          _DeliveryTick.delivered => Icons.done_all_rounded,
                          _DeliveryTick.read => Icons.done_all_rounded,
                        },
                        size: 14,
                        color: msg.tick == _DeliveryTick.read
                            ? cs.primary
                            : fg.withValues(alpha: 0.65),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildQuickReplies(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(
        KwSpacing.sm,
        KwSpacing.xs,
        KwSpacing.sm,
        0,
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            for (final chip in _quickReplies) ...[
              ActionChip(
                label: Text(chip),
                onPressed: _sending ? null : () => _handleSendText(chip),
              ),
              const SizedBox(width: KwSpacing.xs),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildComposer(BuildContext context, HouseholdStrings hStrings) {
    final cs = Theme.of(context).colorScheme;
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(KwSpacing.sm),
      decoration: BoxDecoration(
        color: cs.surfaceContainerLow,
        border: Border(top: BorderSide(color: cs.outlineVariant)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (_recordingVoice)
            Padding(
              padding: const EdgeInsets.only(bottom: KwSpacing.xs),
              child: Row(
                children: [
                  Icon(Icons.fiber_manual_record_rounded,
                      size: 14, color: theme.kwColors.safety.accent),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      '${hStrings.voiceNoteRecording} (0:${_voiceSeconds.toString().padLeft(2, '0')})',
                      style: theme.textTheme.labelMedium,
                    ),
                  ),
                ],
              ),
            ),
          Row(
            children: [
              IconButton(
                tooltip: hStrings.attachPhotoLabel,
                onPressed: _sending ? null : _attachSampleImage,
                icon: const Icon(Icons.photo_camera_outlined),
              ),
              IconButton(
                tooltip: hStrings.shareLocationLabel,
                onPressed: _sending ? null : _shareLocationPin,
                icon: const Icon(Icons.location_on_outlined),
              ),
              Expanded(
                child: TextField(
                  controller: _composerController,
                  enabled: !_sending,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _handleSendText(),
                  decoration: InputDecoration(
                    hintText: hStrings.typeMessageHint,
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: KwSpacing.sm,
                      vertical: KwSpacing.sm,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: KwSpacing.xxs),
              IconButton(
                tooltip: _recordingVoice
                    ? 'Stop and send voice note'
                    : 'Record voice note',
                onPressed: _sending ? null : _toggleVoiceNote,
                icon: Icon(
                  _recordingVoice
                      ? Icons.stop_circle_rounded
                      : Icons.mic_none_rounded,
                  color: _recordingVoice
                      ? theme.kwColors.safety.accent
                      : cs.onSurfaceVariant,
                ),
              ),
              FilledButton(
                onPressed: _sending ? null : () => _handleSendText(),
                child: _sending
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(hStrings.sendLabel),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
