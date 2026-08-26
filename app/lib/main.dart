import 'package:flutter/material.dart';

import 'screens/home_screen.dart';
import 'services/settings.dart';
import 'theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final settings = await Settings.load();
  runApp(KorbKlarApp(settings: settings));
}

class KorbKlarApp extends StatelessWidget {
  const KorbKlarApp({super.key, required this.settings});

  final Settings settings;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'KorbKlar',
      debugShowCheckedModeBanner: false,
      theme: korbLightTheme(),
      darkTheme: korbDarkTheme(),
      // The web interface declares `color-scheme: light dark`, so the app
      // follows the system setting the same way.
      themeMode: ThemeMode.system,
      home: HomeScreen(settings: settings),
    );
  }
}

/// The wordmark used on both screens, matching the web header.
class KorbKlarWordmark extends StatelessWidget {
  const KorbKlarWordmark({super.key, this.fontSize = 25});

  final double fontSize;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Text.rich(
      TextSpan(
        children: [
          TextSpan(text: 'Korb', style: TextStyle(color: colors.text)),
          TextSpan(text: 'Klar', style: TextStyle(color: colors.accent)),
        ],
      ),
      style: TextStyle(fontSize: fontSize, fontWeight: FontWeight.w700),
    );
  }
}
