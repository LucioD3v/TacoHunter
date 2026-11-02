/// App-wide configuration.
///
/// Two things must be filled in before running:
///   1. [apiBaseUrl]  – the API Gateway endpoint that fronts the Lambda.
///   2. The Amazon Location Service values ([alsApiKey], [alsRegion],
///      [alsMapName]) used to render the base map.
class AppConfig {
  // -------------------------------------------------------------------------
  // Backend (API Gateway -> Lambda)
  // -------------------------------------------------------------------------

  /// Full URL to the endpoint that triggers the Lambda.
  ///
  /// The Lambda expects a POST with a JSON body:
  /// `{ "user_prompt": "...", "user_lat": 19.41, "user_lng": -99.17 }`
  static const String apiBaseUrl =
      'https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/search';

  // -------------------------------------------------------------------------
  // Amazon Location Service (base map)
  // -------------------------------------------------------------------------

  /// AWS region where the Amazon Location resources live.
  static const String alsRegion = 'us-east-1';

  /// Name of the Map resource created in Amazon Location Service.
  static const String alsMapName = 'TacoRadar-Map';

  /// Amazon Location Service API key (create one scoped to the Map resource).
  /// Replace before running.
  static const String alsApiKey = 'YOUR_ALS_API_KEY';

  /// MapLibre style descriptor URL served by Amazon Location Service.
  ///
  /// Format:
  /// https://maps.geo.<region>.amazonaws.com/maps/v0/maps/<MapName>/style-descriptor?key=<ApiKey>
  static String get alsStyleUrl =>
      'https://maps.geo.$alsRegion.amazonaws.com/maps/v0/maps/'
      '$alsMapName/style-descriptor?key=$alsApiKey';

  // -------------------------------------------------------------------------
  // Default map camera (CDMX center) used before the user's location resolves.
  // -------------------------------------------------------------------------
  static const double defaultLat = 19.4326;
  static const double defaultLng = -99.1332;
  static const double defaultZoom = 12.0;
}
