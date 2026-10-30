#!/usr/bin/env python3
"""
Seed the TacoRadar-Stores DynamoDB table with iconic CDMX taquerías.

Each item follows the schema the Lambda expects:
    store_id, name, specialty, vibe, address, lat, lng

Enum values match lambda_function.py:
    specialty: suadero | pastor | carnitas | cabeza | barbacoa | all
    vibe:      crudo | nocturno | rapido | familiar | all

Coordinates are approximate (hand-placed from public map data) and intended
for development/demo use — verify them before relying on them in production.

Usage:
    python scripts/seed_stores.py                         # write to the table
    python scripts/seed_stores.py --dry-run               # print, don't write
    python scripts/seed_stores.py --table MyTable --region us-east-1
    python scripts/seed_stores.py --create-table          # create table if missing

Requires AWS credentials in the environment (e.g. via `aws configure`,
environment variables, or an assumed role).
"""

import argparse
import sys
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

DEFAULT_TABLE = "TacoRadar-Stores"
DEFAULT_REGION = "us-east-1"

VALID_SPECIALTIES = {"suadero", "pastor", "carnitas", "cabeza", "barbacoa", "all"}
VALID_VIBES = {"crudo", "nocturno", "rapido", "familiar", "all"}

# ---------------------------------------------------------------------------
# Seed data: iconic CDMX taquerías.
# Coordinates are approximate; adjust if you need pinpoint accuracy.
# ---------------------------------------------------------------------------
STORES = [
    {
        "store_id": "el-vilsito",
        "name": "El Vilsito",
        "specialty": "pastor",
        "vibe": "nocturno",
        "address": "Av. Universidad 248, Narvarte, Benito Juárez",
        "lat": 19.3881,
        "lng": -99.1575,
    },
    {
        "store_id": "el-huequito-centro",
        "name": "El Huequito (Centro)",
        "specialty": "pastor",
        "vibe": "rapido",
        "address": "Ayuntamiento 21, Centro, Cuauhtémoc",
        "lat": 19.4312,
        "lng": -99.1420,
    },
    {
        "store_id": "los-cocuyos",
        "name": "Los Cocuyos",
        "specialty": "suadero",
        "vibe": "nocturno",
        "address": "Bolívar 57, Centro, Cuauhtémoc",
        "lat": 19.4305,
        "lng": -99.1398,
    },
    {
        "store_id": "el-califa-condesa",
        "name": "El Califa (Condesa)",
        "specialty": "suadero",
        "vibe": "nocturno",
        "address": "Altata 22, Condesa, Cuauhtémoc",
        "lat": 19.4115,
        "lng": -99.1795,
    },
    {
        "store_id": "el-tizoncito",
        "name": "El Tizoncito",
        "specialty": "pastor",
        "vibe": "familiar",
        "address": "Tamaulipas 122, Condesa, Cuauhtémoc",
        "lat": 19.4113,
        "lng": -99.1756,
    },
    {
        "store_id": "tacos-hola-condesa",
        "name": "Tacos Hola El Güero",
        "specialty": "carnitas",
        "vibe": "rapido",
        "address": "Amsterdam 135, Hipódromo, Cuauhtémoc",
        "lat": 19.4098,
        "lng": -99.1702,
    },
    {
        "store_id": "carnitas-el-paisa",
        "name": "Carnitas El Paisa",
        "specialty": "carnitas",
        "vibe": "familiar",
        "address": "Mercado de Coyoacán, Coyoacán",
        "lat": 19.3503,
        "lng": -99.1626,
    },
    {
        "store_id": "cabeza-los-parados",
        "name": "Tacos de Cabeza Los Parados",
        "specialty": "cabeza",
        "vibe": "nocturno",
        "address": "Monterrey 333, Roma Sur, Cuauhtémoc",
        "lat": 19.4061,
        "lng": -99.1626,
    },
    {
        "store_id": "barbacoa-el-hidalguense",
        "name": "El Hidalguense",
        "specialty": "barbacoa",
        "vibe": "familiar",
        "address": "Campeche 155, Roma Sur, Cuauhtémoc",
        "lat": 19.4056,
        "lng": -99.1643,
    },
    {
        "store_id": "barbacoa-la-polar",
        "name": "La Polar",
        "specialty": "barbacoa",
        "vibe": "familiar",
        "address": "Guillermo Prieto 129, San Rafael, Cuauhtémoc",
        "lat": 19.4432,
        "lng": -99.1621,
    },
    {
        "store_id": "el-borrego-viudo",
        "name": "El Borrego Viudo",
        "specialty": "pastor",
        "vibe": "nocturno",
        "address": "Av. Revolución 241, Tacubaya, Miguel Hidalgo",
        "lat": 19.4015,
        "lng": -99.1878,
    },
    {
        "store_id": "tacos-don-juan",
        "name": "Tacos Don Juan",
        "specialty": "suadero",
        "vibe": "rapido",
        "address": "Atlixco 94, Condesa, Cuauhtémoc",
        "lat": 19.4126,
        "lng": -99.1742,
    },
    {
        "store_id": "tacos-el-greco",
        "name": "Taquería El Greco",
        "specialty": "pastor",
        "vibe": "familiar",
        "address": "Michoacán 54, Condesa, Cuauhtémoc",
        "lat": 19.4109,
        "lng": -99.1716,
    },
    {
        "store_id": "carnitas-don-raymundo",
        "name": "Carnitas Don Raymundo",
        "specialty": "carnitas",
        "vibe": "crudo",
        "address": "Dr. Vértiz 185, Doctores, Cuauhtémoc",
        "lat": 19.4152,
        "lng": -99.1498,
    },
    {
        "store_id": "tacos-alvaro-obregon",
        "name": "Taquería Álvaro Obregón",
        "specialty": "suadero",
        "vibe": "crudo",
        "address": "Álvaro Obregón 100, Roma Norte, Cuauhtémoc",
        "lat": 19.4178,
        "lng": -99.1613,
    },
    {
        "store_id": "cabeza-tacos-coyoacan",
        "name": "Tacos de Cabeza Coyoacán",
        "specialty": "cabeza",
        "vibe": "rapido",
        "address": "Av. México 123, Coyoacán",
        "lat": 19.3556,
        "lng": -99.1618,
    },
    {
        "store_id": "barbacoa-santiago",
        "name": "Barbacoa Santiago",
        "specialty": "barbacoa",
        "vibe": "familiar",
        "address": "Calz. de Tlalpan 1200, Portales, Benito Juárez",
        "lat": 19.3701,
        "lng": -99.1419,
    },
]


