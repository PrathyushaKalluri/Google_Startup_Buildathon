/// In-memory fallback for non-web (VM / unit test) environments.
class KwLiveStorage {
  static final Map<String, String> _mem = <String, String>{};

  static String? getItem(String key) => _mem[key];

  static void setItem(String key, String value) {
    _mem[key] = value;
  }
}
