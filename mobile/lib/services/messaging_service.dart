import 'package:firebase_messaging/firebase_messaging.dart';

/// Subscribes to the morning notification.
///
/// The backend publishes to a topic rather than to device
/// tokens, so there is no registration to report back and
/// nothing to keep in sync: subscribing is the whole setup.
class MessagingService {
  MessagingService({FirebaseMessaging? messaging})
      : _messaging = messaging ?? FirebaseMessaging.instance;

  static const topic = 'daily_brief';

  final FirebaseMessaging _messaging;

  /// Requests permission and subscribes to the daily topic.
  ///
  /// Android 13 and later require the notification permission at
  /// runtime. A reader who declines still gets a working app,
  /// just no morning prompt, so a refusal is not an error.
  Future<void> start() async {
    await _messaging.requestPermission();

    await _messaging.subscribeToTopic(topic);
  }

  /// The date of the brief a notification tap refers to, if any.
  ///
  /// Reads the data payload the backend attaches. Returns null
  /// when the app was opened normally rather than from a tap.
  static String? briefDateFrom(RemoteMessage? message) {
    final value = message?.data['briefDate'];

    return value is String && value.isNotEmpty ? value : null;
  }

  /// The message that launched the app from a terminated state.
  Future<RemoteMessage?> initialMessage() {
    return _messaging.getInitialMessage();
  }

  /// Taps that arrive while the app is already running.
  Stream<RemoteMessage> get onMessageOpenedApp {
    return FirebaseMessaging.onMessageOpenedApp;
  }
}
