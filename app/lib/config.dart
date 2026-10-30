/// App-wide configuration.
///
/// Replace [apiBaseUrl] with the invoke URL of the API Gateway endpoint that
/// fronts the TacoHunter Lambda (e.g. an HTTP API or REST API stage URL).
class AppConfig {
  /// Full URL to the endpoint that triggers the Lambda.
  ///
  /// The Lambda expects a POST with a JSON body:
  /// `{ "user_prompt": "...", "user_lat": 19.41, "user_lng": -99.17 }`
  static const String apiBaseUrl =
      'https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/search';

  /// Default map camera target (CDMX center) used before the user's location
  /// is resolved.
  static const double defaultLat = 19.4326;
  static const double defaultLng = -99.1332;
  static const double defaultZoom = 13.0;
}
