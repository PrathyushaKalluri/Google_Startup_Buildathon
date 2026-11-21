import 'dart:async';

import 'package:flutter/material.dart';
import 'package:kw_client/kw_client.dart';
import 'package:kw_ui/kw_ui.dart';

/// Primary navigation destinations in the Centre Console.
enum ConsoleDestination {
  board,
  stage,
  calendar,
  overview,
  operations,
}

/// Factory for creating a [LiveCallClient], injectable for tests.
typedef LiveCallClientFactory = LiveCallClient Function(KwConfig config);

/// Central state controller for Keepwell Centre Console.
class ConsoleController extends ChangeNotifier {
  ConsoleController({
    KwConfig? config,
    KwApiClient? apiClient,
    KwAuthHelper? authHelper,
    LiveFeedRepository? liveFeedRepository,
    LiveCallClientFactory? liveCallClientFactory,
    ConsoleDestination initialDestination = ConsoleDestination.board,
    KwUserSession? initialSession,
    bool initialProjectorMode = false,
  })  : config = config ?? KwConfig.fromEnvironment(),
        _liveCallClientFactory =
            liveCallClientFactory ?? ((cfg) => LiveCallClient(config: cfg)),
        _destination = initialDestination,
        _session = initialSession,
        _projectorMode = initialProjectorMode,
        _themePreset =
            initialProjectorMode ? KwThemePreset.projector : KwThemePreset.light {
    this.authHelper = authHelper ?? KwAuthHelper(config: this.config);
    this.apiClient = apiClient ??
        KwApiClient(
          config: this.config,
          tokenProvider: () => _session?.idToken,
        );
    this.liveFeedRepository = liveFeedRepository ??
        LiveFeedRepository(
          config: this.config,
          apiClient: this.apiClient,
          tokenProvider: () => _session?.idToken,
        );
    if (_session != null) {
      unawaited(loadTickets());
      _startFeedWatch();
      _startTicketsWatch();
    }
  }

  final KwConfig config;
  late final KwApiClient apiClient;
  late final KwAuthHelper authHelper;
  late final LiveFeedRepository liveFeedRepository;
  final LiveCallClientFactory _liveCallClientFactory;

  KwUserSession? _session;
  KwThemePreset _themePreset;
  KwThemePreset _preProjectorPreset = KwThemePreset.light;
  bool _projectorMode;
  String _languageCode = 'en';
  ConsoleDestination _destination;

  List<TicketCard> _tickets = const [];
  bool _loadingTickets = false;
  String? _ticketsError;

  String? _selectedTicketId;
  TicketDetail? _selectedDetail;
  bool _loadingDetail = false;
  String? _detailError;

  List<LiveEvent> _liveFeed = const [];
  StreamSubscription<List<LiveEvent>>? _feedSub;
  StreamSubscription<List<TicketCard>>? _ticketsSub;

  KwUserSession? get session => _session;
  bool get isSignedIn => _session != null;
  KwThemePreset get themePreset => _themePreset;
  bool get projectorMode => _projectorMode;
  String get languageCode => _languageCode;
  Locale get locale => Locale(_languageCode);
  ConsoleDestination get destination => _destination;

  List<TicketCard> get tickets => _tickets;
  bool get loadingTickets => _loadingTickets;
  String? get ticketsError => _ticketsError;

  String? get selectedTicketId => _selectedTicketId;
  TicketDetail? get selectedDetail => _selectedDetail;
  bool get loadingDetail => _loadingDetail;
  String? get detailError => _detailError;

  List<LiveEvent> get liveFeed => _liveFeed;

  String get activeCentreKey => _session?.centreKey ?? 'c_fw';
  String get activeCentreId => _session?.centreId ?? '';

  LiveCallClient createLiveCallClient() => _liveCallClientFactory(config);

  void setDestination(ConsoleDestination next) {
    if (_destination == next) return;
    _destination = next;
    notifyListeners();
  }

  void setLanguage(String code) {
    final normalized = code.toLowerCase();
    if (_languageCode == normalized) return;
    _languageCode = normalized;
    notifyListeners();
  }

