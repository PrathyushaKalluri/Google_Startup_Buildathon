// Immutable, strongly-typed Dart models for Keepwell Contract §5.1, §6, and §8.
//
// All `fromJson` factories map snake_case JSON keys to camelCase Dart fields
// and safely ignore unknown fields for forward compatibility (Contract §8).

String _str(dynamic value, [String fallback = '']) =>
    value == null ? fallback : value.toString();

String? _strOrNull(dynamic value) => value?.toString();

int _int(dynamic value, [int fallback = 0]) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value) ?? fallback;
  return fallback;
}

int? _intOrNull(dynamic value) {
  if (value == null) return null;
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value);
  return null;
}

double _double(dynamic value, [double fallback = 0.0]) {
  if (value is double) return value;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value) ?? fallback;
  return fallback;
}

double? _doubleOrNull(dynamic value) {
  if (value == null) return null;
  if (value is double) return value;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

bool _bool(dynamic value, [bool fallback = false]) {
  if (value is bool) return value;
  if (value is String) {
    final lower = value.toLowerCase();
    if (lower == 'true' || lower == 't' || lower == '1') return true;
    if (lower == 'false' || lower == 'f' || lower == '0') return false;
  }
  if (value is num) return value != 0;
  return fallback;
}

List<String> _strList(dynamic value) {
  if (value is List) {
    return List<String>.unmodifiable(value.map((e) => e.toString()));
  }
  return const [];
}

Map<String, dynamic> _map(dynamic value) {
  if (value is Map<String, dynamic>) {
    return Map<String, dynamic>.unmodifiable(value);
  }
  if (value is Map) {
    return Map<String, dynamic>.unmodifiable(
      value.map((k, v) => MapEntry(k.toString(), v)),
    );
  }
  return const {};
}

List<Map<String, dynamic>> _mapList(dynamic value) {
  if (value is List) {
    return List<Map<String, dynamic>>.unmodifiable(
      value.whereType<Map>().map(_map),
    );
  }
  return const [];
}

List<T> _typedList<T>(
  dynamic value,
  T Function(Map<String, dynamic>) parser,
) {
  if (value is List) {
    return List<T>.unmodifiable(
      value.whereType<Map>().map((e) => parser(_map(e))),
    );
  }
  return const [];
}

/// Household summary embedded in [TicketCard] (Contract §5.1).
class HouseholdRef {
  const HouseholdRef({
    required this.id,
    required this.displayName,
    required this.language,
    required this.pincode,
    required this.locality,
    required this.addressLine,
    required this.verifiedVia,
    required this.linkedCentresCount,
  });

  factory HouseholdRef.fromJson(Map<String, dynamic> json) {
    return HouseholdRef(
      id: _str(json['id']),
      displayName: _str(json['display_name']),
      language: _str(json['language'], 'en'),
      pincode: _str(json['pincode']),
      locality: _str(json['locality']),
      addressLine: _str(json['address_line']),
      verifiedVia: _str(json['verified_via']),
      linkedCentresCount: _int(json['linked_centres_count'], 1),
    );
  }

  final String id;
  final String displayName;
  final String language;
  final String pincode;
  final String locality;
  final String addressLine;
  final String verifiedVia;
  final int linkedCentresCount;

  Map<String, dynamic> toJson() => {
        'id': id,
        'display_name': displayName,
        'language': language,
        'pincode': pincode,
        'locality': locality,
        'address_line': addressLine,
        'verified_via': verifiedVia,
        'linked_centres_count': linkedCentresCount,
      };
}

/// Appliance summary embedded in [TicketCard] (Contract §5.1).
class ApplianceRef {
  const ApplianceRef({
    required this.id,
    required this.brand,
    required this.categoryCode,
    this.modelCode,
    this.serialMasked,
    required this.identityStatus,
    this.purchaseDate,
    this.warrantyEnd,
  });

  factory ApplianceRef.fromJson(Map<String, dynamic> json) {
    return ApplianceRef(
      id: _str(json['id']),
      brand: _str(json['brand']),
      categoryCode: _str(json['category_code']),
      modelCode: _strOrNull(json['model_code']),
      serialMasked: _strOrNull(json['serial_masked']),
      identityStatus: _str(json['identity_status'], 'unverified'),
      purchaseDate: _strOrNull(json['purchase_date']),
      warrantyEnd: _strOrNull(json['warranty_end']),
    );
  }

  final String id;
  final String brand;
  final String categoryCode;
  final String? modelCode;
  final String? serialMasked;
  final String identityStatus;
  final String? purchaseDate;
  final String? warrantyEnd;

  Map<String, dynamic> toJson() => {
        'id': id,
        'brand': brand,
        'category_code': categoryCode,
        'model_code': modelCode,
        'serial_masked': serialMasked,
        'identity_status': identityStatus,
        'purchase_date': purchaseDate,
        'warranty_end': warrantyEnd,
      };
}

/// Board-level ticket card (Contract §5.1).
class TicketCard {
  const TicketCard({
    required this.id,
    required this.centreId,
    required this.trigger,
    required this.channel,
    required this.jobType,
    required this.status,
    this.resolution,
    required this.urgencyClass,
    this.neededBy,
    required this.safetyFlag,
    this.safetyReason,
    required this.entitlement,
    required this.household,
    this.appliance,
    required this.complaintSummary,
    required this.language,
    required this.createdAt,
    required this.updatedAt,
    required this.flags,
  });

  factory TicketCard.fromJson(Map<String, dynamic> json) {
    return TicketCard(
      id: _str(json['id']),
      centreId: _str(json['centre_id']),
      trigger: _str(json['trigger']),
      channel: _str(json['channel']),
      jobType: _str(json['job_type'], 'repair'),
      status: _str(json['status']),
      resolution: _strOrNull(json['resolution']),
      urgencyClass: _str(json['urgency_class'], 'standard'),
      neededBy: _strOrNull(json['needed_by']),
      safetyFlag: _bool(json['safety_flag']),
      safetyReason: _strOrNull(json['safety_reason']),
      entitlement: _str(json['entitlement'], 'paid'),
      household: HouseholdRef.fromJson(_map(json['household'])),
      appliance: json['appliance'] is Map
          ? ApplianceRef.fromJson(_map(json['appliance']))
          : null,
      complaintSummary: _str(json['complaint_summary']),
      language: _str(json['language'], 'en'),
      createdAt: _str(json['created_at']),
      updatedAt: _str(json['updated_at']),
      flags: _strList(json['flags']),
    );
  }

  final String id;
  final String centreId;
  final String trigger;
  final String channel;
  final String jobType;
  final String status;
  final String? resolution;
  final String urgencyClass;
  final String? neededBy;
  final bool safetyFlag;
  final String? safetyReason;
  final String entitlement;
  final HouseholdRef household;
  final ApplianceRef? appliance;
  final String complaintSummary;
  final String language;
  final String createdAt;
  final String updatedAt;
  final List<String> flags;

  Map<String, dynamic> toJson() => {
        'id': id,
        'centre_id': centreId,
        'trigger': trigger,
        'channel': channel,
        'job_type': jobType,
        'status': status,
        'resolution': resolution,
        'urgency_class': urgencyClass,
        'needed_by': neededBy,
        'safety_flag': safetyFlag,
        'safety_reason': safetyReason,
        'entitlement': entitlement,
        'household': household.toJson(),
        'appliance': appliance?.toJson(),
        'complaint_summary': complaintSummary,
        'language': language,
        'created_at': createdAt,
        'updated_at': updatedAt,
        'flags': flags,
      };
}

/// KB source citation (Contract §5.1).
class Citation {
  const Citation({
    required this.docTitle,
    this.page,
    this.uri,
    required this.snippet,
  });

  factory Citation.fromJson(Map<String, dynamic> json) {
    return Citation(
      docTitle: _str(json['doc_title']),
      page: _intOrNull(json['page']),
      uri: _strOrNull(json['uri']),
      snippet: _str(json['snippet']),
    );
  }

  final String docTitle;
  final int? page;
  final String? uri;
  final String snippet;

  Map<String, dynamic> toJson() => {
        'doc_title': docTitle,
        'page': page,
        'uri': uri,
        'snippet': snippet,
      };
}

/// Structured case summary card (Contract §5.1).
class CaseCard {
  const CaseCard({
    required this.summary,
    required this.symptoms,
    required this.errorCodes,
    required this.whatWasTried,
    required this.safetyNotes,
    required this.identityNotes,
    required this.sources,
  });

  factory CaseCard.fromJson(Map<String, dynamic> json) {
    return CaseCard(
      summary: _str(json['summary']),
      symptoms: _strList(json['symptoms']),
      errorCodes: _strList(json['error_codes']),
      whatWasTried: _strList(json['what_was_tried']),
      safetyNotes: _str(json['safety_notes']),
      identityNotes: _str(json['identity_notes']),
      sources: _typedList(json['sources'], Citation.fromJson),
    );
  }

  final String summary;
  final List<String> symptoms;
  final List<String> errorCodes;
  final List<String> whatWasTried;
  final String safetyNotes;
  final String identityNotes;
  final List<Citation> sources;

  Map<String, dynamic> toJson() => {
        'summary': summary,
        'symptoms': symptoms,
        'error_codes': errorCodes,
        'what_was_tried': whatWasTried,
        'safety_notes': safetyNotes,
        'identity_notes': identityNotes,
        'sources': sources.map((e) => e.toJson()).toList(),
      };
}

/// Urgency assessment record (Contract §5.1).
class UrgencyAssessment {
  const UrgencyAssessment({
    required this.urgencyClass,
    required this.ruleCodes,
    required this.facts,
    required this.assessedBy,
    required this.reason,
    required this.protectiveStepsSent,
    required this.createdAt,
  });

  factory UrgencyAssessment.fromJson(Map<String, dynamic> json) {
    return UrgencyAssessment(
      urgencyClass: _str(json['class'], 'standard'),
      ruleCodes: _strList(json['rule_codes']),
      facts: _map(json['facts']),
      assessedBy: _str(json['assessed_by'], 'agent'),
      reason: _str(json['reason']),
      protectiveStepsSent: _bool(json['protective_steps_sent']),
      createdAt: _str(json['created_at']),
    );
  }

  final String urgencyClass;
  final List<String> ruleCodes;
  final Map<String, dynamic> facts;
  final String assessedBy;
  final String reason;
  final bool protectiveStepsSent;
  final String createdAt;

  Map<String, dynamic> toJson() => {
        'class': urgencyClass,
        'rule_codes': ruleCodes,
        'facts': facts,
        'assessed_by': assessedBy,
        'reason': reason,
        'protective_steps_sent': protectiveStepsSent,
        'created_at': createdAt,
      };
}

/// Consent gate 1 or gate 2 record (Contract §5.1).
class ConsentGate {
  const ConsentGate({
    required this.gate,
    this.askedAt,
    required this.answer,
    this.choice,
    this.notAskedReason,
  });

  factory ConsentGate.fromJson(Map<String, dynamic> json) {
    return ConsentGate(
      gate: _int(json['gate'], 1),
      askedAt: _strOrNull(json['asked_at']),
      answer: _str(json['answer'], 'not_asked'),
      choice: _strOrNull(json['choice']),
      notAskedReason: _strOrNull(json['not_asked_reason']),
    );
  }

  final int gate;
  final String? askedAt;
  final String answer;
  final String? choice;
  final String? notAskedReason;

  Map<String, dynamic> toJson() => {
        'gate': gate,
        'asked_at': askedAt,
        'answer': answer,
        'choice': choice,
        'not_asked_reason': notAskedReason,
      };
}

/// Clarifying question and answer pair (Contract §5.1).
class ClarifyingQa {
  const ClarifyingQa({
    required this.seq,
    required this.question,
    this.answer,
    this.answerSource,
    this.askedAt,
  });

  factory ClarifyingQa.fromJson(Map<String, dynamic> json) {
    return ClarifyingQa(
      seq: _int(json['seq'], 1),
      question: _str(json['question']),
      answer: _strOrNull(json['answer']),
      answerSource: _strOrNull(json['answer_source']),
      askedAt: _strOrNull(json['asked_at']),
    );
  }

  final int seq;
  final String question;
  final String? answer;
  final String? answerSource;
  final String? askedAt;

  Map<String, dynamic> toJson() => {
        'seq': seq,
        'question': question,
        'answer': answer,
        'answer_source': answerSource,
        'asked_at': askedAt,
      };
}

/// Safe self-fix attempt record (Contract §5.1).
class FixAttempt {
  const FixAttempt({
    required this.id,
    required this.catalogueCode,
    required this.title,
    required this.offeredAt,
    required this.stepsDone,
    required this.ofSteps,
    required this.outcome,
    required this.householdReport,
    required this.observedOnVideo,
  });

  factory FixAttempt.fromJson(Map<String, dynamic> json) {
    return FixAttempt(
      id: _str(json['id']),
      catalogueCode: _str(json['catalogue_code']),
      title: _str(json['title']),
      offeredAt: _str(json['offered_at']),
      stepsDone: _int(json['steps_done']),
      ofSteps: _int(json['of']),
      outcome: _str(json['outcome']),
      householdReport: _str(json['household_report']),
      observedOnVideo: _bool(json['observed_on_video']),
    );
  }

  final String id;
  final String catalogueCode;
  final String title;
  final String offeredAt;
  final int stepsDone;
  final int ofSteps;
  final String outcome;
  final String householdReport;
  final bool observedOnVideo;

  Map<String, dynamic> toJson() => {
        'id': id,
        'catalogue_code': catalogueCode,
        'title': title,
        'offered_at': offeredAt,
        'steps_done': stepsDone,
        'of': ofSteps,
        'outcome': outcome,
        'household_report': householdReport,
        'observed_on_video': observedOnVideo,
      };
}

/// Single diagnostic fault hypothesis (Contract §5.1).
class DiagnosisHypothesis {
  const DiagnosisHypothesis({
    required this.faultKey,
    required this.label,
    required this.probability,
    required this.evidence,
    required this.citations,
  });

  factory DiagnosisHypothesis.fromJson(Map<String, dynamic> json) {
    return DiagnosisHypothesis(
      faultKey: _str(json['fault_key']),
      label: _str(json['label']),
      probability: _double(json['probability']),
      evidence: _strList(json['evidence']),
      citations: _typedList(json['citations'], Citation.fromJson),
    );
  }

  final String faultKey;
  final String label;
  final double probability;
  final List<String> evidence;
  final List<Citation> citations;

  Map<String, dynamic> toJson() => {
        'fault_key': faultKey,
        'label': label,
        'probability': probability,
        'evidence': evidence,
        'citations': citations.map((e) => e.toJson()).toList(),
      };
}

/// Diagnosis bundle (Contract §5.1).
class Diagnosis {
  const Diagnosis({
    required this.hypotheses,
    required this.abstained,
    this.reason,
    this.rerunOf,
    required this.modelVersion,
  });

  factory Diagnosis.fromJson(Map<String, dynamic> json) {
    return Diagnosis(
      hypotheses: _typedList(json['hypotheses'], DiagnosisHypothesis.fromJson),
      abstained: _bool(json['abstained']),
      reason: _strOrNull(json['reason']),
      rerunOf: _strOrNull(json['rerun_of']),
      modelVersion: _str(json['model_version']),
    );
  }

  final List<DiagnosisHypothesis> hypotheses;
  final bool abstained;
  final String? reason;
  final String? rerunOf;
  final String modelVersion;

  Map<String, dynamic> toJson() => {
        'hypotheses': hypotheses.map((e) => e.toJson()).toList(),
        'abstained': abstained,
        'reason': reason,
        'rerun_of': rerunOf,
        'model_version': modelVersion,
      };
}

/// Catalogue-verified part required in a [VisitPlan] (Contract §5.1 & §11).
class VisitPlanPart {
  const VisitPlanPart({
    required this.partNo,
    required this.name,
    required this.probability,
    required this.quantity,
    required this.sourceLadder,
    required this.ready,
  });

  factory VisitPlanPart.fromJson(Map<String, dynamic> json) {
    return VisitPlanPart(
      partNo: _str(json['part_no']),
      name: _str(json['name']),
      probability: _double(json['probability']),
      quantity: _int(json['quantity'], 1),
      sourceLadder: _str(json['source_ladder'], 'centre'),
      ready: _bool(json['ready']),
    );
  }

  final String partNo;
  final String name;
  final double probability;
  final int quantity;
  final String sourceLadder;
  final bool ready;

  Map<String, dynamic> toJson() => {
        'part_no': partNo,
        'name': name,
        'probability': probability,
        'quantity': quantity,
        'source_ladder': sourceLadder,
        'ready': ready,
      };
}

/// Technician visit plan (Contract §5.1).
class VisitPlan {
  const VisitPlan({
    required this.id,
    required this.version,
    required this.triggerReason,
    required this.alreadyTried,
    required this.requiredSkills,
    required this.estDurationP50Min,
    required this.estDurationP80Min,
    required this.toolsNeeded,
    required this.requiresSafetyCert,
    required this.parts,
    required this.accessNotes,
    required this.confidence,
  });

  factory VisitPlan.fromJson(Map<String, dynamic> json) {
    return VisitPlan(
      id: _str(json['id']),
      version: _int(json['version'], 1),
      triggerReason: _str(json['trigger_reason']),
      alreadyTried: _strList(json['already_tried']),
      requiredSkills: _strList(json['required_skills']),
      estDurationP50Min: _int(json['est_duration_p50_min']),
      estDurationP80Min: _int(json['est_duration_p80_min']),
      toolsNeeded: _strList(json['tools_needed']),
      requiresSafetyCert: _strList(json['requires_safety_cert']),
      parts: _typedList(json['parts'], VisitPlanPart.fromJson),
      accessNotes: _str(json['access_notes']),
      confidence: _double(json['confidence']),
    );
  }

  final String id;
  final int version;
  final String triggerReason;
  final List<String> alreadyTried;
  final List<String> requiredSkills;
  final int estDurationP50Min;
  final int estDurationP80Min;
  final List<String> toolsNeeded;
  final List<String> requiresSafetyCert;
  final List<VisitPlanPart> parts;
  final String accessNotes;
  final double confidence;

  Map<String, dynamic> toJson() => {
        'id': id,
        'version': version,
        'trigger_reason': triggerReason,
        'already_tried': alreadyTried,
        'required_skills': requiredSkills,
        'est_duration_p50_min': estDurationP50Min,
        'est_duration_p80_min': estDurationP80Min,
        'tools_needed': toolsNeeded,
        'requires_safety_cert': requiresSafetyCert,
        'parts': parts.map((e) => e.toJson()).toList(),
        'access_notes': accessNotes,
        'confidence': confidence,
      };
}

/// 6-factor assignment score breakdown (weights: 30, 25, 20, 15, 5, 5).
class ScoreBreakdown {
  const ScoreBreakdown({
    required this.fixConfidence,
    required this.partsReadiness,
    required this.timeToVisit,
    required this.routeCost,
    required this.reliability,
    required this.householdFit,
  });

  factory ScoreBreakdown.fromJson(Map<String, dynamic> json) {
    return ScoreBreakdown(
      fixConfidence: _double(json['fix_confidence']),
      partsReadiness: _double(json['parts_readiness']),
      timeToVisit: _double(json['time_to_visit']),
      routeCost: _double(json['route_cost']),
      reliability: _double(json['reliability']),
      householdFit: _double(json['household_fit']),
    );
  }

  final double fixConfidence;
  final double partsReadiness;
  final double timeToVisit;
  final double routeCost;
  final double reliability;
  final double householdFit;

  Map<String, dynamic> toJson() => {
        'fix_confidence': fixConfidence,
        'parts_readiness': partsReadiness,
        'time_to_visit': timeToVisit,
        'route_cost': routeCost,
        'reliability': reliability,
        'household_fit': householdFit,
      };
}

/// Scored technician assignment candidate (Contract §5.1).
class AssignmentCandidate {
  const AssignmentCandidate({
    required this.technicianId,
    required this.name,
    required this.rank,
    required this.score,
    required this.scoreBreakdown,
    required this.slotStart,
    required this.slotEnd,
    required this.outcome,
    required this.chosenBy,
    this.overrideReason,
    required this.why,
  });

  factory AssignmentCandidate.fromJson(Map<String, dynamic> json) {
    return AssignmentCandidate(
      technicianId: _str(json['technician_id']),
      name: _str(json['name']),
      rank: _int(json['rank'], 1),
      score: _double(json['score']),
      scoreBreakdown: ScoreBreakdown.fromJson(_map(json['score_breakdown'])),
      slotStart: _str(json['slot_start']),
      slotEnd: _str(json['slot_end']),
      outcome: _str(json['outcome'], 'proposed'),
      chosenBy: _str(json['chosen_by'], 'agent'),
      overrideReason: _strOrNull(json['override_reason']),
      why: _str(json['why']),
    );
  }

  final String technicianId;
  final String name;
  final int rank;
  final double score;
  final ScoreBreakdown scoreBreakdown;
  final String slotStart;
  final String slotEnd;
  final String outcome;
  final String chosenBy;
  final String? overrideReason;
  final String why;

  Map<String, dynamic> toJson() => {
        'technician_id': technicianId,
        'name': name,
        'rank': rank,
        'score': score,
        'score_breakdown': scoreBreakdown.toJson(),
        'slot_start': slotStart,
        'slot_end': slotEnd,
        'outcome': outcome,
        'chosen_by': chosenBy,
        'override_reason': overrideReason,
        'why': why,
      };
}

/// Proposed appointment slot with price band in paise (Contract §5.1).
class SlotProposal {
  const SlotProposal({
    required this.slotStart,
    required this.slotEnd,
    required this.priceLowPaise,
    required this.priceHighPaise,
    required this.shownAt,
    required this.accepted,
  });

  factory SlotProposal.fromJson(Map<String, dynamic> json) {
    return SlotProposal(
      slotStart: _str(json['slot_start']),
      slotEnd: _str(json['slot_end']),
      priceLowPaise: _int(json['price_low_paise']),
      priceHighPaise: _int(json['price_high_paise']),
      shownAt: _str(json['shown_at']),
      accepted: _bool(json['accepted']),
    );
  }

  final String slotStart;
  final String slotEnd;
  final int priceLowPaise;
  final int priceHighPaise;
  final String shownAt;
  final bool accepted;

  Map<String, dynamic> toJson() => {
        'slot_start': slotStart,
        'slot_end': slotEnd,
        'price_low_paise': priceLowPaise,
        'price_high_paise': priceHighPaise,
        'shown_at': shownAt,
        'accepted': accepted,
      };
}

/// Single line item in a [Quote] (Contract §5.1).
class QuoteLine {
  const QuoteLine({
    required this.kind,
    required this.description,
    required this.amountPaise,
    required this.payer,
  });

  factory QuoteLine.fromJson(Map<String, dynamic> json) {
    return QuoteLine(
      kind: _str(json['kind']),
      description: _str(json['description']),
      amountPaise: _int(json['amount_paise']),
      payer: _str(json['payer'], 'household'),
    );
  }

  final String kind;
  final String description;
  final int amountPaise;
  final String payer;

  Map<String, dynamic> toJson() => {
        'kind': kind,
        'description': description,
        'amount_paise': amountPaise,
        'payer': payer,
      };
}

/// Estimate or firm quote in paise (Contract §5.1).
class Quote {
  const Quote({
    required this.id,
    required this.version,
    required this.quoteType,
    required this.lines,
    required this.totalPaise,
    required this.householdPaise,
    required this.coveredPaise,
    this.approvedAt,
    this.approvalMethod,
    this.variancePct,
  });

  factory Quote.fromJson(Map<String, dynamic> json) {
    return Quote(
      id: _str(json['id']),
      version: _int(json['version'], 1),
      quoteType: _str(json['quote_type'], 'estimate'),
      lines: _typedList(json['lines'], QuoteLine.fromJson),
      totalPaise: _int(json['total_paise']),
      householdPaise: _int(json['household_paise']),
      coveredPaise: _int(json['covered_paise']),
      approvedAt: _strOrNull(json['approved_at']),
      approvalMethod: _strOrNull(json['approval_method']),
      variancePct: _doubleOrNull(json['variance_pct']),
    );
  }

  final String id;
  final int version;
  final String quoteType;
  final List<QuoteLine> lines;
  final int totalPaise;
  final int householdPaise;
  final int coveredPaise;
  final String? approvedAt;
  final String? approvalMethod;
  final double? variancePct;

  Map<String, dynamic> toJson() => {
        'id': id,
        'version': version,
        'quote_type': quoteType,
        'lines': lines.map((e) => e.toJson()).toList(),
        'total_paise': totalPaise,
        'household_paise': householdPaise,
        'covered_paise': coveredPaise,
        'approved_at': approvedAt,
        'approval_method': approvalMethod,
        if (variancePct != null) 'variance_pct': variancePct,
      };
}

/// Part used in a technician debrief (Contract §5.1).
class DebriefPartUsed {
  const DebriefPartUsed({
    required this.partNo,
    required this.quantity,
  });

  factory DebriefPartUsed.fromJson(Map<String, dynamic> json) {
    return DebriefPartUsed(
      partNo: _str(json['part_no']),
      quantity: _int(json['quantity'], 1),
    );
  }

  final String partNo;
  final int quantity;

  Map<String, dynamic> toJson() => {
        'part_no': partNo,
        'quantity': quantity,
      };
}

/// Structured fields extracted from a technician voice debrief (Contract §5.1).
class DebriefExtracted {
  const DebriefExtracted({
    required this.faultFound,
    required this.workDone,
    required this.partsUsed,
    required this.adviceForHousehold,
    required this.applianceNotes,
    required this.followUpNeeded,
  });

  factory DebriefExtracted.fromJson(Map<String, dynamic> json) {
    return DebriefExtracted(
      faultFound: _str(json['fault_found']),
      workDone: _str(json['work_done']),
      partsUsed: _typedList(json['parts_used'], DebriefPartUsed.fromJson),
      adviceForHousehold: _str(json['advice_for_household']),
      applianceNotes: _str(json['appliance_notes']),
      followUpNeeded: _bool(json['follow_up_needed']),
    );
  }

  final String faultFound;
  final String workDone;
  final List<DebriefPartUsed> partsUsed;
  final String adviceForHousehold;
  final String applianceNotes;
  final bool followUpNeeded;

  Map<String, dynamic> toJson() => {
        'fault_found': faultFound,
        'work_done': workDone,
        'parts_used': partsUsed.map((e) => e.toJson()).toList(),
        'advice_for_household': adviceForHousehold,
        'appliance_notes': applianceNotes,
        'follow_up_needed': followUpNeeded,
      };
}

/// Technician close-out voice debrief (Contract §5.1 & §11).
class Debrief {
  const Debrief({
    required this.id,
    required this.visitId,
    required this.status,
    required this.language,
    required this.transcript,
    required this.extracted,
    required this.unresolved,
    this.confirmedAt,
  });

  factory Debrief.fromJson(Map<String, dynamic> json) {
    return Debrief(
      id: _str(json['id']),
      visitId: _str(json['visit_id']),
      status: _str(json['status'], 'processing'),
      language: _str(json['language'], 'en'),
      transcript: _str(json['transcript']),
      extracted: DebriefExtracted.fromJson(_map(json['extracted'])),
      unresolved: _strList(json['unresolved']),
      confirmedAt: _strOrNull(json['confirmed_at']),
    );
  }

  final String id;
  final String visitId;
  final String status;
  final String language;
  final String transcript;
  final DebriefExtracted extracted;
  final List<String> unresolved;
  final String? confirmedAt;

  Map<String, dynamic> toJson() => {
        'id': id,
        'visit_id': visitId,
        'status': status,
        'language': language,
        'transcript': transcript,
        'extracted': extracted.toJson(),
        'unresolved': unresolved,
        'confirmed_at': confirmedAt,
      };
}

/// Google Pay transaction info block (Contract §5.1).
class GooglePayTransactionInfo {
  const GooglePayTransactionInfo({
    required this.currencyCode,
    required this.totalPriceStatus,
    required this.totalPrice,
  });

  factory GooglePayTransactionInfo.fromJson(Map<String, dynamic> json) {
    return GooglePayTransactionInfo(
      currencyCode: _str(json['currency_code'], 'INR'),
      totalPriceStatus: _str(json['total_price_status'], 'FINAL'),
      totalPrice: _str(json['total_price'], '0.00'),
    );
  }

  final String currencyCode;
  final String totalPriceStatus;
  final String totalPrice;

  Map<String, dynamic> toJson() => {
        'currency_code': currencyCode,
        'total_price_status': totalPriceStatus,
        'total_price': totalPrice,
      };
}

/// Google Pay configuration block inside [PaymentIntent] (Contract §5.1).
class GooglePayConfig {
  const GooglePayConfig({
    required this.environment,
    required this.merchantName,
    required this.merchantId,
    required this.gateway,
    required this.gatewayMerchantId,
    required this.transactionInfo,
  });

  factory GooglePayConfig.fromJson(Map<String, dynamic> json) {
    return GooglePayConfig(
      environment: _str(json['environment'], 'TEST'),
      merchantName: _str(json['merchant_name']),
      merchantId: _str(json['merchant_id']),
      gateway: _str(json['gateway']),
      gatewayMerchantId: _str(json['gateway_merchant_id']),
      transactionInfo:
          GooglePayTransactionInfo.fromJson(_map(json['transaction_info'])),
    );
  }

  final String environment;
  final String merchantName;
  final String merchantId;
  final String gateway;
  final String gatewayMerchantId;
  final GooglePayTransactionInfo transactionInfo;

  Map<String, dynamic> toJson() => {
        'environment': environment,
        'merchant_name': merchantName,
        'merchant_id': merchantId,
        'gateway': gateway,
        'gateway_merchant_id': gatewayMerchantId,
        'transaction_info': transactionInfo.toJson(),
      };
}

/// Household payment intent (Contract §5.1).
class PaymentIntent {
  const PaymentIntent({
    required this.id,
    required this.quoteId,
    required this.amountPaise,
    required this.status,
    required this.method,
    this.upiIntentUrl,
    this.googlePay,
    this.paymentRef,
    required this.createdAt,
    required this.expiresAt,
    this.paidAt,
  });

  factory PaymentIntent.fromJson(Map<String, dynamic> json) {
    return PaymentIntent(
      id: _str(json['id']),
      quoteId: _str(json['quote_id']),
      amountPaise: _int(json['amount_paise']),
      status: _str(json['status'], 'created'),
      method: _str(json['method'], 'upi_intent'),
      upiIntentUrl: _strOrNull(json['upi_intent_url']),
      googlePay: json['google_pay'] is Map
          ? GooglePayConfig.fromJson(_map(json['google_pay']))
          : null,
      paymentRef: _strOrNull(json['payment_ref']),
      createdAt: _str(json['created_at']),
      expiresAt: _str(json['expires_at']),
      paidAt: _strOrNull(json['paid_at']),
    );
  }

  final String id;
  final String quoteId;
  final int amountPaise;
  final String status;
  final String method;
  final String? upiIntentUrl;
  final GooglePayConfig? googlePay;
  final String? paymentRef;
  final String createdAt;
  final String expiresAt;
  final String? paidAt;

  Map<String, dynamic> toJson() => {
        'id': id,
        'quote_id': quoteId,
        'amount_paise': amountPaise,
        'status': status,
        'method': method,
        'upi_intent_url': upiIntentUrl,
        'google_pay': googlePay?.toJson(),
        'payment_ref': paymentRef,
        'created_at': createdAt,
        'expires_at': expiresAt,
        'paid_at': paidAt,
      };
}

/// Field technician visit record (Contract §5.1).
class Visit {
  const Visit({
    required this.id,
    required this.technicianId,
    required this.plannedStart,
    required this.plannedEnd,
    this.checkInAt,
    this.checkOutAt,
    this.outcome,
    this.closureConfirmedAt,
    this.rating,
  });

  factory Visit.fromJson(Map<String, dynamic> json) {
    return Visit(
      id: _str(json['id']),
      technicianId: _str(json['technician_id']),
      plannedStart: _str(json['planned_start']),
      plannedEnd: _str(json['planned_end']),
      checkInAt: _strOrNull(json['check_in_at']),
      checkOutAt: _strOrNull(json['check_out_at']),
      outcome: _strOrNull(json['outcome']),
      closureConfirmedAt: _strOrNull(json['closure_confirmed_at']),
      rating: _intOrNull(json['rating']),
    );
  }

  final String id;
  final String technicianId;
  final String plannedStart;
  final String plannedEnd;
  final String? checkInAt;
  final String? checkOutAt;
  final String? outcome;
  final String? closureConfirmedAt;
  final int? rating;

  Map<String, dynamic> toJson() => {
        'id': id,
        'technician_id': technicianId,
        'planned_start': plannedStart,
        'planned_end': plannedEnd,
        'check_in_at': checkInAt,
        'check_out_at': checkOutAt,
        'outcome': outcome,
        'closure_confirmed_at': closureConfirmedAt,
        'rating': rating,
      };
}

/// Timeline event on a ticket or appliance history (Contract §5.1).
class TimelineEvent {
  const TimelineEvent({
    required this.at,
    required this.type,
    required this.actor,
    required this.title,
    required this.detail,
    this.ref,
  });

  factory TimelineEvent.fromJson(Map<String, dynamic> json) {
    return TimelineEvent(
      at: _str(json['at']),
      type: _str(json['type']),
      actor: _str(json['actor'], 'system'),
      title: _str(json['title']),
      detail: _str(json['detail']),
      ref: _strOrNull(json['ref']),
    );
  }

  final String at;
  final String type;
  final String actor;
  final String title;
  final String detail;
  final String? ref;

  Map<String, dynamic> toJson() => {
        'at': at,
        'type': type,
        'actor': actor,
        'title': title,
        'detail': detail,
        'ref': ref,
      };
}

/// Brand authority check result (Contract §5.1).
class AuthorityResult {
  const AuthorityResult({
    required this.level,
    required this.decision,
  });

  factory AuthorityResult.fromJson(Map<String, dynamic> json) {
    return AuthorityResult(
      level: _str(json['level'], 'independent'),
      decision: _str(json['decision'], 'proceed'),
    );
  }

  final String level;
  final String decision;

  Map<String, dynamic> toJson() => {
        'level': level,
        'decision': decision,
      };
}

/// Full ticket detail returned by `GET /v1/tickets/{id}` (Contract §5.1).
class TicketDetail {
  const TicketDetail({
    required this.card,
    required this.caseCard,
    required this.urgency,
    required this.gates,
    required this.clarifyingQa,
    required this.fixAttempts,
    required this.triedSummary,
    this.diagnosis,
    this.visitPlan,
    required this.candidates,
    required this.slotProposals,
    required this.quotes,
    required this.payments,
    this.debrief,
    this.visit,
    required this.timeline,
    required this.authority,
  });

  factory TicketDetail.fromJson(Map<String, dynamic> json) {
    return TicketDetail(
      card: TicketCard.fromJson(_map(json['card'])),
      caseCard: CaseCard.fromJson(_map(json['case_card'])),
      urgency: _typedList(json['urgency'], UrgencyAssessment.fromJson),
      gates: _typedList(json['gates'], ConsentGate.fromJson),
      clarifyingQa: _typedList(json['clarifying_qa'], ClarifyingQa.fromJson),
      fixAttempts: _typedList(json['fix_attempts'], FixAttempt.fromJson),
      triedSummary: _mapList(json['tried_summary']),
      diagnosis: json['diagnosis'] is Map
          ? Diagnosis.fromJson(_map(json['diagnosis']))
          : null,
      visitPlan: json['visit_plan'] is Map
          ? VisitPlan.fromJson(_map(json['visit_plan']))
          : null,
      candidates: _typedList(json['candidates'], AssignmentCandidate.fromJson),
      slotProposals: _typedList(json['slot_proposals'], SlotProposal.fromJson),
      quotes: _typedList(json['quotes'], Quote.fromJson),
      payments: _typedList(json['payments'], PaymentIntent.fromJson),
      debrief: json['debrief'] is Map
          ? Debrief.fromJson(_map(json['debrief']))
          : null,
      visit:
          json['visit'] is Map ? Visit.fromJson(_map(json['visit'])) : null,
      timeline: _typedList(json['timeline'], TimelineEvent.fromJson),
      authority: AuthorityResult.fromJson(_map(json['authority'])),
    );
  }

  final TicketCard card;
  final CaseCard caseCard;
  final List<UrgencyAssessment> urgency;
  final List<ConsentGate> gates;
  final List<ClarifyingQa> clarifyingQa;
  final List<FixAttempt> fixAttempts;
  final List<Map<String, dynamic>> triedSummary;
  final Diagnosis? diagnosis;
  final VisitPlan? visitPlan;
  final List<AssignmentCandidate> candidates;
  final List<SlotProposal> slotProposals;
  final List<Quote> quotes;
  final List<PaymentIntent> payments;
  final Debrief? debrief;
  final Visit? visit;
  final List<TimelineEvent> timeline;
  final AuthorityResult authority;

  Map<String, dynamic> toJson() => {
        'card': card.toJson(),
        'case_card': caseCard.toJson(),
        'urgency': urgency.map((e) => e.toJson()).toList(),
        'gates': gates.map((e) => e.toJson()).toList(),
        'clarifying_qa': clarifyingQa.map((e) => e.toJson()).toList(),
        'fix_attempts': fixAttempts.map((e) => e.toJson()).toList(),
        'tried_summary': triedSummary,
        'diagnosis': diagnosis?.toJson(),
        'visit_plan': visitPlan?.toJson(),
        'candidates': candidates.map((e) => e.toJson()).toList(),
        'slot_proposals': slotProposals.map((e) => e.toJson()).toList(),
        'quotes': quotes.map((e) => e.toJson()).toList(),
        'payments': payments.map((e) => e.toJson()).toList(),
        'debrief': debrief?.toJson(),
        'visit': visit?.toJson(),
        'timeline': timeline.map((e) => e.toJson()).toList(),
        'authority': authority.toJson(),
      };
}

/// Live feed event in `centres/{cid}/feed` and mirrored over WS (Contract §8).
class LiveEvent {
  const LiveEvent({
    required this.id,
    required this.at,
    required this.centreId,
    this.ticketId,
    this.conversationId,
    required this.type,
    required this.actor,
    required this.title,
    required this.detail,
    required this.payload,
  });

  factory LiveEvent.fromJson(Map<String, dynamic> json) {
    // WebSocket mirrored events use `type: "event"` + `event_type: "<catalogue_type>"`.
    // Firestore feed documents use `type: "<catalogue_type>"`.
    final resolvedType = json['event_type'] != null
        ? _str(json['event_type'])
        : _str(json['type']);
    return LiveEvent(
      id: _str(json['id']),
      at: _str(json['at']),
      centreId: _str(json['centre_id']),
      ticketId: _strOrNull(json['ticket_id']),
      conversationId: _strOrNull(json['conversation_id']),
      type: resolvedType,
      actor: _str(json['actor'], 'system'),
      title: _str(json['title']),
      detail: _str(json['detail']),
      payload: _map(json['payload']),
    );
  }

  final String id;
  final String at;
  final String centreId;
  final String? ticketId;
  final String? conversationId;
  final String type;
  final String actor;
  final String title;
  final String detail;
  final Map<String, dynamic> payload;

  Map<String, dynamic> toJson() => {
        'id': id,
        'at': at,
        'centre_id': centreId,
        'ticket_id': ticketId,
        'conversation_id': conversationId,
        'type': type,
        'actor': actor,
        'title': title,
        'detail': detail,
        'payload': payload,
      };
}

/// Cursor-paginated list envelope (Contract §5).
class PagedList<T> {
  const PagedList({
    required this.items,
    this.nextCursor,
  });

  factory PagedList.fromJson(
    Map<String, dynamic> json,
    T Function(Map<String, dynamic>) itemParser,
  ) {
    return PagedList<T>(
      items: _typedList(json['items'], itemParser),
      nextCursor: _strOrNull(json['next_cursor']),
    );
  }

  final List<T> items;
  final String? nextCursor;

  bool get hasMore => nextCursor != null && nextCursor!.isNotEmpty;

  Map<String, dynamic> toJson(Map<String, dynamic> Function(T) itemToJson) => {
        'items': items.map(itemToJson).toList(),
        'next_cursor': nextCursor,
      };
}

/// Standard API error payload (Contract §5).
class KwApiError {
  const KwApiError({
    required this.code,
    required this.message,
    this.field,
    this.requestId,
  });

  factory KwApiError.fromJson(Map<String, dynamic> json) {
    final inner = json['error'] is Map ? _map(json['error']) : json;
    return KwApiError(
      code: _str(inner['code'], 'unknown_error'),
      message: _str(inner['message'], 'An unexpected error occurred'),
      field: _strOrNull(inner['field']),
      requestId: _strOrNull(inner['request_id']),
    );
  }

  final String code;
  final String message;
  final String? field;
  final String? requestId;

  Map<String, dynamic> toJson() => {
        'error': {
          'code': code,
          'message': message,
          'field': field,
          'request_id': requestId,
        },
      };

  @override
  String toString() => 'KwApiError($code: $message)';
}

/// Exception thrown by [KwApiClient] on non-2xx responses.
class KwApiException implements Exception {
  const KwApiException({
    required this.statusCode,
    required this.error,
    this.retryAfterSeconds,
  });

  final int statusCode;
  final KwApiError error;
  final int? retryAfterSeconds;

  bool get isRateLimited => statusCode == 429;
  bool get isTransient => statusCode >= 500 || statusCode == 429;

  @override
  String toString() =>
      'KwApiException(HTTP $statusCode, ${error.code}: ${error.message})';
}

/// Demo scenario entry returned by `GET /v1/admin/demo/cases`.
class DemoCase {
  const DemoCase({
    required this.caseId,
    required this.ticketId,
    required this.trigger,
    required this.channel,
    required this.centreKey,
    required this.centreId,
    required this.centreName,
    required this.urgencyClass,
    required this.safetyFlag,
    required this.stageCandidate,
    required this.summary,
  });

  factory DemoCase.fromJson(Map<String, dynamic> json) {
    return DemoCase(
      caseId: _str(json['case_id']),
      ticketId: _str(json['ticket_id']),
      trigger: _str(json['trigger']),
      channel: _str(json['channel']),
      centreKey: _str(json['centre_key']),
      centreId: _str(json['centre_id']),
      centreName: _str(json['centre_name']),
      urgencyClass: _str(json['urgency_class'], 'standard'),
      safetyFlag: _bool(json['safety_flag']),
      stageCandidate: _bool(json['stage_candidate']),
      summary: _str(json['summary']),
    );
  }

  final String caseId;
  final String ticketId;
  final String trigger;
  final String channel;
  final String centreKey;
  final String centreId;
  final String centreName;
  final String urgencyClass;
  final bool safetyFlag;
  final bool stageCandidate;
  final String summary;

  Map<String, dynamic> toJson() => {
        'case_id': caseId,
        'ticket_id': ticketId,
        'trigger': trigger,
        'channel': channel,
        'centre_key': centreKey,
        'centre_id': centreId,
        'centre_name': centreName,
        'urgency_class': urgencyClass,
        'safety_flag': safetyFlag,
        'stage_candidate': stageCandidate,
        'summary': summary,
      };
}

/// Seeded household persona returned by `GET /v1/admin/demo/households`.
class DemoHousehold {
  const DemoHousehold({
    required this.householdId,
    required this.displayName,
    required this.phoneMasked,
    required this.language,
    required this.magicToken,
    required this.centreKey,
    required this.centreId,
  });

  factory DemoHousehold.fromJson(Map<String, dynamic> json) {
    return DemoHousehold(
      householdId: _str(json['household_id']),
      displayName: _str(json['display_name']),
      phoneMasked: _str(json['phone_masked']),
      language: _str(json['language'], 'en'),
      magicToken: _str(json['magic_token']),
      centreKey: _str(json['centre_key']),
      centreId: _str(json['centre_id']),
    );
  }

  final String householdId;
  final String displayName;
  final String phoneMasked;
  final String language;
  final String magicToken;
  final String centreKey;
  final String centreId;

  Map<String, dynamic> toJson() => {
        'household_id': householdId,
        'display_name': displayName,
        'phone_masked': phoneMasked,
        'language': language,
        'magic_token': magicToken,
        'centre_key': centreKey,
        'centre_id': centreId,
      };
}

/// Centre KPI overview returned by `GET /v1/centre/overview` (Contract §5.2 & §11).
class CentreOverview {
  const CentreOverview({
    required this.centreId,
    required this.centreKey,
    required this.centreName,
    required this.openByClass,
    required this.firstTimeFix,
    required this.fvr14d,
    required this.selfFixResolution,
    required this.gateFunnel,
    required this.urgencyAgreement,
    required this.overrideRate,
    required this.partsReadyAtVisit,
    required this.jobsPerTechDay,
  });

  factory CentreOverview.fromJson(Map<String, dynamic> json) {
    final rawOpen = _map(json['open_by_class']);
    final openByClass = Map<String, int>.unmodifiable(
      rawOpen.map((k, v) => MapEntry(k, _int(v))),
    );
    final rawFunnel = _map(json['gate_funnel']);
    final gateFunnel = Map<String, int>.unmodifiable(
      rawFunnel.map((k, v) => MapEntry(k, _int(v))),
    );
    return CentreOverview(
      centreId: _str(json['centre_id']),
      centreKey: _str(json['centre_key']),
      centreName: _str(json['centre_name']),
      openByClass: openByClass,
      firstTimeFix: _double(json['first_time_fix']),
      fvr14d: _double(json['fvr_14d']),
      selfFixResolution: _double(json['self_fix_resolution']),
      gateFunnel: gateFunnel,
      urgencyAgreement: _double(json['urgency_agreement']),
      overrideRate: _double(json['override_rate']),
      partsReadyAtVisit: _double(json['parts_ready_at_visit']),
      jobsPerTechDay: _double(json['jobs_per_tech_day']),
    );
  }

  final String centreId;
  final String centreKey;
  final String centreName;
  final Map<String, int> openByClass;
  final double firstTimeFix;
  final double fvr14d;
  final double selfFixResolution;
  final Map<String, int> gateFunnel;
  final double urgencyAgreement;
  final double overrideRate;
  final double partsReadyAtVisit;
  final double jobsPerTechDay;

  Map<String, dynamic> toJson() => {
        'centre_id': centreId,
        'centre_key': centreKey,
        'centre_name': centreName,
        'open_by_class': openByClass,
        'first_time_fix': firstTimeFix,
        'fvr_14d': fvr14d,
        'self_fix_resolution': selfFixResolution,
        'gate_funnel': gateFunnel,
        'urgency_agreement': urgencyAgreement,
        'override_rate': overrideRate,
        'parts_ready_at_visit': partsReadyAtVisit,
        'jobs_per_tech_day': jobsPerTechDay,
      };
}

/// Technician roster entry returned by `GET /v1/centre/technicians`.
class TechnicianSummary {
  const TechnicianSummary({
    required this.id,
    required this.centreId,
    required this.centreKey,
    required this.name,
    required this.languages,
    required this.shiftStart,
    required this.shiftEnd,
    required this.vehicleType,
    required this.safetyCerts,
    required this.active,
    required this.status,
    this.lastLocation,
    this.lastPingAt,
    required this.skills,
    required this.metrics,
  });

  factory TechnicianSummary.fromJson(Map<String, dynamic> json) {
    Map<String, double>? loc;
    if (json['last_location'] is Map) {
      final rawLoc = _map(json['last_location']);
      if (rawLoc['lat'] != null && rawLoc['lon'] != null) {
        loc = Map<String, double>.unmodifiable({
          'lat': _double(rawLoc['lat']),
          'lon': _double(rawLoc['lon']),
        });
      }
    }
    return TechnicianSummary(
      id: _str(json['id']),
      centreId: _str(json['centre_id']),
      centreKey: _str(json['centre_key']),
      name: _str(json['name']),
      languages: _strList(json['languages']),
      shiftStart: _str(json['shift_start']),
      shiftEnd: _str(json['shift_end']),
      vehicleType: _str(json['vehicle_type']),
      safetyCerts: _strList(json['safety_certs']),
      active: _bool(json['active'], true),
      status: _str(json['status'], 'available'),
      lastLocation: loc,
      lastPingAt: _strOrNull(json['last_ping_at']),
      skills: _mapList(json['skills']),
      metrics: _map(json['metrics']),
    );
  }

  final String id;
  final String centreId;
  final String centreKey;
  final String name;
  final List<String> languages;
  final String shiftStart;
  final String shiftEnd;
  final String vehicleType;
  final List<String> safetyCerts;
  final bool active;
  final String status;
  final Map<String, double>? lastLocation;
  final String? lastPingAt;
  final List<Map<String, dynamic>> skills;
  final Map<String, dynamic> metrics;

  Map<String, dynamic> toJson() => {
        'id': id,
        'centre_id': centreId,
        'centre_key': centreKey,
        'name': name,
        'languages': languages,
        'shift_start': shiftStart,
        'shift_end': shiftEnd,
        'vehicle_type': vehicleType,
        'safety_certs': safetyCerts,
        'active': active,
        'status': status,
        'last_location': lastLocation,
        'last_ping_at': lastPingAt,
        'skills': skills,
        'metrics': metrics,
      };
}

/// Safe self-fix catalogue entry returned by `GET /v1/safefix`.
class SafeFixEntry {
  const SafeFixEntry({
    required this.id,
    required this.code,
    required this.categoryCode,
    this.brand,
    required this.faultFamily,
    required this.title,
    required this.symptomTerms,
    required this.steps,
    required this.stepCount,
    required this.estMinutes,
    required this.reversible,
    required this.needsTools,
    required this.opensPanel,
    required this.worstCase,
    required this.reviewerName,
    required this.status,
    required this.effectiveness,
  });

  factory SafeFixEntry.fromJson(Map<String, dynamic> json) {
    final rawSteps = json['steps'];
    final steps = rawSteps is List
        ? List<dynamic>.unmodifiable(rawSteps)
        : const <dynamic>[];
    return SafeFixEntry(
      id: _str(json['id']),
      code: _str(json['code']),
      categoryCode: _str(json['category_code']),
      brand: _strOrNull(json['brand']),
      faultFamily: _str(json['fault_family']),
      title: _str(json['title']),
      symptomTerms: _strList(json['symptom_terms']),
      steps: steps,
      stepCount: _int(json['step_count'], steps.length),
      estMinutes: _int(json['est_minutes'], 10),
      reversible: _bool(json['reversible'], true),
      needsTools: _bool(json['needs_tools']),
      opensPanel: _bool(json['opens_panel']),
      worstCase: _str(json['worst_case']),
      reviewerName: _str(json['reviewer_name']),
      status: _str(json['status'], 'active'),
      effectiveness: _map(json['effectiveness']),
    );
  }

  final String id;
  final String code;
  final String categoryCode;
  final String? brand;
  final String faultFamily;
  final String title;
  final List<String> symptomTerms;
  final List<dynamic> steps;
  final int stepCount;
  final int estMinutes;
  final bool reversible;
  final bool needsTools;
  final bool opensPanel;
  final String worstCase;
  final String reviewerName;
  final String status;
  final Map<String, dynamic> effectiveness;

  Map<String, dynamic> toJson() => {
        'id': id,
        'code': code,
        'category_code': categoryCode,
        'brand': brand,
        'fault_family': faultFamily,
        'title': title,
        'symptom_terms': symptomTerms,
        'steps': steps,
        'step_count': stepCount,
        'est_minutes': estMinutes,
        'reversible': reversible,
        'needs_tools': needsTools,
        'opens_panel': opensPanel,
        'worst_case': worstCase,
        'reviewer_name': reviewerName,
        'status': status,
        'effectiveness': effectiveness,
      };
}

/// Household WhatsApp thread message (Contract §6).
class WhatsAppMessage {
  const WhatsAppMessage({
    required this.id,
    required this.direction,
    required this.type,
    this.text,
    this.mediaUrl,
    this.template,
    required this.at,
    this.ticketId,
    required this.status,
  });

  factory WhatsAppMessage.fromJson(Map<String, dynamic> json) {
    return WhatsAppMessage(
      id: _str(json['id']),
      direction: _str(json['direction'], 'in'),
      type: _str(json['type'], 'text'),
      text: _strOrNull(json['text']),
      mediaUrl: _strOrNull(json['media_url']),
      template: _strOrNull(json['template']),
      at: _str(json['at']),
      ticketId: _strOrNull(json['ticket_id']),
      status: _str(json['status'], 'sent'),
    );
  }

  final String id;
  final String direction;
  final String type;
  final String? text;
  final String? mediaUrl;
  final String? template;
  final String at;
  final String? ticketId;
  final String status;

  Map<String, dynamic> toJson() => {
        'id': id,
        'direction': direction,
        'type': type,
        'text': text,
        'media_url': mediaUrl,
        'template': template,
        'at': at,
        'ticket_id': ticketId,
        'status': status,
      };
}

/// Single turn in `centres/{cid}/conversations/{conv}/turns/{turn}` (Contract §6).
class ConversationTurn {
  const ConversationTurn({
    required this.id,
    required this.at,
    required this.speaker,
    required this.text,
    required this.lang,
    required this.isFinal,
    required this.kind,
  });

  factory ConversationTurn.fromJson(Map<String, dynamic> json) {
    return ConversationTurn(
      id: _str(json['id']),
      at: _str(json['at']),
      speaker: _str(json['speaker'], 'agent'),
      text: _str(json['text']),
      lang: _str(json['lang'], 'en'),
      isFinal: _bool(json['final'], true),
      kind: _str(json['kind'], 'speech'),
    );
  }

  final String id;
  final String at;
  final String speaker;
  final String text;
  final String lang;
  final bool isFinal;
  final String kind;

  Map<String, dynamic> toJson() => {
        'id': id,
        'at': at,
        'speaker': speaker,
        'text': text,
        'lang': lang,
        'final': isFinal,
        'kind': kind,
      };
}
