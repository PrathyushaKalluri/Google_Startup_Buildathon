import 'package:flutter/widgets.dart';
import 'package:kw_ui/kw_ui.dart';

/// Household-specific UI chrome strings in English (`en`), Hindi (`hi`),
/// and Telugu (`te`).
///
/// Agent-emitted copy (recording notices, chat replies, captions) is always
/// rendered verbatim from the backend.
@immutable
class HouseholdStrings {
  const HouseholdStrings({
    required this.navWhatsApp,
    required this.navCall,
    required this.navVideo,
    required this.navHome,
    required this.navQuoteOtp,
    required this.zeroSignInBadge,
    required this.themeLight,
    required this.themeDark,
    required this.themeHighContrast,
    required this.whatsappSimulatorTitle,
    required this.serviceCentreLabel,
    required this.householdLabel,
    required this.sessionActiveLabel,
    required this.typeMessageHint,
    required this.sendLabel,
    required this.voiceNoteRecording,
    required this.attachPhotoLabel,
    required this.shareLocationLabel,
    required this.micPermissionTitle,
    required this.micPermissionBody,
    required this.allowMicLabel,
    required this.startCallLabel,
    required this.recordingNoticeLabel,
    required this.switchingToVideoTitle,
    required this.openVideoNowLabel,
    required this.reconnectingLabel,
    required this.reconnectNowLabel,
    required this.cameraPermissionTitle,
    required this.cameraPermissionBody,
    required this.allowCameraLabel,
    required this.denyCameraLabel,
    required this.cameraUnavailableTitle,
    required this.sendStillPhotoLabel,
    required this.stopVideoLabel,
    required this.homeMemoryTitle,
    required this.careIndexLabel,
    required this.nextDueServicesTitle,
    required this.recordedAdviceTitle,
    required this.serviceTimelineTitle,
    required this.quoteTitle,
    required this.approveQuoteLabel,
    required this.quoteApprovedBadge,
    required this.paymentBannerText,
    required this.payWithGooglePayTest,
    required this.payWithUpiIntent,
    required this.sandboxTestCardTitle,
    required this.completeTestPaymentSuccess,
    required this.completeTestPaymentFailure,
    required this.otpSectionTitle,
    required this.confirmOtpLabel,
    required this.jobClosedTitle,
    required this.jobClosedSubtitle,
  });

  final String navWhatsApp;
  final String navCall;
  final String navVideo;
  final String navHome;
  final String navQuoteOtp;
  final String zeroSignInBadge;
  final String themeLight;
  final String themeDark;
  final String themeHighContrast;
  final String whatsappSimulatorTitle;
  final String serviceCentreLabel;
  final String householdLabel;
  final String sessionActiveLabel;
  final String typeMessageHint;
  final String sendLabel;
  final String voiceNoteRecording;
  final String attachPhotoLabel;
  final String shareLocationLabel;
  final String micPermissionTitle;
  final String micPermissionBody;
  final String allowMicLabel;
  final String startCallLabel;
  final String recordingNoticeLabel;
  final String switchingToVideoTitle;
  final String openVideoNowLabel;
  final String reconnectingLabel;
  final String reconnectNowLabel;
  final String cameraPermissionTitle;
  final String cameraPermissionBody;
  final String allowCameraLabel;
  final String denyCameraLabel;
  final String cameraUnavailableTitle;
  final String sendStillPhotoLabel;
  final String stopVideoLabel;
  final String homeMemoryTitle;
  final String careIndexLabel;
  final String nextDueServicesTitle;
  final String recordedAdviceTitle;
  final String serviceTimelineTitle;
  final String quoteTitle;
  final String approveQuoteLabel;
  final String quoteApprovedBadge;
  final String paymentBannerText;
  final String payWithGooglePayTest;
  final String payWithUpiIntent;
  final String sandboxTestCardTitle;
  final String completeTestPaymentSuccess;
  final String completeTestPaymentFailure;
  final String otpSectionTitle;
  final String confirmOtpLabel;
  final String jobClosedTitle;
  final String jobClosedSubtitle;

