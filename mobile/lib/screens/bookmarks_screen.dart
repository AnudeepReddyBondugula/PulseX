import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/brief_item.dart';
import '../providers/bookmark_provider.dart';
import '../theme.dart';

/// Stories the reader saved.
///
/// Only ids are persisted, so a bookmark is listed here once the
/// brief it came from has been opened in this session. That
/// tradeoff keeps the store tiny and avoids duplicating content
/// that Firestore already holds.
class BookmarksScreen extends StatelessWidget {
  const BookmarksScreen({super.key});

  Future<void> _open(BriefItem item) async {
    final uri = Uri.tryParse(item.url);

    if (uri != null) {
      await launchUrl(
        uri,
        mode: LaunchMode.inAppBrowserView,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final bookmarks = context.watch<BookmarkProvider>();
    final items = bookmarks.items;

    return Scaffold(
      appBar: AppBar(title: const Text('Bookmarks')),
      body: items.isEmpty
          ? const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: Text(
                  'Nothing saved yet.\n'
                  'Tap the bookmark icon on a story to keep it.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: PulseTheme.muted),
                ),
              ),
            )
          : ListView.separated(
              itemCount: items.length,
              separatorBuilder: (_, _) =>
                  const Divider(height: 1),
              itemBuilder: (context, index) {
                final item = items[index];

                return ListTile(
                  title: Text(
                    item.title,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  subtitle: Text(
                    item.byline,
                    style: const TextStyle(
                      color: PulseTheme.muted,
                    ),
                  ),
                  trailing: IconButton(
                    tooltip: 'Remove bookmark',
                    icon: const Icon(Icons.bookmark),
                    color: PulseTheme.seed,
                    onPressed: () => bookmarks.toggle(item),
                  ),
                  onTap: () => _open(item),
                );
              },
            ),
    );
  }
}
