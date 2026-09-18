import 'package:flutter/material.dart';

/// The app's single light theme.
///
/// Kept in one place so a dark variant can be added later
/// without touching any widget.
class PulseTheme {
  static const seed = Color(0xFF1D4ED8);

  static const paper = Color(0xFFF7F8FA);
  static const card = Colors.white;
  static const ink = Color(0xFF14161A);
  static const muted = Color(0xFF6B7280);
  static const hairline = Color(0xFFE6E8EC);
  static const paperAccent = Color(0xFF7C3AED);

  static ThemeData get light {
    final base = ThemeData(
      colorScheme: ColorScheme.fromSeed(seedColor: seed),
      useMaterial3: true,
    );

    return base.copyWith(
      scaffoldBackgroundColor: paper,
      appBarTheme: const AppBarTheme(
        backgroundColor: card,
        foregroundColor: ink,
        elevation: 0,
        centerTitle: false,
      ),
      textTheme: base.textTheme.apply(
        bodyColor: ink,
        displayColor: ink,
      ),
    );
  }

  /// The accent colour for a kind of story.
  static Color accentFor({required bool isPaper}) {
    return isPaper ? paperAccent : seed;
  }
}