  void setThemePreset(KwThemePreset preset) {
    _themePreset = preset;
    _projectorMode = preset == KwThemePreset.projector;
    if (!_projectorMode) {
      _preProjectorPreset = preset;
    }
    notifyListeners();
  }

  void setProjectorMode(bool enabled) {
    if (_projectorMode == enabled) return;
    _projectorMode = enabled;
    if (enabled) {
      if (_themePreset != KwThemePreset.projector) {
        _preProjectorPreset = _themePreset;
      }
      _themePreset = KwThemePreset.projector;
    } else {
      _themePreset = _preProjectorPreset;
    }
    notifyListeners();
  }

  Future<void> signInWithEmail(
    String email, {
    String password = 'keepwell-demo-password',
  }) async {
    final signed = await authHelper.signInDemoPersona(
      email.trim(),
      password: password,
    );
    _session = signed;
    notifyListeners();
    await loadTickets();
    _startFeedWatch();
    _startTicketsWatch();
  }

  Future<void> quickSignInFrostAndWave() =>
      signInWithEmail('console.c_fw@keepwell.demo');

  void signOut() {
    _feedSub?.cancel();
    _feedSub = null;
    _ticketsSub?.cancel();
    _ticketsSub = null;
    _session = null;
    _tickets = const [];
    _selectedTicketId = null;
    _selectedDetail = null;
    _liveFeed = const [];
    notifyListeners();
  }

  void _startTicketsWatch() {
    _ticketsSub?.cancel();
    if (_session == null) return;
    final isPlatform = _session?.role == KwRole.platform;
    _ticketsSub = liveFeedRepository
        .watchTickets(
          centreId: isPlatform ? null : activeCentreId,
          centreKey: isPlatform ? null : activeCentreKey,
          pollInterval: const Duration(seconds: 3),
        )
        .listen(
          (cards) {
            if (cards.isNotEmpty) {
              final prevCount = _tickets.length;
              _tickets = sortTickets(cards);
              _loadingTickets = false;
              _ticketsError = null;
              if (_selectedTicketId == null || cards.length > prevCount) {
                unawaited(selectTicket(_tickets.first.id));
              }
              notifyListeners();
            }
          },
          onError: (_) {},
        );
  }

  void _startFeedWatch() {
    _feedSub?.cancel();
    if (_session == null) return;
    _feedSub = liveFeedRepository
        .watchFeed(
          activeCentreId,
          centreKey:
              _session?.role == KwRole.platform ? null : activeCentreKey,
          pollInterval: const Duration(seconds: 4),
        )
        .listen(
          (events) {
            _liveFeed = events;
            notifyListeners();
          },
          onError: (_) {
            // Keep existing feed items calm during transient polling errors.
          },
        );
  }

  Future<void> loadTickets({
    String? status,
    String? urgencyClass,
    String? trigger,
    String? query,
  }) async {
    _loadingTickets = true;
    _ticketsError = null;
    notifyListeners();

    try {
      final isPlatform = _session?.role == KwRole.platform;
      final page = await apiClient.listTickets(
        status: status,
        urgencyClass: urgencyClass,
        trigger: trigger,
        q: query,
        centreId: isPlatform ? null : activeCentreId,
        centreKey: isPlatform ? null : activeCentreKey,
        limit: 100,
      );
      _tickets = sortTickets(page.items);
      _loadingTickets = false;
      notifyListeners();

      if (_tickets.isNotEmpty) {
        final stillExists = _selectedTicketId != null &&
            _tickets.any((t) => t.id == _selectedTicketId);
        if (!stillExists) {
          await selectTicket(_tickets.first.id);
        }
      } else {
        _selectedTicketId = null;
        _selectedDetail = null;
        notifyListeners();
      }
    } catch (e) {
      _loadingTickets = false;
      _ticketsError = e.toString();
      notifyListeners();
    }
  }

  Future<void> selectTicket(String ticketId) async {
    _selectedTicketId = ticketId;
    _loadingDetail = true;
    _detailError = null;
    notifyListeners();

    try {
      final detail = await apiClient.getTicket(ticketId);
      if (_selectedTicketId == ticketId) {
        _selectedDetail = detail;
        _loadingDetail = false;
        notifyListeners();
      }
    } catch (e) {
      if (_selectedTicketId == ticketId) {
        _loadingDetail = false;
        _detailError = e.toString();
        notifyListeners();
      }
    }
  }

