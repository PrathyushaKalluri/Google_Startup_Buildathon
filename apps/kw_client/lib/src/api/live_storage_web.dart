import 'dart:js_interop';

@JS('window.localStorage.getItem')
external JSString? _jsGetItem(JSString key);

@JS('window.localStorage.setItem')
external void _jsSetItem(JSString key, JSString value);

/// Web localStorage persistence using built-in dart:js_interop (Wasm & JS compatible).
class KwLiveStorage {
  static String? getItem(String key) {
    try {
      return _jsGetItem(key.toJS)?.toDart;
    } catch (_) {
      return null;
    }
  }

  static void setItem(String key, String value) {
    try {
      _jsSetItem(key.toJS, value.toJS);
    } catch (_) {}
  }
}
