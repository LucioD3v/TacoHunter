import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

import '../config.dart';
import '../models/search_result.dart';
import '../models/taqueria.dart';
import '../services/location_service.dart';
import '../services/taco_api.dart';

/// Main screen: an interactive Google Map plus a craving search bar that
/// consumes the TacoHunter Lambda and drops a marker per matching taquería.
class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  final Completer<GoogleMapController> _mapController = Completer();
  final TextEditingController _promptController = TextEditingController();
  final LocationService _locationService = LocationService();
  final TacoApi _api = TacoApi();
  final DraggableScrollableController _sheetController =
      DraggableScrollableController();

  /// Index of the currently selected taquería in [_results] (for highlight).
  int? _selectedIndex;

  LatLng _userLocation =
      const LatLng(AppConfig.defaultLat, AppConfig.defaultLng);
  Set<Marker> _markers = {};
  bool _loading = false;
  SearchIntent? _lastIntent;

  /// Latest results, sorted nearest-first, kept so the "fit results" action
  /// can recompute the camera bounds.
  List<Taqueria> _results = const [];

  @override
  void initState() {
    super.initState();
    _initLocation();
  }

  @override
  void dispose() {
    _promptController.dispose();
    _sheetController.dispose();
    _api.dispose();
    super.dispose();
  }

  Future<void> _initLocation() async {
    try {
      final pos = await _locationService.getCurrentPosition();
      final loc = LatLng(pos.latitude, pos.longitude);
      setState(() => _userLocation = loc);
      await _animateTo(loc, AppConfig.defaultZoom);
    } catch (e) {
      // Fall back to the default camera target; just inform the user.
      _showSnack(e.toString());
    }
  }

  Future<void> _animateTo(LatLng target, double zoom) async {
    final controller = await _mapController.future;
    await controller.animateCamera(
      CameraUpdate.newLatLngZoom(target, zoom),
    );
  }

  Future<void> _search() async {
    final prompt = _promptController.text.trim();
    if (prompt.isEmpty) {
      _showSnack('Escribe tu antojo primero.');
      return;
    }

    FocusScope.of(context).unfocus();
    setState(() => _loading = true);

    try {
      final SearchResult result = await _api.search(
        userPrompt: prompt,
        userLat: _userLocation.latitude,
        userLng: _userLocation.longitude,
      );

      final sorted = _sortByDistance(result.taquerias);

      setState(() {
        _lastIntent = result.intent;
        _results = sorted;
        _selectedIndex = null;
        _markers = _buildMarkers(sorted);
      });

      if (sorted.isEmpty) {
        _showSnack('No encontramos taquerías para ese antojo.');
      } else {
        _showSnack(
          'Encontramos ${result.count} taquería(s) · '
          '${result.intent.specialty} / ${result.intent.vibe}',
        );
        // Recenter the map over the results.
        await _fitToResults();
      }
    } catch (e) {
      _showSnack(e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Sort taquerías nearest-first relative to the user's location.
  /// Items without coordinates are pushed to the end.
  List<Taqueria> _sortByDistance(List<Taqueria> taquerias) {
    final list = List<Taqueria>.from(taquerias);
    list.sort((a, b) {
      final da = a.distanceKmFrom(_userLocation.latitude, _userLocation.longitude);
      final db = b.distanceKmFrom(_userLocation.latitude, _userLocation.longitude);
      if (da == null && db == null) return 0;
      if (da == null) return 1;
      if (db == null) return -1;
      return da.compareTo(db);
    });
    return list;
  }

  /// Human-readable distance label (e.g. "850 m" or "2.4 km").
  String _distanceLabel(double km) {
    if (km < 1) return '${(km * 1000).round()} m';
    return '${km.toStringAsFixed(1)} km';
  }

  /// Stable marker id tied to the result index, so the list and the map share
  /// the same identity and we can open a specific InfoWindow on tap.
  MarkerId _markerIdFor(int index) => MarkerId('taqueria_$index');

  Set<Marker> _buildMarkers(List<Taqueria> taquerias) {
    final markers = <Marker>{};
    for (var i = 0; i < taquerias.length; i++) {
      final t = taquerias[i];
      if (!t.hasLocation) continue;
      final km =
          t.distanceKmFrom(_userLocation.latitude, _userLocation.longitude);
      markers.add(
        Marker(
          markerId: _markerIdFor(i),
          position: LatLng(t.lat!, t.lng!),
          infoWindow: InfoWindow(
            title: t.name ?? 'Taquería',
            snippet: [
              if (t.specialty != null) t.specialty,
              if (km != null) 'a ${_distanceLabel(km)}',
              if (t.address != null) t.address,
            ].whereType<String>().join(' · '),
          ),
          onTap: () => _selectTaqueria(i, moveSheet: true),
        ),
      );
    }
    return markers;
  }

  /// Focus a taquería: center the camera on its marker, open its InfoWindow,
  /// and highlight its card in the list.
  Future<void> _selectTaqueria(int index, {bool moveSheet = false}) async {
    if (index < 0 || index >= _results.length) return;
    final t = _results[index];
    if (!t.hasLocation) return;

    setState(() => _selectedIndex = index);

    final controller = await _mapController.future;
    await controller.animateCamera(
      CameraUpdate.newLatLngZoom(LatLng(t.lat!, t.lng!), 16),
    );
    // Give the camera a moment, then open the InfoWindow.
    await controller.showMarkerInfoWindow(_markerIdFor(index));

    // Collapse the sheet a bit so the marker stays visible.
    if (moveSheet && _sheetController.isAttached) {
      await _sheetController.animateTo(
        0.28,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    }
  }

  /// Fit the camera so every result marker (plus the user) is visible.
  Future<void> _fitToResults() async {
    final points = <LatLng>[
      _userLocation,
      for (final t in _results)
        if (t.hasLocation) LatLng(t.lat!, t.lng!),
    ];

    if (points.length < 2) {
      // Nothing to frame beyond the user; just center on them.
      await _animateTo(_userLocation, AppConfig.defaultZoom);
      return;
    }

    final bounds = _boundsFromPoints(points);
    final controller = await _mapController.future;
    // 60px padding so markers aren't flush against the screen edges.
    await controller.animateCamera(CameraUpdate.newLatLngBounds(bounds, 60));
  }

  LatLngBounds _boundsFromPoints(List<LatLng> points) {
    var minLat = points.first.latitude;
    var maxLat = points.first.latitude;
    var minLng = points.first.longitude;
    var maxLng = points.first.longitude;

    for (final p in points) {
      minLat = math.min(minLat, p.latitude);
      maxLat = math.max(maxLat, p.latitude);
      minLng = math.min(minLng, p.longitude);
      maxLng = math.max(maxLng, p.longitude);
    }

    return LatLngBounds(
      southwest: LatLng(minLat, minLng),
      northeast: LatLng(maxLat, maxLng),
    );
  }

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButtonLocation: FloatingActionButtonLocation.endFloat,
      floatingActionButton: _results.isEmpty
          ? null
          : Padding(
              // Lift the button above the collapsed bottom sheet.
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).size.height * 0.12,
              ),
              child: FloatingActionButton.extended(
                onPressed: _fitToResults,
                icon: const Icon(Icons.center_focus_strong),
                label: const Text('Ver todos'),
              ),
            ),
      body: Stack(
        children: [
          GoogleMap(
            initialCameraPosition: CameraPosition(
              target: _userLocation,
              zoom: AppConfig.defaultZoom,
            ),
            myLocationEnabled: true,
            myLocationButtonEnabled: true,
            markers: _markers,
            onMapCreated: (controller) {
              if (!_mapController.isCompleted) {
                _mapController.complete(controller);
              }
            },
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                children: [
                  _SearchBar(
                    controller: _promptController,
                    loading: _loading,
                    onSubmit: _search,
                  ),
                  if (_lastIntent != null) ...[
                    const SizedBox(height: 8),
                    _IntentChips(intent: _lastIntent!),
                  ],
                ],
              ),
            ),
          ),
          if (_results.isNotEmpty)
            _ResultsSheet(
              controller: _sheetController,
              results: _results,
              selectedIndex: _selectedIndex,
              userLocation: _userLocation,
              distanceLabel: _distanceLabel,
              onTapResult: (i) => _selectTaqueria(i, moveSheet: true),
            ),
        ],
      ),
    );
  }
}

