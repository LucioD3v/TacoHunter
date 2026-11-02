# TacoHunter

[![CI](https://github.com/LucioD3v/TacoHunter/actions/workflows/ci.yml/badge.svg)](https://github.com/LucioD3v/TacoHunter/actions/workflows/ci.yml)

**Craving-based taquería discovery, on Amazon Location Service.**

TacoHunter turns a craving written in plain language into an exploration on a
map. You type *"tacos al pastor for the hangover"* and the app interprets your
intent with AI, filters a curated dataset of iconic Mexico City taquerías, and
drops them on an Amazon Location Service map — sorted by how close they are to
you, with a list you can tap to focus each pin.

Built for the AWS Builder Center **"Weekend Challenge: Map it"** hackathon.

---

## Why

In Mexico City the challenge isn't *where are the tacos* (there are thousands),
it's *which one do I want right now*. What you want depends on context:
"something for the hangover," "pastor at midnight," "quiet carnitas with
family." Traditional map apps make you translate that craving into filters
yourself. TacoHunter lets you explore the map by **intent**, in natural
language.

## How it works

1. The app sends your craving + location to **Amazon API Gateway**.
2. **AWS Lambda** prompts **Amazon Bedrock**, which returns a structured intent
   (`specialty`, `vibe`, `search_keywords`) as strict JSON.
3. The Lambda queries **Amazon DynamoDB** and filters taquerías by specialty and
   vibe.
4. The app renders the matches as symbols on an **Amazon Location Service** map,
   sorted nearest-first, with an explorable results list.

## Architecture

```text
                    +-------------------------------+
                    |         Flutter app           |
                    |  (map: Amazon Location /       |
                    |        MapLibre GL)            |
                    +---------------+---------------+
                                    |
             POST { craving, lat, lng }  (HTTPS)
                                    |
                                    v
                    +-------------------------------+
                    |   Amazon API Gateway (HTTP)   |
                    +---------------+---------------+
                                    |
                                    v
                    +-------------------------------+
                    |     AWS Lambda (Python 3.12)  |
                    |  orchestrates prompt + filter |
                    +------+-----------------+------+
                           |                 |
             intent (JSON) |                 | scan + filter
                           v                 v
         +-------------------------+   +------------------------+
         |     Amazon Bedrock      |   |    Amazon DynamoDB     |
         |  Nova Micro             |   |   TacoRadar-Stores     |
         |  (fallback Claude 3     |   |   (place dataset)      |
         |   Haiku)                |   |                        |
         +-------------------------+   +------------------------+
```

## AWS services

| Service | Role |
| --- | --- |
| **Amazon Location Service** | Interactive base map (Map resource served as a MapLibre style). |
| **Amazon Bedrock** | Natural-language craving → structured intent (Nova Micro, Claude 3 Haiku fallback). |
| **AWS Lambda** (Python 3.12) | Orchestration: Bedrock prompt, response parsing, DynamoDB filtering, CORS. |
| **Amazon DynamoDB** | `TacoRadar-Stores` — serverless store for the place dataset. |
| **Amazon API Gateway** (HTTP API) | Exposes the Lambda to the client with CORS. |

## Repository layout

```
.
├── lambda_function.py          # AWS Lambda: Bedrock + DynamoDB + CORS response
├── scripts/
│   └── seed_stores.py          # Seed TacoRadar-Stores with 17 CDMX taquerías
├── tests/
│   ├── test_lambda_function.py # Unit tests for the Lambda helpers
│   └── test_seed_stores.py     # Validates the seed dataset (schema/enums)
├── app/                        # Flutter client
│   ├── lib/
│   │   ├── config.dart         # API endpoint + Amazon Location Service config
│   │   ├── models/             # Taqueria, SearchResult/SearchIntent
│   │   ├── services/           # Location (geolocator) + HTTP client
│   │   └── screens/
│   │       └── map_screen.dart # ALS/MapLibre map + search + results sheet
│   └── test/                   # Widget + model unit tests
└── .github/workflows/ci.yml    # CI: Python + Flutter test suites
```

## Getting started

### 1. Backend (AWS)

Deploy in **us-east-1**:

- **Bedrock** — enable model access to `amazon.nova-micro-v1:0` and
  `anthropic.claude-3-haiku-20240307-v1:0`.
- **DynamoDB** — table `TacoRadar-Stores`, partition key `store_id` (String).
- **Lambda** — Python 3.12 running `lambda_function.py`; the execution role
  needs `bedrock:InvokeModel`, `dynamodb:Scan`/`Query` on the table, plus logs.
- **API Gateway** — HTTP API with a `POST /search` route and CORS enabled.

### 2. Seed the DynamoDB table

```bash
# Preview without writing (no AWS calls)
python scripts/seed_stores.py --dry-run

# Write to the table (requires AWS credentials)
python scripts/seed_stores.py

# Create the table first if it doesn't exist, then seed
python scripts/seed_stores.py --create-table
```

Options: `--table` (default `TacoRadar-Stores`), `--region` (default
`us-east-1`). Coordinates are approximate and meant for development/demo use.

### 3. Amazon Location Service (map)

Create a **Map** resource named `TacoRadar-Map` and an **API key** scoped to it
(actions: `geo:GetMapStyleDescriptor`, `geo:GetMapTile`, `geo:GetMapGlyphs`,
`geo:GetMapSprites`).

### 4. Flutter app

```bash
cd app
flutter create .      # generates platform scaffolding (keeps existing files)
flutter pub get
flutter run
```

Fill in `app/lib/config.dart`:

- `apiBaseUrl` — your API Gateway invoke URL (ending in `/search`).
- `alsRegion`, `alsMapName`, `alsApiKey` — your Amazon Location Service values.

## Tests

```bash
# Backend (Python)
python -m unittest discover -s tests -p "test_*.py"

# App (Flutter)
cd app && flutter analyze && flutter test
```

Both suites run automatically on every pull request via GitHub Actions
(`.github/workflows/ci.yml`).

## A reusable pattern

The *craving → intent (AI) → dataset filter → explorable map* flow isn't
specific to tacos. Swap the dataset and the prompt and you get a map people
explore by speaking their own language — coffee shops, clinics, stations,
tourist points of interest.
