import 'package:flutter/widgets.dart';

/// Portal-specific runtime-switchable strings for English (`en`), Hindi (`hi`),
/// and Telugu (`te`).
@immutable
class BrandStrings {
  const BrandStrings({
    required this.appTitle,
    required this.appSubtitle,
    required this.navRequests,
    required this.navSubmit,
    required this.navAnalytics,
    required this.signInTitle,
    required this.signInSubtitle,
    required this.signInButton,
    required this.signedInAsPrefix,
    required this.signOutLabel,
    required this.customEmailLabel,
    required this.quickPersonasHeading,
    required this.requestsHeading,
    required this.requestsSubtitle,
    required this.searchHint,
    required this.statusAll,
    required this.statusReceived,
    required this.statusInProgress,
    required this.statusClosed,
    required this.statusDeclined,
    required this.declineReasonLabel,
    required this.noRequestsTitle,
    required this.noRequestsBody,
    required this.intakeHeading,
    required this.tabBrandForward,
    required this.tabRetailerHandover,
    required this.submitBrandButton,
    required this.submitRetailerButton,
    required this.responseCardTitle,
    required this.analyticsHeading,
    required this.analyticsSubtitle,
    required this.installedBaseTitle,
    required this.warrantyActiveTitle,
    required this.firstTimeFixTitle,
    required this.selfFixTitle,
    required this.turnaroundTitle,
    required this.centreBreakdownTitle,
    required this.categoryBreakdownTitle,
    required this.accessibleTableToggle,
    required this.lookerStudioTitle,
    required this.lookerConfiguredNote,
    required this.lookerFallbackNote,
    required this.themeLight,
    required this.themeDark,
    required this.themeHighContrastLight,
    required this.themeHighContrastDark,
    required this.refreshLabel,
  });

  final String appTitle;
  final String appSubtitle;
  final String navRequests;
  final String navSubmit;
  final String navAnalytics;
  final String signInTitle;
  final String signInSubtitle;
  final String signInButton;
  final String signedInAsPrefix;
  final String signOutLabel;
  final String customEmailLabel;
  final String quickPersonasHeading;
  final String requestsHeading;
  final String requestsSubtitle;
  final String searchHint;
  final String statusAll;
  final String statusReceived;
  final String statusInProgress;
  final String statusClosed;
  final String statusDeclined;
  final String declineReasonLabel;
  final String noRequestsTitle;
  final String noRequestsBody;
  final String intakeHeading;
  final String tabBrandForward;
  final String tabRetailerHandover;
  final String submitBrandButton;
  final String submitRetailerButton;
  final String responseCardTitle;
  final String analyticsHeading;
  final String analyticsSubtitle;
  final String installedBaseTitle;
  final String warrantyActiveTitle;
  final String firstTimeFixTitle;
  final String selfFixTitle;
  final String turnaroundTitle;
  final String centreBreakdownTitle;
  final String categoryBreakdownTitle;
  final String accessibleTableToggle;
  final String lookerStudioTitle;
  final String lookerConfiguredNote;
  final String lookerFallbackNote;
  final String themeLight;
  final String themeDark;
  final String themeHighContrastLight;
  final String themeHighContrastDark;
  final String refreshLabel;