class _SearchBar extends StatelessWidget {
  final TextEditingController controller;
  final bool loading;
  final VoidCallback onSubmit;

  const _SearchBar({
    required this.controller,
    required this.loading,
    required this.onSubmit,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      elevation: 4,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: Row(
          children: [
            const Icon(Icons.search),
            const SizedBox(width: 8),
            Expanded(
              child: TextField(
                controller: controller,
                textInputAction: TextInputAction.search,
                onSubmitted: (_) => onSubmit(),
                decoration: const InputDecoration(
                  hintText: '¿De qué tienes antojo? (ej. tacos al pastor)',
                  border: InputBorder.none,
                ),
              ),
            ),
            if (loading)
              const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            else
              IconButton(
                icon: const Icon(Icons.send),
                onPressed: onSubmit,
              ),
          ],
        ),
      ),
    );
  }
}

class _IntentChips extends StatelessWidget {
  final SearchIntent intent;

  const _IntentChips({required this.intent});

  @override
  Widget build(BuildContext context) {
    final chips = <Widget>[
      Chip(label: Text('🌮 ${intent.specialty}')),
      Chip(label: Text('✨ ${intent.vibe}')),
      ...intent.searchKeywords.map((k) => Chip(label: Text(k))),
    ];

    return Align(
      alignment: Alignment.centerLeft,
      child: Wrap(spacing: 6, runSpacing: 6, children: chips),
    );
  }
}

