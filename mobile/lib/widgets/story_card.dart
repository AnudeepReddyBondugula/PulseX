import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../models/brief_item.dart';
import '../theme.dart';

/// One full-screen story, in the style of a news card.
///
/// The layout is fixed rather than scrolling: a hero image, the
/// headline, the summary, and why it matters. Summaries are
/// written to two or three sentences precisely so a story fits a
/// screen without the reader scrolling.
class StoryCard extends StatelessWidget {
  const StoryCard({
    super.key,
    required this.item,
    required this.isBookmarked,
    required this.onToggleBookmark,
    required this.onOpenOriginal,
  });

  final BriefItem item;
  final bool isBookmarked;
  final VoidCallback onToggleBookmark;
  final VoidCallback onOpenOriginal;

  @override
  Widget build(BuildContext context) {
    final accent = PulseTheme.accentFor(isPaper: item.isPaper);

    return Container(
      color: PulseTheme.card,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _Hero(item: item, accent: accent),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(
                  20,
                  20,
                  20,
                  8,
                ),
                child: Column(
                  crossAxisAlignment:
                      CrossAxisAlignment.start,
                  children: [
                    _Topics(item: item, accent: accent),
                    const SizedBox(height: 12),
                    Text(
                      item.title,
                      style: const TextStyle(
                        fontSize: 23,
                        height: 1.25,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 14),
                    Expanded(
                      child: SingleChildScrollView(
                        child: Column(
                          crossAxisAlignment:
                              CrossAxisAlignment.start,
                          children: [
                            Text(
                              item.body,
                              style: const TextStyle(
                                fontSize: 16.5,
                                height: 1.5,
                                color: Color(0xFF2B2F36),
                              ),
                            ),
                            if (item.whyItMatters != null) ...[
                              const SizedBox(height: 16),
                              _WhyItMatters(
                                text: item.whyItMatters!,
                                accent: accent,
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            _Footer(
              item: item,
              isBookmarked: isBookmarked,
              onToggleBookmark: onToggleBookmark,
              onOpenOriginal: onOpenOriginal,
            ),
          ],
        ),
      ),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({required this.item, required this.accent});

  final BriefItem item;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    const height = 220.0;

    if (!item.hasImage) {
      return _HeroFallback(
        item: item,
        accent: accent,
        height: height,
      );
    }

    return CachedNetworkImage(
      imageUrl: item.imageUrl!,
      height: height,
      width: double.infinity,
      fit: BoxFit.cover,
      placeholder: (context, url) => Container(
        height: height,
        color: PulseTheme.hairline,
      ),
      // Many feeds carry no usable image, and some carry links
      // that 404. Either way the card still has to render.
      errorWidget: (context, url, error) => _HeroFallback(
        item: item,
        accent: accent,
        height: height,
      ),
    );
  }
}

class _HeroFallback extends StatelessWidget {
  const _HeroFallback({
    required this.item,
    required this.accent,
    required this.height,
  });

  final BriefItem item;
  final Color accent;
  final double height;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            accent.withValues(alpha: 0.85),
            accent.withValues(alpha: 0.45),
          ],
        ),
      ),
      child: Center(
        child: Icon(
          item.isPaper
              ? Icons.science_outlined
              : Icons.newspaper_outlined,
          size: 56,
          color: Colors.white.withValues(alpha: 0.9),
        ),
      ),
    );
  }
}

class _Topics extends StatelessWidget {
  const _Topics({required this.item, required this.accent});

  final BriefItem item;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final labels = [
      if (item.isPaper) 'Research',
      ...item.topics.take(2),
    ];

    if (labels.isEmpty) {
      return const SizedBox.shrink();
    }

    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: [
        for (final label in labels)
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 9,
              vertical: 4,
            ),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              label.toUpperCase(),
              style: TextStyle(
                fontSize: 10.5,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.6,
                color: accent,
              ),
            ),
          ),
      ],
    );
  }
}

class _WhyItMatters extends StatelessWidget {
  const _WhyItMatters({
    required this.text,
    required this.accent,
  });

  final String text;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: BoxDecoration(
        border: Border(
          left: BorderSide(color: accent, width: 3),
        ),
        color: accent.withValues(alpha: 0.05),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'WHY IT MATTERS',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.8,
              color: accent,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            text,
            style: const TextStyle(
              fontSize: 14.5,
              height: 1.45,
              color: Color(0xFF374151),
            ),
          ),
        ],
      ),
    );
  }
}

class _Footer extends StatelessWidget {
  const _Footer({
    required this.item,
    required this.isBookmarked,
    required this.onToggleBookmark,
    required this.onOpenOriginal,
  });

  final BriefItem item;
  final bool isBookmarked;
  final VoidCallback onToggleBookmark;
  final VoidCallback onOpenOriginal;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 8, 8, 8),
      decoration: const BoxDecoration(
        border: Border(
          top: BorderSide(color: PulseTheme.hairline),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: GestureDetector(
              onTap: onOpenOriginal,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    item.byline,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: PulseTheme.ink,
                    ),
                  ),
                  const SizedBox(height: 2),
                  const Text(
                    'Tap to read the original',
                    style: TextStyle(
                      fontSize: 11.5,
                      color: PulseTheme.muted,
                    ),
                  ),
                ],
              ),
            ),
          ),
          IconButton(
            onPressed: onToggleBookmark,
            tooltip: isBookmarked
                ? 'Remove bookmark'
                : 'Bookmark',
            icon: Icon(
              isBookmarked
                  ? Icons.bookmark
                  : Icons.bookmark_border,
              color: isBookmarked
                  ? PulseTheme.seed
                  : PulseTheme.muted,
            ),
          ),
          IconButton(
            onPressed: onOpenOriginal,
            tooltip: 'Open the original',
            icon: const Icon(
              Icons.open_in_new,
              color: PulseTheme.muted,
            ),
          ),
        ],
      ),
    );
  }
}
