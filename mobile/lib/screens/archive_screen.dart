import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/brief.dart';
import '../providers/brief_provider.dart';
import '../services/brief_repository.dart';
import '../theme.dart';

/// Past briefs, newest first.
///
/// Every brief the backend has ever published stays in Firestore,
/// so the archive is a read rather than anything to maintain.
class ArchiveScreen extends StatefulWidget {
  const ArchiveScreen({super.key});

  @override
  State<ArchiveScreen> createState() => _ArchiveScreenState();
}

class _ArchiveScreenState extends State<ArchiveScreen> {
  final _repository = BriefRepository();

  late Future<List<Brief>> _briefs;

  @override
  void initState() {
    super.initState();
    _briefs = _repository.fetchRecent();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Past briefs')),
      body: FutureBuilder<List<Brief>>(
        future: _briefs,
        builder: (context, snapshot) {
          if (snapshot.connectionState ==
              ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (snapshot.hasError) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: Text(
                  'Could not load past briefs.',
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }

          final briefs = snapshot.data ?? const [];

          if (briefs.isEmpty) {
            return const Center(
              child: Text('No briefs yet.'),
            );
          }

          return ListView.separated(
            itemCount: briefs.length,
            separatorBuilder: (_, _) =>
                const Divider(height: 1),
            itemBuilder: (context, index) {
              final brief = briefs[index];

              return ListTile(
                title: Text(
                  _formatDate(brief.date),
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                subtitle: Text(
                  '${brief.articleCount} stories · '
                  '${brief.paperCount} papers',
                  style: const TextStyle(
                    color: PulseTheme.muted,
                  ),
                ),
                trailing: const Icon(
                  Icons.chevron_right,
                  color: PulseTheme.muted,
                ),
                onTap: () {
                  // Loading into the shared provider means the
                  // reading screen is reused as-is.
                  context.read<BriefProvider>().loadDate(
                        _documentId(brief.date),
                      );

                  Navigator.of(context).pop();
                },
              );
            },
          );
        },
      ),
    );
  }
}

String _documentId(DateTime date) {
  final month = date.month.toString().padLeft(2, '0');
  final day = date.day.toString().padLeft(2, '0');

  return '${date.year}-$month-$day';
}

String _formatDate(DateTime date) {
  const months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];

  return '${date.day} ${months[date.month - 1]} ${date.year}';
}
