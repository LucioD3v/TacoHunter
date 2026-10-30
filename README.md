# TacoHunter

[![CI](https://github.com/LucioD3v/TacoHunter/actions/workflows/ci.yml/badge.svg)](https://github.com/LucioD3v/TacoHunter/actions/workflows/ci.yml)

TacoHunter is an AI-powered, context-aware geospatial discovery engine built on AWS. It translates natural language cravings into real-time, hyper-local taquería and street food recommendations on interactive maps.

## Seed the DynamoDB table

Populate `TacoRadar-Stores` with iconic CDMX taquerías (schema matches the
Lambda: `store_id`, `name`, `specialty`, `vibe`, `address`, `lat`, `lng`):

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
