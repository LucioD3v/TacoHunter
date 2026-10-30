import 'package:flutter/material.dart';

import 'screens/map_screen.dart';

void main() {
  runApp(const TacoHunterApp());
}

class TacoHunterApp extends StatelessWidget {
  const TacoHunterApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TacoHunter',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFE63946),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: const MapScreen(),
    );
  }
}