def validate(stores):
    """Validate the seed data against the Lambda's expected schema/enums."""
    errors = []
    seen_ids = set()
    for i, s in enumerate(stores):
        where = f"store[{i}] ({s.get('name', '?')})"
        for field in ("store_id", "name", "specialty", "vibe", "address", "lat", "lng"):
            if field not in s:
                errors.append(f"{where}: missing field '{field}'")
        sid = s.get("store_id")
        if sid in seen_ids:
            errors.append(f"{where}: duplicate store_id '{sid}'")
        seen_ids.add(sid)
        if s.get("specialty") not in VALID_SPECIALTIES:
            errors.append(f"{where}: invalid specialty '{s.get('specialty')}'")
        if s.get("vibe") not in VALID_VIBES:
            errors.append(f"{where}: invalid vibe '{s.get('vibe')}'")
        lat, lng = s.get("lat"), s.get("lng")
        if isinstance(lat, (int, float)) and not (-90 <= lat <= 90):
            errors.append(f"{where}: lat {lat} out of range")
        if isinstance(lng, (int, float)) and not (-180 <= lng <= 180):
            errors.append(f"{where}: lng {lng} out of range")
    return errors


def to_item(store):
    """Convert a seed dict into a DynamoDB-safe item (floats -> Decimal)."""
    item = dict(store)
    # DynamoDB does not accept Python floats; use Decimal via str to avoid
    # binary floating-point drift.
    item["lat"] = Decimal(str(store["lat"]))
    item["lng"] = Decimal(str(store["lng"]))
    return item


def table_exists(dynamodb_client, table_name):
    try:
        dynamodb_client.describe_table(TableName=table_name)
        return True
    except dynamodb_client.exceptions.ResourceNotFoundException:
        return False


def create_table(dynamodb_client, table_name):
    """Create an on-demand table keyed by store_id (String)."""
    print(f"Creating table '{table_name}' (on-demand)...")
    dynamodb_client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "store_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "store_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    waiter = dynamodb_client.get_waiter("table_exists")
    waiter.wait(TableName=table_name)
    print("Table is active.")


def seed(table_name, region, dry_run, create_if_missing):
    errors = validate(STORES)
    if errors:
        print("Seed data failed validation:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"{len(STORES)} stores validated.")

    if dry_run:
        print("--dry-run: nothing will be written. Items:")
        for s in STORES:
            print(f"  {s['store_id']:<28} {s['specialty']:<9} {s['vibe']:<9} "
                  f"({s['lat']}, {s['lng']})  {s['name']}")
        return 0

    session = boto3.Session(region_name=region)
    client = session.client("dynamodb")

    if not table_exists(client, table_name):
        if create_if_missing:
            create_table(client, table_name)
        else:
            print(
                f"Table '{table_name}' not found in region '{region}'. "
                f"Re-run with --create-table to create it.",
                file=sys.stderr,
            )
            return 1

    table = session.resource("dynamodb").Table(table_name)
    try:
        with table.batch_writer(overwrite_by_pkeys=["store_id"]) as batch:
            for store in STORES:
                batch.put_item(Item=to_item(store))
    except ClientError as err:
        print(f"Failed to write items: {err}", file=sys.stderr)
        return 1

    print(f"Seeded {len(STORES)} taquerías into '{table_name}' ({region}).")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Seed TacoRadar-Stores with CDMX taquerías.")
    parser.add_argument("--table", default=DEFAULT_TABLE, help="DynamoDB table name.")
    parser.add_argument("--region", default=DEFAULT_REGION, help="AWS region.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate and print the items without writing.")
    parser.add_argument("--create-table", action="store_true",
                        help="Create the table (on-demand, key=store_id) if it doesn't exist.")
    args = parser.parse_args(argv)

    return seed(args.table, args.region, args.dry_run, args.create_table)


if __name__ == "__main__":
    raise SystemExit(main())