/// Draggable bottom sheet listing the results nearest-first. Tapping a card
/// focuses its marker on the map.
class _ResultsSheet extends StatelessWidget {
  final DraggableScrollableController controller;
  final List<Taqueria> results;
  final int? selectedIndex;
  final LatLng userLocation;
  final String Function(double km) distanceLabel;
  final ValueChanged<int> onTapResult;

  const _ResultsSheet({
    required this.controller,
    required this.results,
    required this.selectedIndex,
    required this.userLocation,
    required this.distanceLabel,
    required this.onTapResult,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return DraggableScrollableSheet(
      controller: controller,
      initialChildSize: 0.32,
      minChildSize: 0.12,
      maxChildSize: 0.85,
      snap: true,
      snapSizes: const [0.12, 0.32, 0.85],
      builder: (context, scrollController) {
        return Material(
          elevation: 12,
          color: theme.colorScheme.surface,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          child: Column(
            children: [
              // Grab handle.
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 10),
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: theme.colorScheme.onSurfaceVariant
                        .withValues(alpha: 0.4),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: Row(
                  children: [
                    Icon(Icons.restaurant, size: 18, color: theme.colorScheme.primary),
                    const SizedBox(width: 8),
                    Text(
                      '${results.length} taquería${results.length == 1 ? '' : 's'} cerca de ti',
                      style: theme.textTheme.titleMedium,
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: ListView.separated(
                  controller: scrollController,
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  itemCount: results.length,
                  separatorBuilder: (_, __) => const Divider(height: 1, indent: 72),
                  itemBuilder: (context, index) {
                    final t = results[index];
                    final km = t.distanceKmFrom(
                      userLocation.latitude,
                      userLocation.longitude,
                    );
                    return _ResultCard(
                      index: index,
                      taqueria: t,
                      distanceText: km != null ? distanceLabel(km) : null,
                      selected: index == selectedIndex,
                      onTap: () => onTapResult(index),
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _ResultCard extends StatelessWidget {
  final int index;
  final Taqueria taqueria;
  final String? distanceText;
  final bool selected;
  final VoidCallback onTap;

  const _ResultCard({
    required this.index,
    required this.taqueria,
    required this.distanceText,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final subtitleParts = <String>[
      if (taqueria.specialty != null) '🌮 ${taqueria.specialty}',
      if (taqueria.vibe != null) '✨ ${taqueria.vibe}',
    ];

    return Container(
      color: selected
          ? theme.colorScheme.primary.withValues(alpha: 0.08)
          : Colors.transparent,
      child: ListTile(
        onTap: onTap,
        leading: CircleAvatar(
          backgroundColor: selected
              ? theme.colorScheme.primary
              : theme.colorScheme.primaryContainer,
          foregroundColor: selected
              ? theme.colorScheme.onPrimary
              : theme.colorScheme.onPrimaryContainer,
          child: Text('${index + 1}'),
        ),
        title: Text(
          taqueria.name ?? 'Taquería',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (subtitleParts.isNotEmpty) Text(subtitleParts.join('  ')),
            if (taqueria.address != null)
              Text(
                taqueria.address!,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodySmall,
              ),
          ],
        ),
        trailing: distanceText == null
            ? const Icon(Icons.chevron_right)
            : Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Icon(Icons.near_me,
                      size: 16, color: theme.colorScheme.primary),
                  const SizedBox(height: 2),
                  Text(
                    distanceText!,
                    style: theme.textTheme.labelMedium?.copyWith(
                      color: theme.colorScheme.primary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
