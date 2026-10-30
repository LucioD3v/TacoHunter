import 'package:flutter_test/flutter_test.dart';
import 'package:taco_hunter/models/taqueria.dart';

void main() {
  group('Taqueria.fromJson', () {
    test('parses all fields with numeric coordinates', () {
      final t = Taqueria.fromJson(const {
        'store_id': 's1',
        'name': 'El Califa',
        'specialty': 'pastor',
        'vibe': 'nocturno',
        'address': 'Av. Siempre Viva 123',
        'lat': 19.41,
        'lng': -99.17,
      });

      expect(t.storeId, 's1');
      expect(t.name, 'El Califa');
      expect(t.specialty, 'pastor');
      expect(t.vibe, 'nocturno');
      expect(t.address, 'Av. Siempre Viva 123');
      expect(t.lat, 19.41);
      expect(t.lng, -99.17);
      expect(t.hasLocation, isTrue);
    });

    test('coerces string coordinates to double', () {
      final t = Taqueria.fromJson(const {'lat': '19.41', 'lng': '-99.17'});
      expect(t.lat, 19.41);
      expect(t.lng, -99.17);
      expect(t.hasLocation, isTrue);
    });

    test('handles missing coordinates', () {
      final t = Taqueria.fromJson(const {'name': 'Sin coords'});
      expect(t.lat, isNull);
      expect(t.lng, isNull);
      expect(t.hasLocation, isFalse);
    });

    test('handles unparseable coordinate strings', () {
      final t = Taqueria.fromJson(const {'lat': 'abc', 'lng': 'xyz'});
      expect(t.lat, isNull);
      expect(t.lng, isNull);
      expect(t.hasLocation, isFalse);
    });
  });

  group('Taqueria.distanceKmFrom (Haversine)', () {
    test('returns ~0 for the same point', () {
      const t = Taqueria(lat: 19.4326, lng: -99.1332);
      final d = t.distanceKmFrom(19.4326, -99.1332);
      expect(d, isNotNull);
      expect(d!, closeTo(0.0, 0.001));
    });

    test('returns null when the taquería has no coordinates', () {
      const t = Taqueria(name: 'Sin coords');
      expect(t.distanceKmFrom(19.43, -99.13), isNull);
    });

    test('computes a known distance within tolerance', () {
      // CDMX Zócalo -> Ángel de la Independencia is ~3.7 km.
      const zocalo = Taqueria(lat: 19.4326, lng: -99.1332);
      final d = zocalo.distanceKmFrom(19.4270, -99.1677);
      expect(d, isNotNull);
      // Allow a generous tolerance; the point is that it's in the right range.
      expect(d!, closeTo(3.7, 0.6));
    });

    test('is symmetric (A->B equals B->A)', () {
      const a = Taqueria(lat: 19.4326, lng: -99.1332);
      const b = Taqueria(lat: 19.3910, lng: -99.1700);
      final ab = a.distanceKmFrom(b.lat!, b.lng!)!;
      final ba = b.distanceKmFrom(a.lat!, a.lng!)!;
      expect(ab, closeTo(ba, 0.0001));
    });

    test('a farther point yields a larger distance', () {
      const origin = Taqueria(lat: 19.4326, lng: -99.1332);
      final near = origin.distanceKmFrom(19.4330, -99.1340)!;
      final far = origin.distanceKmFrom(20.6597, -103.3496)!; // Guadalajara
      expect(far, greaterThan(near));
    });
  });
}
