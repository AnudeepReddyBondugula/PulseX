import 'brief_item.dart';

/// One day's curated brief.
class Brief {
  const Brief({
    required this.id,
    required this.date,
    required this.title,
    required this.introduction,
    required this.summary,
    required this.items,
  });

  /// Builds a brief from a Firestore document map.
  factory Brief.fromMap(String documentId, Map<String, dynamic> map) {
    final rawItems = map['items'];

    final items = rawItems is List
        ? rawItems
            .whereType<Map>()
            .map((item) => BriefItem.fromMap(
                  Map<String, dynamic>.from(item),
                ))
            .toList()
        : <BriefItem>[];

    return Brief(
      id: map['id'] as String? ?? documentId,
      date: DateTime.tryParse(
            map['date'] as String? ?? documentId,
          ) ??
          DateTime.now(),
      title: map['title'] as String? ?? 'PulseX Daily Brief',
      introduction: map['introduction'] as String? ?? '',
      summary: map['summary'] as String? ?? '',
      items: items,
    );
  }

  final String id;
  final DateTime date;
  final String title;
  final String introduction;
  final String summary;
  final List<BriefItem> items;

  bool get isEmpty => items.isEmpty;

  int get articleCount =>
      items.where((item) => !item.isPaper).length;

  int get paperCount => items.where((item) => item.isPaper).length;
}
