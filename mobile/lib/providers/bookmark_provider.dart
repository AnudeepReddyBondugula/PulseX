import 'package:flutter/foundation.dart';

import '../models/brief_item.dart';
import '../services/bookmark_store.dart';

/// Tracks which stories the reader has saved.
///
/// Saved items are held in memory alongside the ids so the
/// bookmarks screen can render without re-reading Firestore.
class BookmarkProvider extends ChangeNotifier {
  BookmarkProvider({BookmarkStore? store})
      : _store = store ?? BookmarkStore();

  final BookmarkStore _store;

  final Map<String, BriefItem> _items = {};
  Set<String> _ids = {};

  Set<String> get ids => Set.unmodifiable(_ids);

  List<BriefItem> get items =>
      _items.values.toList(growable: false);

  bool isBookmarked(String id) => _ids.contains(id);

  /// Reads saved ids from the device.
  Future<void> load() async {
    _ids = await _store.load();
    notifyListeners();
  }

  /// Registers items from a loaded brief.
  ///
  /// Only the ids are persisted, so the full story has to be
  /// recovered from whichever brief it appeared in.
  void remember(Iterable<BriefItem> items) {
    for (final item in items) {
      if (_ids.contains(item.id)) {
        _items[item.id] = item;
      }
    }
  }

  /// Saves or unsaves one story.
  Future<void> toggle(BriefItem item) async {
    if (_ids.contains(item.id)) {
      _ids.remove(item.id);
      _items.remove(item.id);
    } else {
      _ids.add(item.id);
      _items[item.id] = item;
    }

    notifyListeners();

    await _store.save(_ids);
  }
}