  static const BrandStrings en = BrandStrings(
    appTitle: 'Keepwell Brand & Retailer Portal',
    appSubtitle: 'Warranty forwards, installation handovers & FVR-14 quality',
    navRequests: 'Forwarded Requests',
    navSubmit: 'Forward / Handover',
    navAnalytics: 'Analytics & Looker',
    signInTitle: 'Sign in to Brand & Retailer Portal',
    signInSubtitle:
        'Select a demo brand or platform account to inspect forwarded requests, test authority checks, and view service quality analytics.',
    signInButton: 'Sign in',
    signedInAsPrefix: 'Signed in as',
    signOutLabel: 'Sign out',
    customEmailLabel: 'Demo account email',
    quickPersonasHeading: 'Demo Brand & Platform Accounts',
    requestsHeading: 'Forwarded Service Requests',
    requestsSubtitle:
        'Track every warranty forward and retailer installation handover sent to service centres, including authority decline reasons.',
    searchHint: 'Search by ticket, appliance, household, or decline reason…',
    statusAll: 'All',
    statusReceived: 'Received',
    statusInProgress: 'In Progress',
    statusClosed: 'Closed',
    statusDeclined: 'Declined',
    declineReasonLabel: 'Decline reason',
    noRequestsTitle: 'No matching forwarded requests',
    noRequestsBody:
        'Try clearing filters or submit a new brand warranty forward or retailer handover.',
    intakeHeading: 'Submit Brand Forward or Retailer Handover',
    tabBrandForward: 'Brand Warranty Forward',
    tabRetailerHandover: 'Retailer Installation Handover',
    submitBrandButton: 'Submit Brand Forward',
    submitRetailerButton: 'Submit Retailer Handover',
    responseCardTitle: 'Intake Response (HTTP 202)',
    analyticsHeading: 'Service Quality & Installed Base',
    analyticsSubtitle:
        'Live FVR-14 resolution, warranty coverage, centre breakdown, and Looker Studio reporting.',
    installedBaseTitle: 'Installed Base',
    warrantyActiveTitle: 'Active Warranty',
    firstTimeFixTitle: 'First-Time Fix',
    selfFixTitle: 'Self-Fix Resolved',
    turnaroundTitle: 'Avg Turnaround',
    centreBreakdownTitle: 'Service Quality by Centre',
    categoryBreakdownTitle: 'Breakdown by Appliance Category',
    accessibleTableToggle: 'Accessible data table',
    lookerStudioTitle: 'Looker Studio Executive Report',
    lookerConfiguredNote:
        'Connected to configured Looker Studio embed URL.',
    lookerFallbackNote:
        'LOOKER_STUDIO_URL is not configured. Showing interactive native analytics fallback.',
    themeLight: 'Light',
    themeDark: 'Dark',
    themeHighContrastLight: 'High-Contrast Light',
    themeHighContrastDark: 'High-Contrast Dark',
    refreshLabel: 'Refresh',
  );