  Future<TicketDetail> reclassifyUrgency({
    required String ticketId,
    required String urgencyClass,
    required String reason,
  }) async {
    final updated = await apiClient.reclassifyUrgency(
      ticketId,
      urgencyClass: urgencyClass,
      reason: reason,
    );
    _applyUpdatedDetail(updated);
    return updated;
  }

  Future<TicketDetail> reassignTicket({
    required String ticketId,
    required String technicianId,
    required String slotStart,
    required String slotEnd,
    required String reason,
  }) async {
    final updated = await apiClient.reassignTicket(
      ticketId,
      technicianId: technicianId,
      slotStart: slotStart,
      slotEnd: slotEnd,
      reason: reason,
    );
    _applyUpdatedDetail(updated);
    return updated;
  }

  Future<TicketDetail> rerunDiagnosis(String ticketId) async {
    final updated = await apiClient.rerunDiagnosis(ticketId);
    _applyUpdatedDetail(updated);
    return updated;
  }

  Future<TicketDetail> returnToBrand({
    required String ticketId,
    required String reason,
  }) async {
    final updated = await apiClient.returnToBrand(ticketId, reason: reason);
    _applyUpdatedDetail(updated);
    return updated;
  }

  Future<TimelineEvent> sendCentreMessage({
    required String ticketId,
    required String text,
  }) async {
    final event = await apiClient.sendCentreMessage(ticketId, text: text);
    if (_selectedTicketId == ticketId) {
      await selectTicket(ticketId);
    }
    return event;
  }

  void _applyUpdatedDetail(TicketDetail updated) {
    if (_selectedTicketId == updated.card.id) {
      _selectedDetail = updated;
    }
    final nextList = _tickets
        .map((item) => item.id == updated.card.id ? updated.card : item)
        .toList();
    _tickets = sortTickets(nextList);
    notifyListeners();
  }

  /// Sorts tickets strictly: `safety` -> `urgent` -> `standard` -> `planned`,
  /// then earliest `needed_by` ascending, then `updated_at` descending.
  static List<TicketCard> sortTickets(List<TicketCard> items) {
    final copy = List<TicketCard>.from(items);
    copy.sort((a, b) {
      final ua = urgencyRank(a.urgencyClass);
      final ub = urgencyRank(b.urgencyClass);
      if (ua != ub) return ua.compareTo(ub);

      final da = parseIsoDate(a.neededBy);
      final db = parseIsoDate(b.neededBy);
      if (da != null && db != null) {
        final cmp = da.compareTo(db);
        if (cmp != 0) return cmp;
      } else if (da != null) {
        return -1;
      } else if (db != null) {
        return 1;
      }
      return b.updatedAt.compareTo(a.updatedAt);
    });
    return List<TicketCard>.unmodifiable(copy);
  }

  static int urgencyRank(String urgencyClass) {
    return switch (urgencyClass.toLowerCase()) {
      'safety' => 0,
      'urgent' => 1,
      'standard' => 2,
      'planned' => 3,
      _ => 2,
    };
  }

  static DateTime? parseIsoDate(String? raw) {
    if (raw == null || raw.trim().isEmpty) return null;
    return DateTime.tryParse(raw.trim());
  }

  static int statusToStep(String status) {
    final lower = status.toLowerCase();
    if (lower.contains('closed') || lower.contains('resolved')) return 5;
    if (lower.contains('visit') ||
        lower.contains('en_route') ||
        lower.contains('checked_in') ||
        lower.contains('in_progress')) {
      return 4;
    }
    if (lower.contains('assigned') || lower.contains('scheduled')) return 3;
    if (lower.contains('self_fix') || lower.contains('guided')) return 2;
    if (lower.contains('triage') ||
        lower.contains('diagnos') ||
        lower.contains('quote')) {
      return 1;
    }
    return 0;
  }

  @override
  void dispose() {
    _feedSub?.cancel();
    super.dispose();
  }
}
