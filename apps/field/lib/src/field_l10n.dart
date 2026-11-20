import 'package:flutter/widgets.dart';
import 'package:kw_ui/kw_ui.dart';

/// Field-specific localized labels complementing [KwStrings] for `en`, `hi`, `te`.
@immutable
class FieldStrings {
  const FieldStrings({
    required this.appTitle,
    required this.signInSubtitle,
    required this.emailLabel,
    required this.signInButton,
    required this.signOutTooltip,
    required this.roleTechnician,
    required this.rolePartsCentre,
    required this.todaysJobsTitle,
    required this.partsRequestsTab,
    required this.partsStockTab,
    required this.onlineStatus,
    required this.offlineNoQueue,
    required this.syncNow,
    required this.simulateOffline,
    required this.alreadyTriedTitle,
    required this.hypothesesTitle,
    required this.toolsAndPartsTitle,
    required this.checkInAction,
    required this.partsUsedAction,
    required this.evidenceAction,
    required this.firmQuoteTitle,
    required this.debriefTitle,
    required this.otpClosureTitle,
    required this.privacyLoggedNotice,
    required this.addressHiddenNotice,
    required this.openInMaps,
    required this.acceptAction,
    required this.markReadyAction,
    required this.handoverAction,
    required this.saveStockAction,
  });

  final String appTitle;
  final String signInSubtitle;
  final String emailLabel;
  final String signInButton;
  final String signOutTooltip;
  final String roleTechnician;
  final String rolePartsCentre;
  final String todaysJobsTitle;
  final String partsRequestsTab;
  final String partsStockTab;
  final String onlineStatus;
  final String offlineNoQueue;
  final String syncNow;
  final String simulateOffline;
  final String alreadyTriedTitle;
  final String hypothesesTitle;
  final String toolsAndPartsTitle;
  final String checkInAction;
  final String partsUsedAction;
  final String evidenceAction;
  final String firmQuoteTitle;
  final String debriefTitle;
  final String otpClosureTitle;
  final String privacyLoggedNotice;
  final String addressHiddenNotice;
  final String openInMaps;
  final String acceptAction;
  final String markReadyAction;
  final String handoverAction;
  final String saveStockAction;

  static const FieldStrings en = FieldStrings(
    appTitle: 'Keepwell Field',
    signInSubtitle: 'Sign in as a field technician or parts centre operator.',
    emailLabel: 'Work email',
    signInButton: 'Sign in',
    signOutTooltip: 'Sign out',
    roleTechnician: 'Technician',
    rolePartsCentre: 'Parts Centre',
    todaysJobsTitle: "Today's Jobs",
    partsRequestsTab: 'Requests',
    partsStockTab: 'Stock',
    onlineStatus: 'Online',
    offlineNoQueue: 'Offline — changes will queue locally',
    syncNow: 'Sync now',
    simulateOffline: 'Offline mode',
    alreadyTriedTitle: 'Already Tried (Do Not Repeat)',
    hypothesesTitle: 'Probable Fault Hypotheses',
    toolsAndPartsTitle: 'Tools & Parts Ladder',
    checkInAction: 'Check in with location',
    partsUsedAction: 'Record parts used',
    evidenceAction: 'Upload photo / video',
    firmQuoteTitle: 'Firm Quote Composer',
    debriefTitle: 'Spoken Close-Out Debrief',
    otpClosureTitle: 'Household OTP Closure',
    privacyLoggedNotice: 'Contact reads are logged for household privacy.',
    addressHiddenNotice: 'Address and phone are masked until the slot is confirmed.',
    openInMaps: 'Open in Google Maps',
    acceptAction: 'Accept',
    markReadyAction: 'Mark Ready',
    handoverAction: 'Handover',
    saveStockAction: 'Save stock update',
  );

