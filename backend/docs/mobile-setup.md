# Mobile setup

Everything needed to get the app onto a phone. The steps only you can do
come first, because nothing else works without them.

## What the app is

A Flutter Android app that reads each day's brief from Firestore and shows
one story per screen, swiped vertically. A push notification arrives each
morning; tapping it opens that day's brief at the first card.

It reads data the backend publishes. It never talks to OpenRouter, Resend
or the feeds directly.

```
backend (GitHub Actions)          app (phone)
  collect, rank, summarize
  write briefs/{date}   ──────→   read briefs/{date}
  send to FCM topic     ──────→   notification → open that day
  send email
```

## Step 1 — Create the Firebase project

Only you can do this; it needs console access.

1. Go to [console.firebase.google.com](https://console.firebase.google.com)
   and create a project. Note the **project id**.
2. **Build → Firestore Database → Create database.** Start in production
   mode and pick a region near you. Rules come in step 4.
3. **Build → Authentication → Get started → Anonymous → Enable.** The app
   signs in anonymously so Firestore rules can require a caller without
   showing a login screen.
4. Cloud Messaging needs no setup beyond the project existing.

## Step 2 — Connect the app

From the `mobile/` directory:

```bash
dart pub global activate flutterfire_cli
flutterfire configure --project=<your-project-id>
```

This writes two files, neither of which is committed:

- `lib/firebase_options.dart` — replaces the placeholder that currently
  throws an explanatory error
- `android/app/google-services.json` — read by the Gradle plugin

Select **Android** when prompted. The application id is `com.pulsex.app`.

## Step 3 — Give the backend write access

1. **Project Settings → Service accounts → Generate new private key.** A
   JSON file downloads.
2. Add its **entire contents** as a GitHub repository secret named
   `FIREBASE_SERVICE_ACCOUNT_JSON`, at Settings → Secrets and variables →
   Actions.

The value is the JSON itself, not a path: the workflow runs on a runner
with no persistent disk. Leaving this unset disables Firestore publishing
and the notification, and the backend falls back to email only.

## Step 4 — Firestore security rules

Paste these at **Firestore Database → Rules**:

```
rules_version = '2';

service cloud.firestore {
  match /databases/{database}/documents {
    // Briefs are readable by any signed-in caller, including
    // anonymous ones, and writable only by the service account,
    // which bypasses these rules entirely.
    match /briefs/{date} {
      allow read: if request.auth != null;
      allow write: if false;
    }
  }
}
```

`allow write: if false` is not a mistake. The Admin SDK bypasses rules, so
the backend still writes; this stops anything else from doing so.

## Step 5 — Run it

```bash
cd mobile
flutter run
```

You need Android Studio or the Android SDK installed, and a device or
emulator. First run takes a few minutes.

If Firestore has no briefs yet, the app shows "No brief yet" — correct
behaviour, not a failure. Trigger `daily-brief.yml` manually from the
Actions tab to publish one.

## Step 6 — Release to the Play Store

### Create an upload keystore

```bash
keytool -genkey -v -keystore ~/pulsex-upload.jks \
  -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

**Back this file up.** Lose it and you cannot ship updates to an existing
listing without Google's help.

Then create `mobile/android/key.properties`:

```properties
storePassword=<password>
keyPassword=<password>
keyAlias=upload
storeFile=/absolute/path/to/pulsex-upload.jks
```

That file is gitignored. Without it the release build falls back to the
debug key, so local release builds keep working.

### Build

```bash
flutter build appbundle --release
```

The bundle lands at `build/app/outputs/bundle/release/app-release.aab`.

### Upload

1. Create the app at [play.google.com/console](https://play.google.com/console).
   A developer account is a one-off $25.
2. Upload the `.aab` to internal testing first. It reaches only testers
   you name and skips the full review wait.
3. Play requires a privacy policy URL, a data safety declaration, and
   store assets: an icon, a feature graphic and screenshots.

Declare honestly in the data safety form: the app collects no personal
data, uses anonymous authentication, and stores bookmarks only on the
device.

## Versioning

Both the version name and code come from `mobile/pubspec.yaml`:

```yaml
version: 1.0.0+1
```

`1.0.0` is what users see; `+1` is the version code, which **must
increase on every Play Store upload**. Bump it before each build.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `UnsupportedError: Firebase is not configured yet` | Step 2 not run |
| Build fails on `google-services.json` | Step 2 not run, or it's in the wrong directory |
| App opens but shows "Could not load" | Rules from step 4 missing, or Anonymous auth not enabled |
| "No brief yet" | Firestore is genuinely empty; run the workflow |
| No notification arrives | Notification permission denied, or the run's FCM step failed |
| Notification arrives, tapping does nothing | Check the `default_notification_channel_id` in the manifest matches the backend's channel |
| Release build has no network | The `INTERNET` permission is in the main manifest; do not remove it |

## Design notes

**Topic rather than device tokens.** The backend publishes to the
`daily_brief` topic and the app subscribes on first run, so there is no
device registry to maintain and no token refresh to handle.

**Items embedded in the brief document.** Opening a day costs one
Firestore read, not a collection query. Fifteen summarized items sit far
inside the 1 MB document limit.

**Bookmarks are device-local.** Only ids are stored, so a saved story
appears in the list once the brief it came from has been opened in the
session. That keeps the store tiny; real sign-in would be the fix if you
want cross-device bookmarks.

**Every Firestore field is read defensively.** A brief missing an optional
value still renders. Summarization can fail for a single item without
failing the run, so a story with no summary is a real case the app
handles rather than a hypothetical one.
