/// One story in a brief: a news article or a research paper.
class BriefItem {
  const BriefItem({
    required this.id,
    required this.kind,
    required this.title,
    required this.url,
    required this.source,
    required this.publishedAt,
    required this.topics,
    required this.authors,
    required this.importanceScore,
    this.summary,
    this.whyItMatters,
    this.imageUrl,
  });

  /// Builds an item from a Firestore map.
  ///
  /// Every field is read defensively. A brief that loses one
  /// optional value should still render, so missing keys become
  /// empty rather than throwing.
  factory BriefItem.fromMap(Map<String, dynamic> map) {
    return BriefItem(
      id: _string(map['id']) ?? '',
      kind: _string(map['kind']) == 'paper'
          ? BriefItemKind.paper
          : BriefItemKind.news,
      title: _string(map['title']) ?? 'Untitled',
      url: _string(map['url']) ?? '',
      source: _string(map['source']) ?? 'Unknown source',
      publishedAt: _dateTime(map['publishedAt']),
      topics: _stringList(map['topics']),
      authors: _stringList(map['authors']),
      importanceScore: _double(map['importanceScore']),
      summary: _string(map['summary']),
      whyItMatters: _string(map['whyItMatters']),
      imageUrl: _string(map['imageUrl']),
    );
  }

  final String id;
  final BriefItemKind kind;
  final String title;
  final String url;
  final String source;
  final DateTime? publishedAt;
  final List<String> topics;
  final List<String> authors;
  final double importanceScore;
  final String? summary;
  final String? whyItMatters;
  final String? imageUrl;

  bool get isPaper => kind == BriefItemKind.paper;

  bool get hasImage => imageUrl != null && imageUrl!.isNotEmpty;

  /// The byline shown under the headline.
  ///
  /// Papers read better credited to their authors than to
  /// "arXiv", so they borrow the author list when there is one.
  String get byline {
    if (isPaper && authors.isNotEmpty) {
      return authors.take(2).join(', ');
    }

    return source;
  }

  /// The body text, falling back to a note when unsummarized.
  ///
  /// Summarization can fail for one item without failing the
  /// brief, so this case is real rather than theoretical.
  String get body {
    final text = summary;

    if (text != null && text.isNotEmpty) {
      return text;
    }

    return 'No summary was generated for this story. '
        'Open the original to read it.';
  }
}

/// Whether a story came from a news feed or from arXiv.
enum BriefItemKind { news, paper }

String? _string(Object? value) {
  if (value is String && value.trim().isNotEmpty) {
    return value.trim();
  }

  return null;
}

List<String> _stringList(Object? value) {
  if (value is List) {
    return value
        .map(_string)
        .whereType<String>()
        .toList(growable: false);
  }

  return const [];
}

double _double(Object? value) {
  if (value is num) {
    return value.toDouble();
  }

  return 0;
}

DateTime? _dateTime(Object? value) {
  if (value is String) {
    return DateTime.tryParse(value);
  }

  return null;
}
