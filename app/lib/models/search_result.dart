import 'taqueria.dart';

/// The detected intent block returned by the Lambda (from Bedrock).
///
/// Named `SearchIntent` (not `Intent`) to avoid clashing with Flutter's
/// `Intent` class from the Actions/Shortcuts framework.
class SearchIntent {
  final String specialty;
  final String vibe;
  final List<String> searchKeywords;

  const SearchIntent({
    required this.specialty,
    required this.vibe,
    required this.searchKeywords,
  });

  factory SearchIntent.fromJson(Map<String, dynamic> json) {
    final keywords = (json['search_keywords'] as List?) ?? const [];
    return SearchIntent(
      specialty: json['specialty']?.toString() ?? 'all',
      vibe: json['vibe']?.toString() ?? 'all',
      searchKeywords: keywords.map((e) => e.toString()).toList(),
    );
  }
}

/// Full response payload from the Lambda:
/// `{ intent, user_location, count, taquerias }`.
class SearchResult {
  final SearchIntent intent;
  final int count;
  final List<Taqueria> taquerias;

  const SearchResult({
    required this.intent,
    required this.count,
    required this.taquerias,
  });

  factory SearchResult.fromJson(Map<String, dynamic> json) {
    final list = (json['taquerias'] as List?) ?? const [];
    return SearchResult(
      intent: SearchIntent.fromJson(
        (json['intent'] as Map?)?.cast<String, dynamic>() ?? const {},
      ),
      count: (json['count'] as num?)?.toInt() ?? list.length,
      taquerias: list
          .map((e) => Taqueria.fromJson((e as Map).cast<String, dynamic>()))
          .toList(),
    );
  }
}
