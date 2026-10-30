import 'dart:math' as math;

/// A single taquería returned by the Lambda.
///
/// Maps one element of the `taquerias` array in the Lambda response:
/// `{ store_id, name, specialty, vibe, address, lat, lng }`.
class Taqueria {
  final String? storeId;
  final String? name;
  final String? specialty;
  final String? vibe;
  final String? address;
  final double? lat;
  final double? lng;

  const Taqueria({
    this.storeId,
    this.name,
    this.specialty,
    this.vibe,
    this.address,
    this.lat,
    this.lng,
  });

  factory Taqueria.fromJson(Map<String, dynamic> json) {
    return Taqueria(
      storeId: json['store_id']?.toString(),
      name: json['name']?.toString(),
      specialty: json['specialty']?.toString(),
      vibe: json['vibe']?.toString(),
      address: json['address']?.toString(),
      lat: _toDouble(json['lat']),
      lng: _toDouble(json['lng']),
    );
  }

  /// Whether this taquería has usable coordinates for the map.
  bool get hasLocation => lat != null && lng != null;

  /// Great-circle distance in kilometers from [fromLat]/[fromLng] to this
  /// taquería, using the Haversine formula. Returns `null` if this taquería
  /// has no coordinates.
  double? distanceKmFrom(double fromLat, double fromLng) {
    if (!hasLocation) return null;

    const earthRadiusKm = 6371.0;
    final dLat = _toRadians(lat! - fromLat);
    final dLng = _toRadians(lng! - fromLng);

    final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
        math.cos(_toRadians(fromLat)) *
            math.cos(_toRadians(lat!)) *
            math.sin(dLng / 2) *
            math.sin(dLng / 2);
    final c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));

    return earthRadiusKm * c;
  }

  static double _toRadians(double degrees) => degrees * math.pi / 180.0;

  static double? _toDouble(dynamic value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    return double.tryParse(value.toString());
  }
}
