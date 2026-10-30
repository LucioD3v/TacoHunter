import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/search_result.dart';

/// Thin client for the TacoHunter Lambda (via API Gateway).
class TacoApi {
  final http.Client _client;
  final String baseUrl;

  TacoApi({http.Client? client, String? baseUrl})
      : _client = client ?? http.Client(),
        baseUrl = baseUrl ?? AppConfig.apiBaseUrl;

  /// Send a craving + location to the Lambda and parse the structured result.
  ///
  /// Throws [TacoApiException] on transport or non-200 responses.
  Future<SearchResult> search({
    required String userPrompt,
    required double userLat,
    required double userLng,
  }) async {
    final uri = Uri.parse(baseUrl);

    http.Response response;
    try {
      response = await _client.post(
        uri,
        headers: const {'Content-Type': 'application/json'},
        body: jsonEncode({
          'user_prompt': userPrompt,
          'user_lat': userLat,
          'user_lng': userLng,
        }),
      );
    } catch (e) {
      throw TacoApiException('No se pudo conectar con el servidor: $e');
    }

    if (response.statusCode != 200) {
      throw TacoApiException(
        'El servidor respondió ${response.statusCode}.',
        body: response.body,
      );
    }

    final Map<String, dynamic> json =
        jsonDecode(response.body) as Map<String, dynamic>;
    return SearchResult.fromJson(json);
  }

  void dispose() => _client.close();
}

class TacoApiException implements Exception {
  final String message;
  final String? body;

  TacoApiException(this.message, {this.body});

  @override
  String toString() => 'TacoApiException: $message';
}