  static const HouseholdStrings en = HouseholdStrings(
    navWhatsApp: 'WhatsApp',
    navCall: 'Voice Call',
    navVideo: 'Video Link',
    navHome: 'Home Memory',
    navQuoteOtp: 'Quote & OTP',
    zeroSignInBadge: 'Zero sign-in · Magic link',
    themeLight: 'Light',
    themeDark: 'Dark',
    themeHighContrast: 'High Contrast',
    whatsappSimulatorTitle: 'WhatsApp simulator',
    serviceCentreLabel: 'Service centre',
    householdLabel: 'Household',
    sessionActiveLabel: 'Magic-link session active',
    typeMessageHint: 'Message the service centre…',
    sendLabel: 'Send',
    voiceNoteRecording: 'Recording voice note… tap again to send',
    attachPhotoLabel: 'Attach sticker/photo',
    shareLocationLabel: 'Share location pin',
    micPermissionTitle: 'Microphone access for this voice call',
    micPermissionBody:
        'Your microphone is used only while this call is active so the service centre can hear you and show live captions.',
    allowMicLabel: 'Allow microphone',
    startCallLabel: 'Start voice call',
    recordingNoticeLabel: 'Recording notice',
    switchingToVideoTitle: 'Switching to video...',
    openVideoNowLabel: 'Open video check now',
    reconnectingLabel: 'Connection refreshed — reconnecting call…',
    reconnectNowLabel: 'Reconnect call',
    cameraPermissionTitle: 'Camera permission for guided check',
    cameraPermissionBody:
        'Your rear camera is shared only while this video check is open. You can stop video at any moment and continue on voice.',
    allowCameraLabel: 'Allow camera',
    denyCameraLabel: 'Camera unavailable / deny',
    cameraUnavailableTitle: 'Camera unavailable — send a still photo instead',
    sendStillPhotoLabel: 'Send still photo',
    stopVideoLabel: 'Stop video (continue on voice)',
    homeMemoryTitle: 'Home Memory',
    careIndexLabel: 'Care Index',
    nextDueServicesTitle: 'Next due services',
    recordedAdviceTitle: 'Recorded advice notes',
    serviceTimelineTitle: 'Append-only service timeline',
    quoteTitle: 'Estimate & firm quote',
    approveQuoteLabel: 'Approve quote',
    quoteApprovedBadge: 'Quote approved',
    paymentBannerText:
        'Payment does not close the job — only your OTP closes the repair.',
    payWithGooglePayTest: 'Google Pay (TEST)',
    payWithUpiIntent: 'Pay via UPI Intent',
    sandboxTestCardTitle: 'Sandbox payment simulator (PAYMENT_MODE=sandbox)',
    completeTestPaymentSuccess: 'Complete test payment (Success)',
    completeTestPaymentFailure: 'Complete test payment (Failure)',
    otpSectionTitle: 'Close repair with your 6-digit OTP',
    confirmOtpLabel: 'Confirm OTP & close repair',
    jobClosedTitle: 'Repair closed with your OTP',
    jobClosedSubtitle:
        'Your appliance timeline and receipt have been updated in Home Memory.',
  );