  static const BrandStrings hi = BrandStrings(
    appTitle: 'कीपवेल ब्रांड एवं रिटेलर पोर्टल',
    appSubtitle: 'वारंटी फॉरवर्ड, इंस्टॉलेशन हैंडओवर और FVR-14 गुणवत्ता',
    navRequests: 'फॉरवर्ड किए गए अनुरोध',
    navSubmit: 'फॉरवर्ड / हैंडओवर',
    navAnalytics: 'एनालिटिक्स एवं लुकर',
    signInTitle: 'ब्रांड एवं रिटेलर पोर्टल में साइन इन करें',
    signInSubtitle:
        'फॉरवर्ड अनुरोध देखने, अधिकार जांचने और सेवा गुणवत्ता एनालिटिक्स के लिए डेमो खाता चुनें।',
    signInButton: 'साइन इन करें',
    signedInAsPrefix: 'साइन इन:',
    signOutLabel: 'साइन आउट',
    customEmailLabel: 'डेमो खाता ईमेल',
    quickPersonasHeading: 'डेमो ब्रांड एवं प्लेटफ़ॉर्म खाते',
    requestsHeading: 'फॉरवर्ड किए गए सेवा अनुरोध',
    requestsSubtitle:
        'सर्विस सेंटर को भेजे गए सभी वारंटी फॉरवर्ड और रिटेलर हैंडओवर ट्रैक करें, अस्वीकृति कारणों सहित।',
    searchHint: 'टिकट, उपकरण, ग्राहक या कारण से खोजें…',
    statusAll: 'सभी',
    statusReceived: 'प्राप्त',
    statusInProgress: 'प्रगति पर',
    statusClosed: 'पूर्ण',
    statusDeclined: 'अस्वीकृत',
    declineReasonLabel: 'अस्वीकृति कारण',
    noRequestsTitle: 'कोई मेल खाता अनुरोध नहीं',
    noRequestsBody:
        'फ़िल्टर हटाएँ या नया ब्रांड वारंटी फॉरवर्ड अथवा रिटेलर हैंडओवर सबमिट करें।',
    intakeHeading: 'ब्रांड फॉरवर्ड या रिटेलर हैंडओवर सबमिट करें',
    tabBrandForward: 'ब्रांड वारंटी फॉरवर्ड',
    tabRetailerHandover: 'रिटेलर इंस्टॉलेशन हैंडओवर',
    submitBrandButton: 'ब्रांड फॉरवर्ड भेजें',
    submitRetailerButton: 'रिटेलर हैंडओवर भेजें',
    responseCardTitle: 'इनटेक प्रतिक्रिया (HTTP 202)',
    analyticsHeading: 'सेवा गुणवत्ता और इंस्टॉल्ड बेस',
    analyticsSubtitle:
        'लाइव FVR-14 समाधान, वारंटी कवरेज, सेंटर विश्लेषण और लुकर स्टूडियो रिपोर्ट।',
    installedBaseTitle: 'इंस्टॉल्ड बेस',
    warrantyActiveTitle: 'सक्रिय वारंटी',
    firstTimeFixTitle: 'पहली बार सुधार',
    selfFixTitle: 'स्वयं-सुधार',
    turnaroundTitle: 'औसत समय',
    centreBreakdownTitle: 'सेंटर के अनुसार सेवा गुणवत्ता',
    categoryBreakdownTitle: 'उपकरण श्रेणी के अनुसार विवरण',
    accessibleTableToggle: 'सुगम डेटा तालिका',
    lookerStudioTitle: 'लुकर स्टूडियो रिपोर्ट',
    lookerConfiguredNote: 'कॉन्फ़िगर किए गए लुकर स्टूडियो URL से जुड़ा हुआ है।',
    lookerFallbackNote:
        'LOOKER_STUDIO_URL कॉन्फ़िगर नहीं है। नेटिव इंटरैक्टिव एनालिटिक्स दिखाया जा रहा है।',
    themeLight: 'लाइट',
    themeDark: 'डार्क',
    themeHighContrastLight: 'हाई-कंट्रास्ट लाइट',
    themeHighContrastDark: 'हाई-कंट्रास्ट डार्क',
    refreshLabel: 'रीफ़्रेश',
  );

