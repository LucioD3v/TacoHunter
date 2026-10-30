# TacoHunter · Flutter app

Cliente móvil de TacoHunter: muestra un mapa interactivo, obtiene la ubicación
del usuario y consume la Lambda de backend para traducir un antojo en lenguaje
natural a taquerías cercanas.

## Estructura

```
app/
├── pubspec.yaml                  # Dependencias (google_maps_flutter, geolocator, http)
├── lib/
│   ├── main.dart                 # Entry point + tema
│   ├── config.dart               # URL del endpoint + defaults del mapa
│   ├── models/
│   │   ├── taqueria.dart         # Modelo de taquería (store_id, name, lat, lng, ...)
│   │   └── search_result.dart    # Respuesta de la Lambda (intent + taquerias)
│   ├── services/
│   │   ├── location_service.dart # Permisos + posición actual (geolocator)
│   │   └── taco_api.dart         # Cliente HTTP de la Lambda
│   └── screens/
│       └── map_screen.dart       # Mapa + barra de búsqueda + marcadores
├── android/app/src/main/AndroidManifest.xml  # Permisos + API key Android
└── ios/Runner/
    ├── Info.plist                # Permisos de ubicación
    └── AppDelegate.swift         # API key de Google Maps iOS
```

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

3. Configura las claves y el endpoint:
   - `lib/config.dart` → `apiBaseUrl` con la URL de tu API Gateway.
   - `android/app/src/main/AndroidManifest.xml` → `YOUR_ANDROID_MAPS_API_KEY`.
   - `ios/Runner/AppDelegate.swift` → `YOUR_IOS_MAPS_API_KEY`.

4. Ejecuta:

   ```bash
   flutter run
   ```

## Notas

- Android requiere `minSdkVersion >= 21` para `google_maps_flutter`.
- iOS requiere plataforma mínima 14.0 (ajústalo en `ios/Podfile`).
- Las claves de Google Maps de Android e iOS son distintas y deben tener
  habilitadas las APIs "Maps SDK for Android" / "Maps SDK for iOS".
