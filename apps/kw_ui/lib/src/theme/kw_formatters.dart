/// Indian locale (`en-IN`) currency and IST (`+05:30`) date/time formatters.
///
/// Money is always stored as integer paise per Shared Contract §1.
String formatInrPaise(
  int paise, {
  bool showZeroDecimals = false,
}) {
  final isNegative = paise < 0;
  final absPaise = paise.abs();
  final rupees = absPaise ~/ 100;
  final remPaise = absPaise % 100;

  final groupedRupees = _formatIndianGrouping(rupees);
  final sign = isNegative ? '-' : '';

  if (remPaise == 0 && !showZeroDecimals) {
    return '$sign₹$groupedRupees';
  }
  final paiseStr = remPaise.toString().padLeft(2, '0');
  return '$sign₹$groupedRupees.$paiseStr';
}

/// Formats a paise price range using Indian lakh grouping, e.g. `₹450 – ₹850`.
String formatInrRange(
  int lowPaise,
  int highPaise, {
  bool showZeroDecimals = false,
}) {
  final low = formatInrPaise(lowPaise, showZeroDecimals: showZeroDecimals);
  final high = formatInrPaise(highPaise, showZeroDecimals: showZeroDecimals);
  if (low == high) return low;
  return '$low – $high';
}

String _formatIndianGrouping(int value) {
  final digits = value.toString();
  if (digits.length <= 3) return digits;

  final lastThree = digits.substring(digits.length - 3);
  var remaining = digits.substring(0, digits.length - 3);
  final groups = <String>[];

  while (remaining.length > 2) {
    groups.insert(0, remaining.substring(remaining.length - 2));
    remaining = remaining.substring(0, remaining.length - 2);
  }
  if (remaining.isNotEmpty) {
    groups.insert(0, remaining);
  }
  groups.add(lastThree);
  return groups.join(',');
}

const _istOffset = Duration(hours: 5, minutes: 30);

const _months = <String>[
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

/// Converts [dt] to India Standard Time (`+05:30`) and formats cleanly.
///
/// Examples:
/// - `21 Nov, 03:45 PM IST`
/// - `03:45 PM IST` (when `includeDate: false`)
/// - `21 Nov 2026` (when `includeTime: false`)
String formatIstDateTime(
  DateTime dt, {
  bool includeDate = true,
  bool includeTime = true,
  bool includeYear = false,
  bool includeTzLabel = true,
}) {
  final ist = dt.toUtc().add(_istOffset);
  final parts = <String>[];

  if (includeDate) {
    final day = ist.day.toString().padLeft(2, '0');
    final month = _months[ist.month - 1];
    parts.add(includeYear ? '$day $month ${ist.year}' : '$day $month');
  }

  if (includeTime) {
    final hour24 = ist.hour;
    final period = hour24 >= 12 ? 'PM' : 'AM';
    final hour12 = hour24 % 12 == 0 ? 12 : hour24 % 12;
    final minute = ist.minute.toString().padLeft(2, '0');
    final timeStr = '${hour12.toString().padLeft(2, '0')}:$minute $period';
    parts.add(includeTzLabel ? '$timeStr IST' : timeStr);
  }

  return parts.join(', ');
}

/// Formats a time window in IST, e.g. `10:00 AM – 12:00 PM IST`.
String formatIstSlotWindow(DateTime start, DateTime end) {
  final startIst = start.toUtc().add(_istOffset);
  final endIst = end.toUtc().add(_istOffset);

  final sameDay = startIst.year == endIst.year &&
      startIst.month == endIst.month &&
      startIst.day == endIst.day;

  final startText = formatIstDateTime(
    start,
    includeDate: true,
    includeTime: true,
    includeTzLabel: false,
  );
  final endText = formatIstDateTime(
    end,
    includeDate: !sameDay,
    includeTime: true,
    includeTzLabel: true,
  );
  return '$startText – $endText';
}
