import 'package:flutter_test/flutter_test.dart';
import 'package:pulsex/models/brief.dart';
import 'package:pulsex/models/brief_item.dart';

/// A Firestore document as the backend publishes it.
Map<String, dynamic> firestoreBrief({
  List<Map<String, dynamic>>? items,
}) {
  return {
    'id': 'pulsex-2026-09-18',
    'date': '2026-09-18',
    'title': 'PulseX Daily Brief',
    'introduction': 'Good morning.',
    'summary': 'Agents were the theme.',
    'generatedAt': '2026-09-18T03:00:00+00:00',
    'articleCount': 1,
    'paperCount': 1,
    'items': items ?? [newsItem(), paperItem()],
  };
}

Map<String, dynamic> newsItem() {
  return {
    'id': 'a1',
    'kind': 'news',
    'title': 'A model shipped',
    'url': 'https://openai.com/a1',
    'source': 'OpenAI',
    'publishedAt': '2026-09-17T10:00:00+00:00',
    'summary': 'It shipped.',
    'whyItMatters': 'It is faster.',
    'topics': ['LLM'],
    'authors': ['Alice Smith'],
    'importanceScore': 0.7,
    'imageUrl': 'https://openai.com/hero.jpg',
  };
}

Map<String, dynamic> paperItem() {
  return {
    'id': 'p1',
    'kind': 'paper',
    'title': 'On scaling',
    'url': 'https://arxiv.org/abs/2609.00001',
    'source': 'arXiv',
    'publishedAt': '2026-09-17T08:00:00+00:00',
    'summary': 'They scaled things.',
    'whyItMatters': null,
    'topics': ['AI Research'],
    'authors': ['Bob Jones', 'Carol White'],
    'importanceScore': 0.9,
    'imageUrl': null,
  };
}

void main() {
  group('Brief.fromMap', () {
    test('reads the fields the backend publishes', () {
      final brief = Brief.fromMap(
        '2026-09-18',
        firestoreBrief(),
      );

      expect(brief.id, 'pulsex-2026-09-18');
      expect(brief.title, 'PulseX Daily Brief');
      expect(brief.introduction, 'Good morning.');
      expect(brief.date.year, 2026);
      expect(brief.date.month, 9);
      expect(brief.date.day, 18);
    });

    test('counts articles and papers separately', () {
      final brief = Brief.fromMap(
        '2026-09-18',
        firestoreBrief(),
      );

      expect(brief.items.length, 2);
      expect(brief.articleCount, 1);
      expect(brief.paperCount, 1);
    });

    test('a brief with no items reports empty', () {
      final brief = Brief.fromMap(
        '2026-09-18',
        firestoreBrief(items: []),
      );

      expect(brief.isEmpty, isTrue);
    });

    test('missing fields fall back rather than throwing', () {
      // A partial document should still render something.
      final brief = Brief.fromMap('2026-09-18', {});

      expect(brief.id, '2026-09-18');
      expect(brief.title, isNotEmpty);
      expect(brief.items, isEmpty);
    });
  });

  group('BriefItem.fromMap', () {
    test('reads a news item', () {
      final item = BriefItem.fromMap(newsItem());

      expect(item.kind, BriefItemKind.news);
      expect(item.isPaper, isFalse);
      expect(item.source, 'OpenAI');
      expect(item.hasImage, isTrue);
      expect(item.whyItMatters, 'It is faster.');
    });

    test('reads a paper', () {
      final item = BriefItem.fromMap(paperItem());

      expect(item.kind, BriefItemKind.paper);
      expect(item.isPaper, isTrue);
      expect(item.hasImage, isFalse);
      expect(item.whyItMatters, isNull);
    });

    test('a paper is credited to its authors', () {
      // "arXiv" is accurate but tells the reader less than
      // the names do.
      expect(BriefItem.fromMap(paperItem()).byline,
          'Bob Jones, Carol White');
    });

    test('an article is credited to its source', () {
      expect(BriefItem.fromMap(newsItem()).byline, 'OpenAI');
    });

    test('an unsummarized item still has body text', () {
      // Summarization can fail for one item without failing
      // the brief, so this case is real.
      final map = newsItem()..['summary'] = null;

      expect(BriefItem.fromMap(map).body, isNotEmpty);
    });

    test('blank strings are treated as absent', () {
      final map = newsItem()..['imageUrl'] = '   ';

      expect(BriefItem.fromMap(map).hasImage, isFalse);
    });

    test('a malformed topics value does not throw', () {
      final map = newsItem()..['topics'] = 'not a list';

      expect(BriefItem.fromMap(map).topics, isEmpty);
    });

    test('an unparsable date becomes null', () {
      final map = newsItem()..['publishedAt'] = 'not a date';

      expect(BriefItem.fromMap(map).publishedAt, isNull);
    });
  });
}
