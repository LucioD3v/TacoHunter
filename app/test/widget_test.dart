// Basic smoke test for the TacoHunter app.
//
// Note: the map screen requires platform channels (Google Maps, geolocator),
// so this test only verifies that the root widget builds and renders the
// search bar without throwing.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:taco_hunter/main.dart';

void main() {
  testWidgets('App builds and shows the craving search field',
      (WidgetTester tester) async {
    await tester.pumpWidget(const TacoHunterApp());
    await tester.pump();

    // The search bar hint should be present.
    expect(find.byType(TextField), findsOneWidget);
  });
}
