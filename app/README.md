# TacoHunter · Flutter app

Cliente móvil de TacoHunter: muestra un mapa interactivo de **Amazon Location
Service** (renderizado con MapLibre), obtiene la ubicación del usuario y consume
la Lambda de backend para traducir un antojo en lenguaje natural a taquerías
cercanas.

## Estructura

```
app/
├── pubspec.yaml                  # Dependencias (maplibre_gl, geolocator, http)
├── lib/
│   ├── main.dart                 # Entry point + tema
│   ├── config.dart               # Endpoint de la Lambda + config de Amazon Location Service
│   ├── models/
│   │   ├── taqueria.dart         # Modelo de taquería (store_id, name, lat, lng, ...)
│   │   └── search_result.dart    # Respuesta de la Lambda (intent + taquerias)
│   ├── services/
│   │   ├── location_service.dart # Permisos + posición actual (geolocator)
│   │   └── taco_api.dart         # Cliente HTTP de la Lambda
│   └── screens/
│       └── map_screen.dart       # Mapa ALS/MapLibre + búsqueda + símbolos
├── android/app/src/main/AndroidManifest.xml  # Permisos (internet + ubicación)
└── ios/Runner/
    ├── Info.plist                # Permisos de ubicación
    └── AppDelegate.swift         # Sin SDK de mapas (MapLibre + ALS por URL)
```

## El mapa: Amazon Location Service

El mapa base se sirve desde un recurso **Map** de Amazon Location Service como
estilo compatible con MapLibre. La app apunta `maplibre_gl` a la URL del estilo:

```
https://maps.geo.<region>.amazonaws.com/maps/v0/maps/<MapName>/style-descriptor?key=<ApiKey>
```

No se embebe ninguna clave de proveedor de mapas en el código nativo: la API key
de Amazon Location Service se pasa en tiempo de ejecución dentro de esa URL
(ver `lib/config.dart`).

## Contrato con la Lambda

`POST` a `AppConfig.apiBaseUrl` con:

```json
{ "user_prompt": "tacos al pastor para la cruda", "user_lat": 19.41, "user_lng": -99.17 }
```

Respuesta esperada (status 200, CORS habilitado):

```json
{
  "intent": { "specialty": "pastor", "vibe": "crudo", "search_keywords": ["pastor"] },
  "user_location": { "lat": 19.41, "lng": -99.17 },
  "count": 2,
  "taquerias": [
    { "store_id": "s1", "name": "El Califa", "specialty": "pastor",
      "vibe": "nocturno", "address": "...", "lat": 19.41, "lng": -99.17 }
  ]
}
```

## Puesta en marcha

1. Genera el andamiaje de plataforma (este template solo incluye los archivos
   personalizados; el resto lo crea Flutter):

   ```bash
   cd app
   flutter create .
   ```

   > `flutter create .` respeta los archivos existentes de `lib/`, `pubspec.yaml`,
   > el `AndroidManifest.xml`, `Info.plist` y `AppDelegate.swift` ya incluidos.

2. Instala dependencias:

   ```bash
   flutter pub get
   ```

3. Configura el endpoint y Amazon Location Service en `lib/config.dart`:
   - `apiBaseUrl` → la URL de tu API Gateway.
   - `alsRegion` → región de tus recursos de Amazon Location (p. ej. `us-east-1`).
   - `alsMapName` → nombre del recurso Map (p. ej. `TacoRadar-Map`).
   - `alsApiKey` → API key de Amazon Location Service con alcance al Map.

4. Ejecuta:

   ```bash
   flutter run
   ```

## Notas

- El mapa se renderiza con `maplibre_gl`; Android requiere `minSdkVersion >= 21`.
- iOS requiere plataforma mínima 14.0 (ajústalo en `ios/Podfile`).
- La API key de Amazon Location Service debe estar restringida al recurso Map
  (y opcionalmente a Places/Routes si los agregas).