  static const HouseholdStrings hi = HouseholdStrings(
    navWhatsApp: 'व्हाट्सएप',
    navCall: 'वॉइस कॉल',
    navVideo: 'वीडियो लिंक',
    navHome: 'होम मेमोरी',
    navQuoteOtp: 'कोट व ओटीपी',
    zeroSignInBadge: 'बिना लॉग-इन · मैजिक लिंक',
    themeLight: 'लाइट',
    themeDark: 'डार्क',
    themeHighContrast: 'हाई कॉन्ट्रास्ट',
    whatsappSimulatorTitle: 'WhatsApp simulator',
    serviceCentreLabel: 'सर्विस सेंटर',
    householdLabel: 'परिवार',
    sessionActiveLabel: 'मैजिक-लिंक सत्र सक्रिय',
    typeMessageHint: 'सर्विस सेंटर को संदेश लिखें…',
    sendLabel: 'भेजें',
    voiceNoteRecording: 'वॉइस नोट रिकॉर्ड हो रहा है… भेजने के लिए फिर टैप करें',
    attachPhotoLabel: 'स्टिकर/फोटो जोड़ें',
    shareLocationLabel: 'लोकेशन पिन भेजें',
    micPermissionTitle: 'इस वॉइस कॉल के लिए माइक्रोफोन अनुमति',
    micPermissionBody:
        'आपका माइक्रोफोन केवल इस कॉल के दौरान उपयोग होता है ताकि सर्विस सेंटर आपको सुन सके और लाइव कैप्शन दिखा सके।',
    allowMicLabel: 'माइक्रोफोन की अनुमति दें',
    startCallLabel: 'वॉइस कॉल शुरू करें',
    recordingNoticeLabel: 'रिकॉर्डिंग सूचना',
    switchingToVideoTitle: 'Switching to video...',
    openVideoNowLabel: 'अभी वीडियो जाँच खोलें',
    reconnectingLabel: 'कनेक्शन रीफ्रेश हुआ — कॉल पुनः जुड़ रही है…',
    reconnectNowLabel: 'पुनः कनेक्ट करें',
    cameraPermissionTitle: 'मार्गदर्शित जाँच के लिए कैमरा अनुमति',
    cameraPermissionBody:
        'आपका कैमरा केवल इस वीडियो जाँच के दौरान साझा होता है। आप कभी भी वीडियो बंद करके वॉइस पर जारी रख सकते हैं।',
    allowCameraLabel: 'कैमरा की अनुमति दें',
    denyCameraLabel: 'कैमरा उपलब्ध नहीं / अस्वीकार',
    cameraUnavailableTitle: 'कैमरा उपलब्ध नहीं — इसके बजाय फोटो भेजें',
    sendStillPhotoLabel: 'फोटो भेजें',
    stopVideoLabel: 'Stop video (continue on voice)',
    homeMemoryTitle: 'होम मेमोरी',
    careIndexLabel: 'केयर इंडेक्स',
    nextDueServicesTitle: 'आगामी सेवाएँ',
    recordedAdviceTitle: 'दर्ज सलाह नोट्स',
    serviceTimelineTitle: 'सेवा समयरेखा',
    quoteTitle: 'अनुमान और अंतिम कोट',
    approveQuoteLabel: 'कोट स्वीकृत करें',
    quoteApprovedBadge: 'कोट स्वीकृत',
    paymentBannerText:
        'Payment does not close the job — only your OTP closes the repair.',
    payWithGooglePayTest: 'Google Pay (TEST)',
    payWithUpiIntent: 'UPI लिंक से भुगतान',
    sandboxTestCardTitle: 'सैंडबॉक्स भुगतान सिम्युलेटर (PAYMENT_MODE=sandbox)',
    completeTestPaymentSuccess: 'Complete test payment (Success)',
    completeTestPaymentFailure: 'Complete test payment (Failure)',
    otpSectionTitle: 'अपने 6-अंकीय OTP से मरम्मत बंद करें',
    confirmOtpLabel: 'OTP पुष्टि करें और बंद करें',
    jobClosedTitle: 'आपके OTP से मरम्मत पूर्ण हुई',
    jobClosedSubtitle:
        'आपकी उपकरण समयरेखा और रसीद होम मेमोरी में अपडेट कर दी गई है।',
  );

