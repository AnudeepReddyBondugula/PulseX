import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'firebase_options.dart';
import 'providers/bookmark_provider.dart';
import 'providers/brief_provider.dart';
import 'screens/brief_screen.dart';
import 'services/auth_service.dart';
import 'services/messaging_service.dart';
import 'theme.dart';

/// Handles a notification that arrives while the app is closed.
///
/// Must be a top-level function: Android runs it in a separate
/// isolate with no access to the app's state.
@pragma('vm:entry-point')
Future<void> _onBackgroundMessage(RemoteMessage message) async {
  // Nothing to do. The system displays the notification itself,
  // and the brief is already in Firestore by the time it arrives.
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  FirebaseMessaging.onBackgroundMessage(_onBackgroundMessage);

  runApp(const PulseXApp());
}

class PulseXApp extends StatelessWidget {
  const PulseXApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => BriefProvider()),
        ChangeNotifierProvider(
          create: (_) => BookmarkProvider(),
        ),
      ],
      child: MaterialApp(
        title: 'PulseX',
        debugShowCheckedModeBanner: false,
        theme: PulseTheme.light,
        home: const _Bootstrap(),
      ),
    );
  }
}

/// Signs in, subscribes to notifications, and loads a brief.
///
/// All three happen once, before the reading screen appears, so
/// no screen has to handle a half-initialized app.
class _Bootstrap extends StatefulWidget {
  const _Bootstrap();

  @override
  State<_Bootstrap> createState() => _BootstrapState();
}

class _BootstrapState extends State<_Bootstrap> {
  final _auth = AuthService();
  final _messaging = MessagingService();

  @override
  void initState() {
    super.initState();
    _start();
  }

  Future<void> _start() async {
    final briefs = context.read<BriefProvider>();
    final bookmarks = context.read<BookmarkProvider>();

    // Firestore rules require an authenticated caller, so this
    // has to succeed before any read is attempted.
    await _auth.ensureSignedIn();

    await bookmarks.load();

    // A tap on the morning notification names a date; opening
    // the app directly just wants the latest brief.
    final launchMessage = await _messaging.initialMessage();
    final launchDate = MessagingService.briefDateFrom(
      launchMessage,
    );

    if (launchDate != null) {
      await briefs.loadDate(launchDate);
    } else {
      await briefs.loadLatest();
    }

    if (mounted) {
      bookmarks.remember(briefs.brief?.items ?? const []);
    }

    // Taps that arrive while the app is already open.
    _messaging.onMessageOpenedApp.listen((message) {
      final date = MessagingService.briefDateFrom(message);

      if (date != null) {
        briefs.loadDate(date);
      }
    });

    // Last, because a reader who declines the permission prompt
    // should still have a working app behind it.
    await _messaging.start();
  }

  @override
  Widget build(BuildContext context) {
    return const BriefScreen();
  }
}
