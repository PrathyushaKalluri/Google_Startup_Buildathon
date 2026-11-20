import 'package:flutter/widgets.dart';

/// Runtime-switchable UI chrome strings for English (`en`), Hindi (`hi`),
/// and Telugu (`te`).
///
/// Agent-emitted household copy is always displayed verbatim from the backend
/// (Shared Contract §9); these strings cover UI chrome, labels, and badges.
@immutable
class KwStrings {
  const KwStrings({
    required this.languageCode,
    required this.languageName,
    required this.urgencySafety,
    required this.urgencyUrgent,
    required this.urgencyStandard,
    required this.urgencyPlanned,
    required this.safetyStopNotice,
    required this.consentGateTitle,
    required this.gate1Label,
    required this.gate2Label,
    required this.gateAnswerYes,
    required this.gateAnswerNo,
    required this.gateAnswerSilence,
    required this.gateAnswerNotAsked,
    required this.gateChoiceContinueHere,
    required this.gateChoiceSwitchToVideo,
    required this.gateSkippedSafetyReason,
    required this.gateSkippedNonRepairReason,
    required this.stepIntake,
    required this.stepTriage,
    required this.stepSelfFix,
    required this.stepAssigned,
    required this.stepVisit,
    required this.stepClosed,
    required this.confidenceLabel,
    required this.abstainedTitle,
    required this.abstainedDefaultReason,
    required this.sourcePagePrefix,
    required this.sourceSnippetTitle,
    required this.closeLabel,
    required this.scoreTotalLabel,
    required this.factorFixConfidence,
    required this.factorPartsReadiness,
    required this.factorTimeToVisit,
    required this.factorRouteCost,
    required this.factorReliability,
    required this.factorHouseholdFit,
    required this.scoreBreakdownToggle,
    required this.speakerAgent,
    required this.speakerHousehold,
    required this.modalityVoice,
    required this.modalityVideo,
    required this.modalityText,
    required this.transcriptInterim,
    required this.callMute,
    required this.callUnmute,
    required this.callSpeaker,
    required this.callSwitchToVideo,
    required this.callEnd,
    required this.recommendedSlotBadge,
    required this.alternativeSlotBadge,
    required this.routeStaticFallbackBadge,
    required this.payerBrand,
    required this.payerPlan,
    required this.payerHousehold,
    required this.needsChecking,
    required this.needsCheckingExcludedHint,
    required this.otpHeading,
    required this.otpDigitLabel,
    required this.fvr14Label,
    required this.fvr14Subtitle,
    required this.neededByPrefix,
    required this.unreadLabel,
    required this.retryLabel,
    required this.emptyDefaultTitle,
    required this.emptyDefaultBody,
    required this.errorDefaultTitle,
    required this.errorDefaultBody,
    required this.loadingLabel,
  });

  final String languageCode;
  final String languageName;

  // Urgency classes
  final String urgencySafety;
  final String urgencyUrgent;
  final String urgencyStandard;
  final String urgencyPlanned;
  final String safetyStopNotice;

  // Consent gates
  final String consentGateTitle;
  final String gate1Label;
  final String gate2Label;
  final String gateAnswerYes;
  final String gateAnswerNo;
  final String gateAnswerSilence;
  final String gateAnswerNotAsked;
  final String gateChoiceContinueHere;
  final String gateChoiceSwitchToVideo;
  final String gateSkippedSafetyReason;
  final String gateSkippedNonRepairReason;

  // 6-step status stepper
  final String stepIntake;
  final String stepTriage;
  final String stepSelfFix;
  final String stepAssigned;
  final String stepVisit;
  final String stepClosed;

  // Confidence meter & citations
  final String confidenceLabel;
  final String abstainedTitle;
  final String abstainedDefaultReason;
  final String sourcePagePrefix;
  final String sourceSnippetTitle;
  final String closeLabel;

  // Candidate score bar (6 factors)
  final String scoreTotalLabel;
  final String factorFixConfidence;
  final String factorPartsReadiness;
  final String factorTimeToVisit;
  final String factorRouteCost;
  final String factorReliability;
  final String factorHouseholdFit;
  final String scoreBreakdownToggle;

  // Transcript & call controls
  final String speakerAgent;
  final String speakerHousehold;
  final String modalityVoice;
  final String modalityVideo;
  final String modalityText;
  final String transcriptInterim;
  final String callMute;
  final String callUnmute;
  final String callSpeaker;
  final String callSwitchToVideo;
  final String callEnd;

  // Slots, routes, money, OTP, FVR
  final String recommendedSlotBadge;
  final String alternativeSlotBadge;
  final String routeStaticFallbackBadge;
  final String payerBrand;
  final String payerPlan;
  final String payerHousehold;
  final String needsChecking;
  final String needsCheckingExcludedHint;
  final String otpHeading;
  final String otpDigitLabel;
  final String fvr14Label;
  final String fvr14Subtitle;