  static const BrandStrings te = BrandStrings(
    appTitle: 'కీప్‌వెల్ బ్రాండ్ & రిటైలర్ పోర్టల్',
    appSubtitle: 'వారంటీ ఫార్వార్డ్‌లు, ఇన్‌స్టాలేషన్ హ్యాండోవర్‌లు & FVR-14',
    navRequests: 'ఫార్వార్డ్ అభ్యర్థనలు',
    navSubmit: 'ఫార్వార్డ్ / హ్యాండోవర్',
    navAnalytics: 'అనలిటిక్స్ & లుకర్',
    signInTitle: 'బ్రాండ్ & రిటైలర్ పోర్టల్‌లో సైన్ ఇన్ చేయండి',
    signInSubtitle:
        'ఫార్వార్డ్ అభ్యర్థనలను పరిశీలించడానికి, అధికార తనిఖీలను పరీక్షించడానికి డెమో ఖాతాను ఎంచుకోండి.',
    signInButton: 'సైన్ ఇన్',
    signedInAsPrefix: 'సైన్ ఇన్:',
    signOutLabel: 'సైన్ అవుట్',
    customEmailLabel: 'డెమో ఖాతా ఇమెయిల్',
    quickPersonasHeading: 'డెమో బ్రాండ్ & ప్లాట్‌ఫామ్ ఖాతాలు',
    requestsHeading: 'ఫార్వార్డ్ చేసిన సేవా అభ్యర్థనలు',
    requestsSubtitle:
        'సర్వీస్ సెంటర్లకు పంపిన ప్రతి వారంటీ ఫార్వార్డ్ మరియు రిటైలర్ హ్యాండోవర్‌ను ట్రాక్ చేయండి.',
    searchHint: 'టికెట్, ఉపకరణం, గృహం లేదా కారణం ద్వారా వెతకండి…',
    statusAll: 'అన్నీ',
    statusReceived: 'అందింది',
    statusInProgress: 'ప్రగతిలో ఉంది',
    statusClosed: 'పూర్తయింది',
    statusDeclined: 'తిరస్కరించబడింది',
    declineReasonLabel: 'తిరస్కరణ కారణం',
    noRequestsTitle: 'సరిపోయే అభ్యర్థనలు లేవు',
    noRequestsBody:
        'ఫిల్టర్‌లను తీసివేయండి లేదా కొత్త బ్రాండ్ ఫార్వార్డ్ లేదా రిటైలర్ హ్యాండోవర్ పంపండి.',
    intakeHeading: 'బ్రాండ్ ఫార్వార్డ్ లేదా రిటైలర్ హ్యాండోవర్ సమర్పించండి',
    tabBrandForward: 'బ్రాండ్ వారంటీ ఫార్వార్డ్',
    tabRetailerHandover: 'రిటైలర్ ఇన్‌స్టాలేషన్ హ్యాండోవర్',
    submitBrandButton: 'బ్రాండ్ ఫార్వార్డ్ పంపండి',
    submitRetailerButton: 'రిటైలర్ హ్యాండోవర్ పంపండి',
    responseCardTitle: 'ఇన్‌టేక్ ప్రతిస్పందన (HTTP 202)',
    analyticsHeading: 'సేవా నాణ్యత & ఇన్‌స్టాల్ చేసిన బేస్',
    analyticsSubtitle:
        'లైవ్ FVR-14 పరిష్కారం, వారంటీ కవరేజ్, సెంటర్ విశ్లేషణ మరియు లుకర్ స్టూడియో నివేదిక.',
    installedBaseTitle: 'ఇన్‌స్టాల్ చేసిన బేస్',
    warrantyActiveTitle: 'యాక్టివ్ వారంటీ',
    firstTimeFixTitle: 'మొదటిసారి పరిష్కారం',
    selfFixTitle: 'స్వీయ పరిష్కారం',
    turnaroundTitle: 'సగటు సమయం',
    centreBreakdownTitle: 'సెంటర్ వారీగా సేవా నాణ్యత',
    categoryBreakdownTitle: 'ఉపకరణ వర్గం వారీగా విశ్లేషణ',
    accessibleTableToggle: 'యాక్సెసిబుల్ డేటా పట్టిక',
    lookerStudioTitle: 'లుకర్ స్టూడియో నివేదిక',
    lookerConfiguredNote: 'కాన్ఫిగర్ చేసిన లుకర్ స్టూడియో URL కు కనెక్ట్ చేయబడింది.',
    lookerFallbackNote:
        'LOOKER_STUDIO_URL కాన్ఫిగర్ చేయబడలేదు. నేటివ్ ఇంటరాక్టివ్ అనలిటిక్స్ చూపబడుతోంది.',
    themeLight: 'లైట్',
    themeDark: 'డార్క్',
    themeHighContrastLight: 'హై-కాంట్రాస్ట్ లైట్',
    themeHighContrastDark: 'హై-కాంట్రాస్ట్ డార్క్',
    refreshLabel: 'రిఫ్రెష్',
  );

  static BrandStrings forLanguageCode(String code) {
    return switch (code.toLowerCase()) {
      'hi' => hi,
      'te' => te,
      _ => en,
    };
  }
}
