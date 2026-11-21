import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';

/// User roles defined in Contract §3.
enum KwRole {
  centreAdmin('centre_admin'),
  technician('technician'),
  partsCentre('parts_centre'),
  brand('brand'),
  platform('platform'),
  household('household');

  const KwRole(this.wireValue);

  final String wireValue;

  static KwRole fromWire(String? value) {
    for (final role in KwRole.values) {
      if (role.wireValue == value) return role;
    }
    return KwRole.centreAdmin;
  }
}

/// Metadata for one of the 9 seeded Keepwell service centres (Contract §3).
class KwCentreIdentity {
  const KwCentreIdentity({
    required this.key,
    required this.name,
    required this.locality,
    required this.brandsSummary,
  });

  final String key;
  final String name;
  final String locality;
  final String brandsSummary;
}

/// Authenticated user session holding identity claims and bearer token.
class KwUserSession {
  const KwUserSession({
    required this.uid,
    required this.email,
    required this.role,
    this.centreId,
    this.centreKey,
    this.technicianId,
    this.partsCentreId,
    this.brandId,
    this.householdId,
    required this.idToken,
    this.displayName,
  });

  factory KwUserSession.fromJson(Map<String, dynamic> json) {
    return KwUserSession(
      uid: (json['uid'] ?? '').toString(),
      email: (json['email'] ?? '').toString(),
      role: KwRole.fromWire(json['role']?.toString()),
      centreId: json['centre_id']?.toString(),
      centreKey: json['centre_key']?.toString(),
      technicianId: json['technician_id']?.toString(),
      partsCentreId: json['parts_centre_id']?.toString(),
      brandId: json['brand_id']?.toString(),
      householdId: json['household_id']?.toString(),
      idToken: (json['id_token'] ?? '').toString(),
      displayName: json['display_name']?.toString(),
    );
  }

  final String uid;
  final String email;
  final KwRole role;
  final String? centreId;
  final String? centreKey;
  final String? technicianId;
  final String? partsCentreId;
  final String? brandId;
  final String? householdId;
  final String idToken;
  final String? displayName;

  Map<String, dynamic> toJson() => {
        'uid': uid,
        'email': email,
        'role': role.wireValue,
        'centre_id': centreId,
        'centre_key': centreKey,
        'technician_id': technicianId,
        'parts_centre_id': partsCentreId,
        'brand_id': brandId,
        'household_id': householdId,
        'id_token': idToken,
        'display_name': displayName,
      };

  KwUserSession copyWith({
    String? uid,
    String? email,
    KwRole? role,
    String? centreId,
    String? centreKey,
    String? technicianId,
    String? partsCentreId,
    String? brandId,
    String? householdId,
    String? idToken,
    String? displayName,
  }) {
    return KwUserSession(
      uid: uid ?? this.uid,
      email: email ?? this.email,
      role: role ?? this.role,
      centreId: centreId ?? this.centreId,
      centreKey: centreKey ?? this.centreKey,
      technicianId: technicianId ?? this.technicianId,
      partsCentreId: partsCentreId ?? this.partsCentreId,
      brandId: brandId ?? this.brandId,
      householdId: householdId ?? this.householdId,
      idToken: idToken ?? this.idToken,
      displayName: displayName ?? this.displayName,
    );
  }
}

/// Demo & Firebase Auth emulator helper covering all 9 centres and roles
/// defined in Contract §3.
class KwAuthHelper {
  KwAuthHelper({
    required this.config,
    http.Client? httpClient,
  }) : _http = httpClient ?? http.Client();

  final KwConfig config;
  final http.Client _http;

  /// Canonical 9 service centres from Contract §3.
  static const List<KwCentreIdentity> demoCentres = [
    KwCentreIdentity(
      key: 'c_av',
      name: 'Aerovane Authorised Service, Gachibowli',
      locality: 'Gachibowli',
      brandsSummary: 'Aerovane (authorised)',
    ),
    KwCentreIdentity(
      key: 'c_zn',
      name: 'Zenith Care Hub, Kondapur',
      locality: 'Kondapur',
      brandsSummary: 'Zenith (authorised)',
    ),
    KwCentreIdentity(
      key: 'c_fw',
      name: 'Frost and Wave Service Point, Kukatpally',
      locality: 'Kukatpally',
      brandsSummary: 'Frostline, Wavecrest (authorised)',
    ),
    KwCentreIdentity(
      key: 'c_cc',
      name: 'Cool Craft Appliance Services, Madhapur',
      locality: 'Madhapur',
      brandsSummary: 'Aerovane, Frostline, Wavecrest, Zenith (independent)',
    ),
    KwCentreIdentity(
      key: 'c_aq',
      name: 'AquaCare RO and Geyser Services, Manikonda',
      locality: 'Manikonda',
      brandsSummary: 'Heatwell, Purelo (authorised)',
    ),
    KwCentreIdentity(
      key: 'c_mh',
      name: 'Metro Home Appliance Care, Miyapur',
      locality: 'Miyapur',
      brandsSummary: 'Five brands (independent)',
    ),
    KwCentreIdentity(
      key: 'c_ip',
      name: 'InstallPro Mounting Services, Tolichowki',
      locality: 'Tolichowki',
      brandsSummary: 'Aerovane, Zenith (installation only)',
    ),
    KwCentreIdentity(
      key: 'c_ls',
      name: 'Lakeshore Service Centre, Jubilee Hills',
      locality: 'Jubilee Hills',
      brandsSummary: 'Wavecrest (authorised), others independent',
    ),
    KwCentreIdentity(
      key: 'c_hw',
      name: 'Heatwell Authorised Service, Banjara Hills',
      locality: 'Banjara Hills',
      brandsSummary: 'Heatwell (authorised)',
    ),
  ];