  // Case card & states
  final String neededByPrefix;
  final String unreadLabel;
  final String retryLabel;
  final String emptyDefaultTitle;
  final String emptyDefaultBody;
  final String errorDefaultTitle;
  final String errorDefaultBody;
  final String loadingLabel;

  static const KwStrings en = KwStrings(
    languageCode: 'en',
    languageName: 'English',
    urgencySafety: 'Safety',
    urgencyUrgent: 'Urgent',
    urgencyStandard: 'Standard',
    urgencyPlanned: 'Planned',
    safetyStopNotice:
        'Please stop using it and switch it off at the wall. A technician will come as soon as possible.',
    consentGateTitle: 'Self-fix consent',
    gate1Label: 'Gate 1 · Safe self-fix',
    gate2Label: 'Gate 2 · Call or video',
    gateAnswerYes: 'Yes',
    gateAnswerNo: 'No',
    gateAnswerSilence: 'No response (treated as No)',
    gateAnswerNotAsked: 'Not asked',
    gateChoiceContinueHere: 'Carry on here',
    gateChoiceSwitchToVideo: 'Switch to video',
    gateSkippedSafetyReason: 'Skipped — safety path active',
    gateSkippedNonRepairReason: 'Skipped — non-repair job',
    stepIntake: 'Intake',
    stepTriage: 'Triage',
    stepSelfFix: 'Self-fix',
    stepAssigned: 'Assigned',
    stepVisit: 'Visit',
    stepClosed: 'Closed',
    confidenceLabel: 'Diagnostic confidence',
    abstainedTitle: 'Insufficient evidence — abstained',
    abstainedDefaultReason:
        'More inspection is needed before confirming a fault.',
    sourcePagePrefix: 'p.',
    sourceSnippetTitle: 'Manual excerpt',
    closeLabel: 'Close',
    scoreTotalLabel: 'Match score',
    factorFixConfidence: 'Fix confidence',
    factorPartsReadiness: 'Parts readiness',
    factorTimeToVisit: 'Time to visit',
    factorRouteCost: 'Route cost',
    factorReliability: 'Reliability',
    factorHouseholdFit: 'Household fit',
    scoreBreakdownToggle: 'Score breakdown',
    speakerAgent: 'Service Centre',
    speakerHousehold: 'Household',
    modalityVoice: 'Voice',
    modalityVideo: 'Video',
    modalityText: 'Message',
    transcriptInterim: 'Listening…',
    callMute: 'Mute',
    callUnmute: 'Unmute',
    callSpeaker: 'Speaker',
    callSwitchToVideo: 'Switch to video',
    callEnd: 'End call',
    recommendedSlotBadge: 'Recommended',
    alternativeSlotBadge: 'Alternative',
    routeStaticFallbackBadge: 'Estimated route',
    payerBrand: 'Brand',
    payerPlan: 'Plan',
    payerHousehold: 'Household',
    needsChecking: 'Needs checking',
    needsCheckingExcludedHint: 'Excluded from quote total until verified',
    otpHeading: 'Household closure OTP',
    otpDigitLabel: 'OTP digit',
    fvr14Label: 'FVR-14',
    fvr14Subtitle: 'First-visit resolution (14 days)',
    neededByPrefix: 'Needed by',
    unreadLabel: 'Unread update',
    retryLabel: 'Try again',
    emptyDefaultTitle: 'Nothing here yet',
    emptyDefaultBody: 'New updates will appear here automatically.',
    errorDefaultTitle: 'Could not load this view',
    errorDefaultBody: 'Please check your connection and try again.',
    loadingLabel: 'Loading content',
  );

