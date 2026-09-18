// PLACEHOLDER — replace by running, from the mobile/ directory:
//
//     dart pub global activate flutterfire_cli
//     flutterfire configure --project=<your-firebase-project-id>
//
// That command overwrites this file with your project's real
// values, and writes android/app/google-services.json.
//
// This placeholder exists so the project analyzes and so a
// forgotten setup step fails with an explanation rather than a
// cryptic Firebase initialization error.

import 'package:firebase_core/firebase_core.dart';

/// Firebase configuration for the current platform.
class DefaultFirebaseOptions {
  /// The options for the platform the app is running on.
  static FirebaseOptions get currentPlatform {
    throw UnsupportedError(
      'Firebase is not configured yet.\n\n'
      'Run this from the mobile/ directory:\n'
      '  dart pub global activate flutterfire_cli\n'
      '  flutterfire configure --project=<project-id>\n\n'
      'See backend/docs/mobile-setup.md for the full steps.',
    );
  }
}
