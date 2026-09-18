import 'package:shared_preferences/shared_preferences.dart';

/// Stores bookmarked story ids on the device.
///
/// Device-local by design: there are no accounts to sync
/// against. Switching to per-user storage later means replacing
/// this class, not its callers.
class BookmarkStore {
  static const _key = 'bookmarked_item_ids';

  /// Returns every bookmarked story id.
  Future<Set<String>> load() async {
    final prefs = await SharedPreferences.getInstance();

    return (prefs.getStringList(_key) ?? const []).toSet();
  }

  /// Persists the given set of story ids.
  Future<void> save(Set<String> ids) async {
    final prefs = await SharedPreferences.getInstance();

    await prefs.setStringList(_key, ids.toList(growable: false));
  }
}