  static const KwStrings hi = KwStrings(
    languageCode: 'hi',
    languageName: 'हिन्दी',
    urgencySafety: 'सुरक्षा',
    urgencyUrgent: 'तत्काल',
    urgencyStandard: 'सामान्य',
    urgencyPlanned: 'नियोजित',
    safetyStopNotice:
        'कृपया इसका उपयोग बंद करें और दीवार से स्विच ऑफ कर दें। तकनीशियन जल्द से जल्द पहुँचेगा।',
    consentGateTitle: 'स्वयं जांच सहमति',
    gate1Label: 'चरण 1 · सुरक्षित स्वयं जांच',
    gate2Label: 'चरण 2 · कॉल या वीडियो',
    gateAnswerYes: 'हाँ',
    gateAnswerNo: 'नहीं',
    gateAnswerSilence: 'कोई उत्तर नहीं (नहीं माना गया)',
    gateAnswerNotAsked: 'नहीं पूछा गया',
    gateChoiceContinueHere: 'यहीं जारी रखें',
    gateChoiceSwitchToVideo: 'वीडियो पर जाएँ',
    gateSkippedSafetyReason: 'छोड़ा गया — सुरक्षा पथ सक्रिय',
    gateSkippedNonRepairReason: 'छोड़ा गया — गैर-मरम्मत कार्य',
    stepIntake: 'प्राप्ति',
    stepTriage: 'जाँच',
    stepSelfFix: 'स्वयं प्रयास',
    stepAssigned: 'आवंटित',
    stepVisit: 'विज़िट',
    stepClosed: 'पूर्ण',
    confidenceLabel: 'निदान विश्वास',
    abstainedTitle: 'पर्याप्त साक्ष्य नहीं — रोका गया',
    abstainedDefaultReason: 'खराबी की पुष्टि से पहले और जाँच आवश्यक है।',
    sourcePagePrefix: 'पृ.',
    sourceSnippetTitle: 'मैनुअल अंश',
    closeLabel: 'बंद करें',
    scoreTotalLabel: 'मिलान स्कोर',
    factorFixConfidence: 'मरम्मत विश्वास',
    factorPartsReadiness: 'पुर्जों की उपलब्धता',
    factorTimeToVisit: 'विज़िट समय',
    factorRouteCost: 'मार्ग लागत',
    factorReliability: 'विश्वसनीयता',
    factorHouseholdFit: 'घर की उपयुक्तता',
    scoreBreakdownToggle: 'स्कोर विवरण',
    speakerAgent: 'सर्विस सेंटर',
    speakerHousehold: 'ग्राहक',
    modalityVoice: 'वॉइस',
    modalityVideo: 'वीडियो',
    modalityText: 'संदेश',
    transcriptInterim: 'सुन रहे हैं…',
    callMute: 'म्यूट',
    callUnmute: 'अनम्यूट',
    callSpeaker: 'स्पीकर',
    callSwitchToVideo: 'वीडियो चालू करें',
    callEnd: 'कॉल समाप्त',
    recommendedSlotBadge: 'सुझाया गया',
    alternativeSlotBadge: 'विकल्प',
    routeStaticFallbackBadge: 'अनुमानित मार्ग',
    payerBrand: 'ब्रांड',
    payerPlan: 'प्लान',
    payerHousehold: 'ग्राहक',
    needsChecking: 'जाँच आवश्यक',
    needsCheckingExcludedHint: 'सत्यापन तक कोट योग से बाहर',
    otpHeading: 'समापन ओटीपी (OTP)',
    otpDigitLabel: 'ओटीपी अंक',
    fvr14Label: 'FVR-14',
    fvr14Subtitle: 'पहली विज़िट समाधान (14 दिन)',
    neededByPrefix: 'अपेक्षित समय',
    unreadLabel: 'अपठित अपडेट',
    retryLabel: 'पुनः प्रयास करें',
    emptyDefaultTitle: 'अभी यहाँ कुछ नहीं है',
    emptyDefaultBody: 'नए अपडेट यहाँ अपने आप दिखाई देंगे।',
    errorDefaultTitle: 'यह दृश्य लोड नहीं हो सका',
    errorDefaultBody: 'कृपया कनेक्शन जाँचें और पुनः प्रयास करें।',
    loadingLabel: 'सामग्री लोड हो रही है',
  );