  static const FieldStrings hi = FieldStrings(
    appTitle: 'कीपवेल फील्ड',
    signInSubtitle: 'फील्ड तकनीशियन या पार्ट्स सेंटर ऑपरेटर के रूप में साइन इन करें।',
    emailLabel: 'कार्य ईमेल',
    signInButton: 'साइन इन करें',
    signOutTooltip: 'साइन आउट',
    roleTechnician: 'तकनीशियन',
    rolePartsCentre: 'पार्ट्स सेंटर',
    todaysJobsTitle: 'आज के कार्य',
    partsRequestsTab: 'अनुरोध',
    partsStockTab: 'स्टॉक',
    onlineStatus: 'ऑनलाइन',
    offlineNoQueue: 'ऑफ़लाइन — बदलाव स्थानीय रूप से कतार में रहेंगे',
    syncNow: 'अभी सिंक करें',
    simulateOffline: 'ऑफ़लाइन मोड',
    alreadyTriedTitle: 'पहले से आज़माया गया (दोहराएँ नहीं)',
    hypothesesTitle: 'संभावित खराबी के कारण',
    toolsAndPartsTitle: 'उपकरण और पुर्ज़ों की सूची',
    checkInAction: 'लोकेशन के साथ चेक-इन',
    partsUsedAction: 'उपयोग किए गए पुर्ज़े दर्ज करें',
    evidenceAction: 'फ़ोटो / वीडियो अपलोड करें',
    firmQuoteTitle: 'अंतिम कोट निर्माता',
    debriefTitle: 'वॉइस समापन डीब्रीफ़',
    otpClosureTitle: 'ग्राहक ओटीपी समापन',
    privacyLoggedNotice: 'ग्राहक गोपनीयता के लिए संपर्क देखने का रिकॉर्ड रखा जाता है।',
    addressHiddenNotice: 'स्लॉट की पुष्टि होने तक पता और फ़ोन छिपे रहते हैं।',
    openInMaps: 'गूगल मैप्स में खोलें',
    acceptAction: 'स्वीकार करें',
    markReadyAction: 'तैयार चिह्नित करें',
    handoverAction: 'हैंडओवर करें',
    saveStockAction: 'स्टॉक अपडेट सहेजें',
  );

  static const FieldStrings te = FieldStrings(
    appTitle: 'కీప్‌వెల్ ఫీల్డ్',
    signInSubtitle: 'ఫీల్డ్ టెక్నీషియన్ లేదా పార్ట్స్ సెంటర్ ఆపరేటర్‌గా సైన్ ఇన్ చేయండి.',
    emailLabel: 'పని ఇమెయిల్',
    signInButton: 'సైన్ ఇన్',
    signOutTooltip: 'సైన్ అవుట్',
    roleTechnician: 'టెక్నీషియన్',
    rolePartsCentre: 'పార్ట్స్ సెంటర్',
    todaysJobsTitle: 'నేటి పనులు',
    partsRequestsTab: 'అభ్యర్థనలు',
    partsStockTab: 'స్టాక్',
    onlineStatus: 'ఆన్‌లైన్',
    offlineNoQueue: 'ఆఫ్‌లైన్ — మార్పులు స్థానికంగా క్యూలో ఉంటాయి',
    syncNow: 'ఇప్పుడే సింక్ చేయండి',
    simulateOffline: 'ఆఫ్‌లైన్ మోడ్',
    alreadyTriedTitle: 'ఇప్పటికే ప్రయత్నించినవి (మళ్లీ చేయవద్దు)',
    hypothesesTitle: 'సంభావ్య లోప అంచనాలు',
    toolsAndPartsTitle: 'పరికరాలు & భాగాల జాబితా',
    checkInAction: 'లొకేషన్‌తో చెక్-ఇన్',
    partsUsedAction: 'వాడిన భాగాలను నమోదు చేయండి',
    evidenceAction: 'ఫోటో / వీడియో అప్‌లోడ్',
    firmQuoteTitle: 'తుది కోట్ తయారీ',
    debriefTitle: 'వాయిస్ ముగింపు డీబ్రీఫ్',
    otpClosureTitle: 'గృహస్థుడి ఓటీపీ ముగింపు',
    privacyLoggedNotice: 'గృహ గోప్యత కోసం కాంటాక్ట్ వీక్షణలు లాగ్ చేయబడతాయి.',
    addressHiddenNotice: 'స్లాట్ నిర్ధారించే వరకు చిరునామా మరియు ఫోన్ దాచబడతాయి.',
    openInMaps: 'గూగుల్ మ్యాప్స్‌లో తెరవండి',
    acceptAction: 'అంగీకరించండి',
    markReadyAction: 'సిద్ధంగా గుర్తించండి',
    handoverAction: 'హ్యాండోవర్ చేయండి',
    saveStockAction: 'స్టాక్ అప్‌డేట్ సేవ్ చేయండి',
  );

  static FieldStrings of(BuildContext context) {
    final code = KwStrings.of(context).languageCode;
    return switch (code) {
      'hi' => hi,
      'te' => te,
      _ => en,
    };
  }
}