  static const HouseholdStrings te = HouseholdStrings(
    navWhatsApp: 'వాట్సాప్',
    navCall: 'వాయిస్ కాల్',
    navVideo: 'వీడియో లింక్',
    navHome: 'హోమ్ మెమరీ',
    navQuoteOtp: 'కోట్ & ఓటీపీ',
    zeroSignInBadge: 'సైన్-ఇన్ లేదు · మ్యాజిక్ లింక్',
    themeLight: 'లైట్',
    themeDark: 'డార్క్',
    themeHighContrast: 'హై కాంట్రాస్ట్',
    whatsappSimulatorTitle: 'WhatsApp simulator',
    serviceCentreLabel: 'సర్వీస్ సెంటర్',
    householdLabel: 'గృహం',
    sessionActiveLabel: 'మ్యాజిక్-లింక్ సెషన్ సక్రియం',
    typeMessageHint: 'సర్వీస్ సెంటర్‌కు సందేశం రాయండి…',
    sendLabel: 'పంపండి',
    voiceNoteRecording: 'వాయిస్ నోట్ రికార్డ్ అవుతోంది… పంపడానికి మళ్లీ నొక్కండి',
    attachPhotoLabel: 'స్టిక్కర్/ఫోటో జతచేయండి',
    shareLocationLabel: 'లొకేషన్ పిన్ పంపండి',
    micPermissionTitle: 'ఈ వాయిస్ కాల్ కోసం మైక్రోఫోన్ అనుమతి',
    micPermissionBody:
        'ఈ కాల్ జరుగుతున్నప్పుడు మాత్రమే మీ మైక్రోఫోన్ ఉపయోగించబడుతుంది.',
    allowMicLabel: 'మైక్రోఫోన్ అనుమతించండి',
    startCallLabel: 'వాయిస్ కాల్ ప్రారంభించండి',
    recordingNoticeLabel: 'రికార్డింగ్ నోటీసు',
    switchingToVideoTitle: 'Switching to video...',
    openVideoNowLabel: 'ఇప్పుడే వీడియో తనిఖీ తెరవండి',
    reconnectingLabel: 'కనెక్షన్ పునరుద్ధరించబడుతోంది…',
    reconnectNowLabel: 'మళ్లీ కనెక్ట్ చేయండి',
    cameraPermissionTitle: 'మార్గదర్శక తనిఖీ కోసం కెమెరా అనుమతి',
    cameraPermissionBody:
        'ఈ వీడియో తనిఖీ తెరిచి ఉన్నప్పుడు మాత్రమే మీ కెమెరా షేర్ అవుతుంది. ఎప్పుడైనా వీడియో ఆపి వాయిస్‌లో కొనసాగవచ్చు.',
    allowCameraLabel: 'కెమెరా అనుమతించండి',
    denyCameraLabel: 'కెమెరా అందుబాటులో లేదు / తిరస్కరించండి',
    cameraUnavailableTitle: 'కెమెరా అందుబాటులో లేదు — బదులుగా ఫోటో పంపండి',
    sendStillPhotoLabel: 'ఫోటో పంపండి',
    stopVideoLabel: 'Stop video (continue on voice)',
    homeMemoryTitle: 'హోమ్ మెమరీ',
    careIndexLabel: 'కేర్ ఇండెక్స్',
    nextDueServicesTitle: 'తదుపరి సేవలు',
    recordedAdviceTitle: 'నమోదైన సూచనలు',
    serviceTimelineTitle: 'సేవా కాలక్రమం',
    quoteTitle: 'అంచనా & తుది కోట్',
    approveQuoteLabel: 'కోట్ ఆమోదించండి',
    quoteApprovedBadge: 'కోట్ ఆమోదించబడింది',
    paymentBannerText:
        'Payment does not close the job — only your OTP closes the repair.',
    payWithGooglePayTest: 'Google Pay (TEST)',
    payWithUpiIntent: 'UPI ద్వారా చెల్లించండి',
    sandboxTestCardTitle: 'సాండ్‌బాక్స్ చెల్లింపు సిమ్యులేటర్ (PAYMENT_MODE=sandbox)',
    completeTestPaymentSuccess: 'Complete test payment (Success)',
    completeTestPaymentFailure: 'Complete test payment (Failure)',
    otpSectionTitle: 'మీ 6-అంకెల OTP తో మరమ్మతు ముగించండి',
    confirmOtpLabel: 'OTP నిర్ధారించి ముగించండి',
    jobClosedTitle: 'మీ OTP తో మరమ్మతు పూర్తయింది',
    jobClosedSubtitle:
        'మీ ఉపకరణ కాలక్రమం మరియు రసీదు హోమ్ మెమరీలో నవీకరించబడ్డాయి.',
  );

  static HouseholdStrings of(BuildContext context) {
    final code = KwStrings.of(context).languageCode;
    return switch (code) {
      'hi' => hi,
      'te' => te,
      _ => en,
    };
  }
}
