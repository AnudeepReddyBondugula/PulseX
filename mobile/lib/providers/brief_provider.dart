import 'package:flutter/foundation.dart';

import '../models/brief.dart';
import '../services/brief_repository.dart';

/// How loading a brief is going.
enum BriefStatus { loading, ready, empty, failed }

/// Holds the brief currently on screen.
class BriefProvider extends ChangeNotifier {
  BriefProvider({BriefRepository? repository})
      : _repository = repository ?? BriefRepository();

  final BriefRepository _repository;

  BriefStatus _status = BriefStatus.loading;
  Brief? _brief;
  String? _error;

  BriefStatus get status => _status;
  Brief? get brief => _brief;
  String? get error => _error;

  /// Loads the most recent brief.
  Future<void> loadLatest() async {
    await _load(_repository.fetchLatest);
  }

  /// Loads one specific day, by its date-based id.
  ///
  /// Used when a notification tap names a date. Falls back to the
  /// latest brief if that day is missing, so a stale notification
  /// still opens something useful.
  Future<void> loadDate(String date) async {
    await _load(() async {
      return await _repository.fetchByDate(date) ??
          await _repository.fetchLatest();
    });
  }

  Future<void> _load(Future<Brief?> Function() fetch) async {
    _status = BriefStatus.loading;
    _error = null;
    notifyListeners();

    try {
      final brief = await fetch();

      if (brief == null || brief.isEmpty) {
        _brief = brief;
        _status = BriefStatus.empty;
      } else {
        _brief = brief;
        _status = BriefStatus.ready;
      }
    } catch (error) {
      _error = error.toString();
      _status = BriefStatus.failed;
    }

    notifyListeners();
  }
}