  static const KwStrings te = KwStrings(
    languageCode: 'te',
    languageName: 'తెలుగు',
    urgencySafety: 'భద్రత',
    urgencyUrgent: 'అత్యవసరం',
    urgencyStandard: 'సాధారణం',
    urgencyPlanned: 'ప్రణాళిక',
    safetyStopNotice:
        'దయచేసి దీనిని ఉపయోగించడం ఆపి, గోడ స్విచ్ ఆఫ్ చేయండి. టెక్నీషియన్ వీలైనంత త్వరగా వస్తారు.',
    consentGateTitle: 'స్వీయ-పరిష్కార అనుమతి',
    gate1Label: 'దశ 1 · సురక్షిత స్వీయ పరిష్కారం',
    gate2Label: 'దశ 2 · కాల్ లేదా వీడియో',
    gateAnswerYes: 'అవును',
    gateAnswerNo: 'కాదు',
    gateAnswerSilence: 'స్పందన లేదు (కాదుగా పరిగణించబడింది)',
    gateAnswerNotAsked: 'అడగలేదు',
    gateChoiceContinueHere: 'ఇక్కడే కొనసాగండి',
    gateChoiceSwitchToVideo: 'వీడియోకు మారండి',
    gateSkippedSafetyReason: 'వదిలివేయబడింది — భద్రతా మార్గం అమలులో ఉంది',
    gateSkippedNonRepairReason: 'వదిలివేయబడింది — మరమ్మతు కాని పని',
    stepIntake: 'నమోదు',
    stepTriage: 'పరిశీలన',
    stepSelfFix: 'స్వీయ ప్రయత్నం',
    stepAssigned: 'కేటాయింపు',
    stepVisit: 'సందర్శన',
    stepClosed: 'పూర్తయింది',
    confidenceLabel: 'నిర్ధారణ నమ్మకం',
    abstainedTitle: 'తగిన ఆధారాలు లేవు — నిలిపివేయబడింది',
    abstainedDefaultReason: 'లోపాన్ని నిర్ధారించే ముందు మరింత పరిశీలన అవసరం.',
    sourcePagePrefix: 'పే.',
    sourceSnippetTitle: 'మాన్యువల్ భాగం',
    closeLabel: 'మూసివేయండి',
    scoreTotalLabel: 'సరిపోలిక స్కోర్',
    factorFixConfidence: 'మరమ్మతు నమ్మకం',
    factorPartsReadiness: 'భాగాల లభ్యత',
    factorTimeToVisit: 'సందర్శన సమయం',
    factorRouteCost: 'మార్గ వ్యయం',
    factorReliability: 'విశ్వసనీయత',
    factorHouseholdFit: 'గృహ అనుకూలత',
    scoreBreakdownToggle: 'స్కోర్ వివరాలు',
    speakerAgent: 'సర్వీస్ సెంటర్',
    speakerHousehold: 'గృహస్థుడు',
    modalityVoice: 'వాయిస్',
    modalityVideo: 'వీడియో',
    modalityText: 'సందేశం',
    transcriptInterim: 'వింటోంది…',
    callMute: 'మ్యూట్',
    callUnmute: 'అన్‌మ్యూట్',
    callSpeaker: 'స్పీకర్',
    callSwitchToVideo: 'వీడియోకు మారండి',
    callEnd: 'కాల్ ముగించు',
    recommendedSlotBadge: 'సిఫార్సు',
    alternativeSlotBadge: 'ప్రత్యామ్నాయం',
    routeStaticFallbackBadge: 'అంచనా మార్గం',
    payerBrand: 'బ్రాండ్',
    payerPlan: 'ప్లాన్',
    payerHousehold: 'గృహస్థుడు',
    needsChecking: 'పరిశీలన అవసరం',
    needsCheckingExcludedHint: 'ధృవీకరించే వరకు కోట్ మొత్తంలో చేర్చబడదు',
    otpHeading: 'ముగింపు ఓటీపీ (OTP)',
    otpDigitLabel: 'ఓటీపీ అంకె',
    fvr14Label: 'FVR-14',
    fvr14Subtitle: 'మొదటి సందర్శన పరిష్కారం (14 రోజులు)',
    neededByPrefix: 'అవసరమైన సమయం',
    unreadLabel: 'చదవని అప్‌డేట్',
    retryLabel: 'మళ్లీ ప్రయత్నించండి',
    emptyDefaultTitle: 'ఇక్కడ ఇంకా ఏమీ లేదు',
    emptyDefaultBody: 'కొత్త అప్‌డేట్లు ఇక్కడ స్వయంచాలకంగా కనిపిస్తాయి.',
    errorDefaultTitle: 'ఈ వీక్షణను లోడ్ చేయలేకపోయాము',
    errorDefaultBody: 'దయచేసి కనెక్షన్ తనిఖీ చేసి మళ్లీ ప్రయత్నించండి.',
    loadingLabel: 'లోడ్ అవుతోంది',
  );

  static KwStrings forLanguageCode(String code) {
    return switch (code.toLowerCase()) {
      'hi' => hi,
      'te' => te,
      _ => en,
    };
  }

  static KwStrings of(BuildContext context) {
    final scoped =
        context.dependOnInheritedWidgetOfExactType<KwLocaleScope>();
    if (scoped != null) {
      return scoped.strings;
    }
    final locale = Localizations.maybeLocaleOf(context);
    return forLanguageCode(locale?.languageCode ?? 'en');
  }
}

/// Provides runtime-switchable [KwStrings] to any Keepwell subtree.
class KwLocaleScope extends InheritedWidget {
  KwLocaleScope({
    super.key,
    required String languageCode,
    required super.child,
  })  : languageCode = languageCode.toLowerCase(),
        strings = KwStrings.forLanguageCode(languageCode);

  final String languageCode;
  final KwStrings strings;

  @override
  bool updateShouldNotify(covariant KwLocaleScope oldWidget) {
    return oldWidget.languageCode != languageCode;
  }
}
