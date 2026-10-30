import 'package:geolocator/geolocator.dart';

/// Resolves the device's current position, handling permissions and the
/// "location services disabled" case.
class LocationService {
  /// Returns the current [Position], or throws a [LocationException] with a
  /// user-friendly message if it can't be obtained.
  Future<Position> getCurrentPosition() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw LocationException(
        'Los servicios de ubicación están desactivados.',
      );
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        throw LocationException('Permiso de ubicación denegado.');
      }
    }

    if (permission == LocationPermission.deniedForever) {
      throw LocationException(
        'Permiso de ubicación denegado permanentemente. '
        'Actívalo desde los ajustes del sistema.',
      );
    }

    return Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
    );
  }
}

class LocationException implements Exception {
  final String message;
  LocationException(this.message);

  @override
  String toString() => message;
}