  static const List<String> demoBrandKeys = [
    'aerovane',
    'frostline',
    'wavecrest',
    'zenith',
    'heatwell',
    'purelo',
  ];

  /// Returns the centre admin and technician personas for a given [centreKey].
  static List<KwUserSession> demoPersonasForCentre(
    String centreKey, {
    String? centreId,
  }) {
    final centre = demoCentres.firstWhere(
      (c) => c.key == centreKey,
      orElse: () => demoCentres[2],
    );
    return [
      KwUserSession(
        uid: 'demo-console-$centreKey',
        email: 'console.$centreKey@keepwell.demo',
        role: KwRole.centreAdmin,
        centreId: centreId,
        centreKey: centreKey,
        idToken: 'demo-token-console-$centreKey',
        displayName: '${centre.name} Admin',
      ),
      KwUserSession(
        uid: 'demo-tech1-$centreKey',
        email: 'tech1.$centreKey@keepwell.demo',
        role: KwRole.technician,
        centreId: centreId,
        centreKey: centreKey,
        technicianId: 'tech1_$centreKey',
        idToken: 'demo-token-tech1-$centreKey',
        displayName: 'Technician 1 (${centre.locality})',
      ),
      KwUserSession(
        uid: 'demo-tech2-$centreKey',
        email: 'tech2.$centreKey@keepwell.demo',
        role: KwRole.technician,
        centreId: centreId,
        centreKey: centreKey,
        technicianId: 'tech2_$centreKey',
        idToken: 'demo-token-tech2-$centreKey',
        displayName: 'Technician 2 (${centre.locality})',
      ),
    ];
  }

  /// Complete roster of demo personas across all 9 centres, parts, brand, and platform.
  static List<KwUserSession> get allDemoPersonas {
    final result = <KwUserSession>[];
    for (final centre in demoCentres) {
      result.addAll(demoPersonasForCentre(centre.key));
    }
    result.add(
      const KwUserSession(
        uid: 'demo-parts',
        email: 'parts.demo@keepwell.demo',
        role: KwRole.partsCentre,
        partsCentreId: 'parts_centre_demo',
        idToken: 'demo-token-parts',
        displayName: 'Parts Centre Operator',
      ),
    );
    for (final brandKey in demoBrandKeys) {
      final title = brandKey[0].toUpperCase() + brandKey.substring(1);
      result.add(
        KwUserSession(
          uid: 'demo-brand-$brandKey',
          email: 'brand.$brandKey@keepwell.demo',
          role: KwRole.brand,
          brandId: brandKey,
          idToken: 'demo-token-brand-$brandKey',
          displayName: '$title Brand Portal',
        ),
      );
    }
    result.add(
      const KwUserSession(
        uid: 'demo-platform',
        email: 'platform@keepwell.demo',
        role: KwRole.platform,
        idToken: 'demo-token-platform',
        displayName: 'Keepwell Platform Admin',
      ),
    );
    return List<KwUserSession>.unmodifiable(result);
  }

  /// Finds a demo persona by exact email (case-insensitive).
  static KwUserSession? findPersonaByEmail(String email) {
    final lower = email.trim().toLowerCase();
    for (final persona in allDemoPersonas) {
      if (persona.email.toLowerCase() == lower) {
        return persona;
      }
    }
    return null;
  }

  /// Signs in a demo persona.
  ///
  /// When [KwConfig.useAuthEmulator] is true, attempts to sign in via the
  /// Firebase Auth Emulator REST endpoint (`accounts:signInWithPassword`) and
  /// attaches the emulator ID token; if the emulator is unreachable in local
  /// demo mode, returns the deterministic demo session so UI flows never block.
  Future<KwUserSession> signInDemoPersona(
    String email, {
    String password = 'keepwell-demo-password',
  }) async {
    final base = findPersonaByEmail(email) ??
        KwUserSession(
          uid: 'demo-${email.hashCode.abs()}',
          email: email,
          role: KwRole.centreAdmin,
          centreKey: 'c_fw',
          idToken: 'demo-token-${email.hashCode.abs()}',
          displayName: email,
        );

    if (!config.useAuthEmulator && config.firebaseApiKey.trim().isEmpty) {
      return base;
    }

    try {
      final Uri uri;
      if (config.useAuthEmulator) {
        final host = config.firebaseAuthEmulatorHost.trim();
        final prefix = host.startsWith('http://') || host.startsWith('https://')
            ? host
            : 'http://$host';
        uri = Uri.parse(
          '$prefix/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=fake-api-key',
        );
      } else {
        uri = Uri.parse(
          'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${config.firebaseApiKey.trim()}',
        );
      }
      final resp = await _http
          .post(
            uri,
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode({
              'email': email,
              'password': password,
              'returnSecureToken': true,
            }),
          )
          .timeout(const Duration(seconds: 6));

      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        final token = data['idToken']?.toString();
        final localId = data['localId']?.toString();
        if (token != null && token.isNotEmpty) {
          return base.copyWith(
            uid: localId ?? base.uid,
            idToken: token,
          );
        }
      }
    } catch (_) {
      // Fall back to local deterministic demo session when emulator isn't running.
    }

    return base;
  }

  void close() {
    _http.close();
  }
}
