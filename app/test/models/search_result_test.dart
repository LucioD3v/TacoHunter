import 'package:flutter_test/flutter_test.dart';
import 'package:taco_hunter/models/search_result.dart';

void main() {
  group('SearchIntent.fromJson', () {
    test('parses specialty, vibe and keywords', () {
      final intent = SearchIntent.fromJson(const {
        'specialty': 'pastor',
        'vibe': 'crudo',
        'search_keywords': ['pastor', 'cebollita'],
      });

      expect(intent.specialty, 'pastor');
      expect(intent.vibe, 'crudo');
      expect(intent.searchKeywords, ['pastor', 'cebollita']);
    });

    test('falls back to "all" when fields are missing', () {
      final intent = SearchIntent.fromJson(const {});
      expect(intent.specialty, 'all');
      expect(intent.vibe, 'all');
      expect(intent.searchKeywords, isEmpty);
    });

    test('stringifies non-string keyword entries', () {
      final intent = SearchIntent.fromJson(const {
        'search_keywords': [1, true, 'taco'],
      });
      expect(intent.searchKeywords, ['1', 'true', 'taco']);
    });
  });

  group('SearchResult.fromJson', () {
    test('parses the full Lambda payload', () {
      final result = SearchResult.fromJson(const {
        'intent': {
          'specialty': 'suadero',
          'vibe': 'nocturno',
          'search_keywords': ['suadero'],
        },
        'count': 2,
        'taquerias': [
          {'store_id': 's1', 'name': 'A', 'lat': 19.41, 'lng': -99.17},
          {'store_id': 's2', 'name': 'B', 'lat': 19.42, 'lng': -99.18},
        ],
      });

      expect(result.intent.specialty, 'suadero');
      expect(result.count, 2);
      expect(result.taquerias, hasLength(2));
      expect(result.taquerias.first.name, 'A');
    });

    test('defaults count to the list length when absent', () {
      final result = SearchResult.fromJson(const {
        'taquerias': [
          {'store_id': 's1', 'lat': 19.41, 'lng': -99.17},
        ],
      });
      expect(result.count, 1);
    });

    test('handles an empty / missing taquerias list', () {
      final result = SearchResult.fromJson(const {'count': 0});
      expect(result.taquerias, isEmpty);
      expect(result.count, 0);
      // Intent still defaults safely.
      expect(result.intent.specialty, 'all');
    });
  });
}
