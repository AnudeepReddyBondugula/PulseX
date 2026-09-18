import 'package:cloud_firestore/cloud_firestore.dart';

import '../models/brief.dart';

/// Reads briefs published by the backend.
///
/// Items are embedded in each brief document, so opening a day
/// costs one read rather than a collection query.
class BriefRepository {
  BriefRepository({FirebaseFirestore? firestore})
      : _firestore = firestore ?? FirebaseFirestore.instance;

  static const collection = 'briefs';

  final FirebaseFirestore _firestore;

  /// Returns the most recent brief, or null if none exist.
  ///
  /// Deliberately "latest" rather than "today": a scheduled run
  /// can be delayed or skipped, and showing yesterday's brief
  /// beats showing an empty screen.
  Future<Brief?> fetchLatest() async {
    final snapshot = await _firestore
        .collection(collection)
        .orderBy(FieldPath.documentId, descending: true)
        .limit(1)
        .get();

    if (snapshot.docs.isEmpty) {
      return null;
    }

    final doc = snapshot.docs.first;

    return Brief.fromMap(doc.id, doc.data());
  }

  /// Returns one brief by its date-based document id.
  Future<Brief?> fetchByDate(String date) async {
    final doc =
        await _firestore.collection(collection).doc(date).get();

    final data = doc.data();

    if (!doc.exists || data == null) {
      return null;
    }

    return Brief.fromMap(doc.id, data);
  }

  /// Returns recent briefs, newest first, for the archive.
  Future<List<Brief>> fetchRecent({int limit = 30}) async {
    final snapshot = await _firestore
        .collection(collection)
        .orderBy(FieldPath.documentId, descending: true)
        .limit(limit)
        .get();

    return snapshot.docs
        .map((doc) => Brief.fromMap(doc.id, doc.data()))
        .toList(growable: false);
  }
}
