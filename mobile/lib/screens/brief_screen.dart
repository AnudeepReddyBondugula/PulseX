import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/brief.dart';
import '../models/brief_item.dart';
import '../providers/bookmark_provider.dart';
import '../providers/brief_provider.dart';
import '../theme.dart';
import '../widgets/story_card.dart';
import 'archive_screen.dart';
import 'bookmarks_screen.dart';

/// The reading surface: one story per screen, swiped vertically.
class BriefScreen extends StatefulWidget {
  const BriefScreen({super.key});

  @override
  State<BriefScreen> createState() => _BriefScreenState();
}

class _BriefScreenState extends State<BriefScreen> {
  final _controller = PageController();
  int _index = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _openOriginal(BriefItem item) async {
    final uri = Uri.tryParse(item.url);

    if (uri == null) {
      return;
    }

    // An in-app browser keeps the reader inside the app, so
    // returning to the brief is one back press.
    final launched = await launchUrl(
      uri,
      mode: LaunchMode.inAppBrowserView,
    );

    if (!launched && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not open that link.'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<BriefProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Text(_titleFor(provider)),
        actions: [
          IconButton(
            tooltip: 'Bookmarks',
            icon: const Icon(Icons.bookmark_border),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const BookmarksScreen(),
              ),
            ),
          ),
          IconButton(
            tooltip: 'Past briefs',
            icon: const Icon(Icons.calendar_month_outlined),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const ArchiveScreen(),
              ),
            ),
          ),
        ],
        bottom: _Progress(
          index: _index,
          total: provider.brief?.items.length ?? 0,
        ),
      ),
      body: _body(provider),
    );
  }

  String _titleFor(BriefProvider provider) {
    final brief = provider.brief;

    if (brief == null) {
      return 'PulseX';
    }

    return _formatDate(brief.date);
  }

  Widget _body(BriefProvider provider) {
    switch (provider.status) {
      case BriefStatus.loading:
        return const Center(
          child: CircularProgressIndicator(),
        );

      case BriefStatus.failed:
        return _Message(
          icon: Icons.cloud_off_outlined,
          title: 'Could not load your brief',
          detail: provider.error ?? 'Something went wrong.',
          onRetry: provider.loadLatest,
        );

      case BriefStatus.empty:
        return _Message(
          icon: Icons.inbox_outlined,
          title: 'No brief yet',
          detail: 'The next one arrives tomorrow morning.',
          onRetry: provider.loadLatest,
        );

      case BriefStatus.ready:
        return _pages(provider.brief!);
    }
  }

  Widget _pages(Brief brief) {
    final bookmarks = context.watch<BookmarkProvider>();

    return PageView.builder(
      controller: _controller,
      scrollDirection: Axis.vertical,
      itemCount: brief.items.length + 1,
      onPageChanged: (index) => setState(() => _index = index),
      itemBuilder: (context, index) {
        if (index == 0) {
          return _Introduction(brief: brief);
        }

        final item = brief.items[index - 1];

        return StoryCard(
          item: item,
          isBookmarked: bookmarks.isBookmarked(item.id),
          onToggleBookmark: () => bookmarks.toggle(item),
          onOpenOriginal: () => _openOriginal(item),
        );
      },
    );
  }
}

/// The first page: the brief's own introduction and summary.
class _Introduction extends StatelessWidget {
  const _Introduction({required this.brief});

  final Brief brief;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: PulseTheme.card,
      padding: const EdgeInsets.all(24),
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              _formatDate(brief.date).toUpperCase(),
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.2,
                color: PulseTheme.seed,
              ),
            ),
            const SizedBox(height: 14),
            Text(
              brief.introduction.isEmpty
                  ? 'Your daily brief'
                  : brief.introduction,
              style: const TextStyle(
                fontSize: 26,
                height: 1.3,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 18),
            Text(
              brief.summary,
              style: const TextStyle(
                fontSize: 16.5,
                height: 1.55,
                color: Color(0xFF3A3F47),
              ),
            ),
            const SizedBox(height: 26),
            Text(
              '${brief.articleCount} stories · '
              '${brief.paperCount} papers',
              style: const TextStyle(
                fontSize: 13,
                color: PulseTheme.muted,
              ),
            ),
            const SizedBox(height: 32),
            Row(
              children: const [
                Icon(
                  Icons.keyboard_arrow_up,
                  color: PulseTheme.muted,
                ),
                SizedBox(width: 6),
                Text(
                  'Swipe up to start reading',
                  style: TextStyle(
                    fontSize: 13.5,
                    color: PulseTheme.muted,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Progress extends StatelessWidget implements PreferredSizeWidget {
  const _Progress({required this.index, required this.total});

  final int index;
  final int total;

  @override
  Size get preferredSize => const Size.fromHeight(2);

  @override
  Widget build(BuildContext context) {
    if (total == 0) {
      return const SizedBox(height: 2);
    }

    return SizedBox(
      height: 2,
      child: LinearProgressIndicator(
        value: index / total,
        backgroundColor: PulseTheme.hairline,
        color: PulseTheme.seed,
      ),
    );
  }
}

class _Message extends StatelessWidget {
  const _Message({
    required this.icon,
    required this.title,
    required this.detail,
    required this.onRetry,
  });

  final IconData icon;
  final String title;
  final String detail;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 52, color: PulseTheme.muted),
            const SizedBox(height: 16),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              detail,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 14,
                color: PulseTheme.muted,
              ),
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: onRetry,
              child: const Text('Try again'),
            ),
          ],
        ),
      ),
    );
  }
}

String _formatDate(DateTime date) {
  const months = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  return '${months[date.month - 1]} ${date.day}, ${date.year}';
}
