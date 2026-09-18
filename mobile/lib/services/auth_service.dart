import 'package:firebase_auth/firebase_auth.dart';

/// Signs the app in anonymously.
///
/// There is no login screen: Firestore rules require an
/// authenticated caller so the briefs are not world-readable,
/// and anonymous auth satisfies that without asking the reader
/// for anything. Upgrading to real accounts later does not
/// change any calling code.
class AuthService {
  AuthService({FirebaseAuth? auth})
      : _auth = auth ?? FirebaseAuth.instance;

  final FirebaseAuth _auth;

  /// Ensures a signed-in user exists, returning its uid.
  Future<String> ensureSignedIn() async {
    final existing = _auth.currentUser;

    if (existing != null) {
      return existing.uid;
    }

    final credential = await _auth.signInAnonymously();

    return credential.user?.uid ?? '';
  }
}
