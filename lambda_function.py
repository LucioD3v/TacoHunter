"""
TacoHunter - AWS Lambda Function
=================================

AI-powered, context-aware geospatial discovery engine.

Flow:
    1. Receive a natural-language craving (`user_prompt`) plus the user's
       current coordinates (`user_lat`, `user_lng`).
    2. Use Amazon Bedrock to translate the craving into a structured intent
       (specialty, vibe, search_keywords) in strict JSON.
    3. Query the `TacoRadar-Stores` DynamoDB table and filter the stores that
       match the detected specialty / vibe.
    4. Return a CORS-enabled HTTP response (status 200) with the detected
       intent and the matching taquerías (including lat/lng coordinates).

Spec reference: .kiro/specs/backend-lambda.md
Runtime: Python 3.12
"""

import json
import logging
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

AWS_REGION = "us-east-1"
DYNAMODB_TABLE_NAME = "TacoRadar-Stores"

# Primary and fallback Bedrock models.
PRIMARY_MODEL_ID = "amazon.nova-micro-v1:0"
FALLBACK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# Allowed enum values (used to sanitise Bedrock output).
VALID_SPECIALTIES = {"suadero", "pastor", "carnitas", "cabeza", "barbacoa", "all"}
VALID_VIBES = {"crudo", "nocturno", "rapido", "familiar", "all"}

# ---------------------------------------------------------------------------
# AWS clients (initialised once per container for reuse across invocations)
# ---------------------------------------------------------------------------
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
stores_table = dynamodb.Table(DYNAMODB_TABLE_NAME)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class DecimalEncoder(json.JSONEncoder):
    """Serialise DynamoDB Decimal values to native JSON numbers."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            # Keep integers as int, everything else as float.
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def build_prompt(user_prompt: str) -> str:
    """Build the instruction prompt that forces strict-JSON output from the model."""
    return (
        "Eres un analizador de intenciones para una app de recomendación de "
        "taquerías en México. A partir de un antojo escrito en lenguaje "
        "natural, extrae la intención del usuario.\n\n"
        "Responde ÚNICAMENTE con un objeto JSON válido. NO uses Markdown, NO "
        "uses bloques de código, NO agregues texto antes ni después del JSON.\n\n"
        "El JSON debe tener EXACTAMENTE esta estructura:\n"
        "{\n"
        '  "specialty": "suadero|pastor|carnitas|cabeza|barbacoa|all",\n'
        '  "vibe": "crudo|nocturno|rapido|familiar|all",\n'
        '  "search_keywords": ["palabras", "clave"]\n'
        "}\n\n"
        "Reglas:\n"
        '- "specialty" debe ser uno de: suadero, pastor, carnitas, cabeza, '
        'barbacoa, all. Usa "all" si no se especifica un tipo de taco.\n'
        '- "vibe" debe ser uno de: crudo, nocturno, rapido, familiar, all. '
        'Usa "all" si no se puede inferir un ambiente.\n'
        '- "search_keywords" es una lista de palabras clave relevantes '
        "extraídas del antojo.\n\n"
        f"Antojo del usuario: {user_prompt}"
    )


def invoke_bedrock_model(model_id: str, user_prompt: str) -> str:
    """Invoke a Bedrock model and return the raw text completion.

    The request body differs between Amazon Nova and Anthropic Claude models,
    so the body is built according to the target model family.
    """
    prompt_text = build_prompt(user_prompt)

    if model_id.startswith("anthropic."):
        # Anthropic Claude (Messages API) payload.
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "temperature": 0,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt_text}]}
            ],
        }
    else:
        # Amazon Nova payload.
        body = {
            "messages": [{"role": "user", "content": [{"text": prompt_text}]}],
            "inferenceConfig": {"maxTokens": 512, "temperature": 0},
        }

    response = bedrock_runtime.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )

    payload = json.loads(response["body"].read())
    return extract_model_text(model_id, payload)


def extract_model_text(model_id: str, payload: dict) -> str:
    """Extract the plain text completion from a model-specific response body."""
    if model_id.startswith("anthropic."):
        # Claude Messages API -> {"content": [{"type": "text", "text": "..."}]}
        contents = payload.get("content", [])
        return "".join(part.get("text", "") for part in contents).strip()

    # Amazon Nova -> {"output": {"message": {"content": [{"text": "..."}]}}}
    message = payload.get("output", {}).get("message", {})
    contents = message.get("content", [])
    return "".join(part.get("text", "") for part in contents).strip()


def parse_intent(raw_text: str) -> dict:
    """Parse the model's raw text into an intent dict with validated fields.

    Defensive against models that wrap JSON in ```json fences or add prose.
    """
    cleaned = raw_text.strip()

    # Strip accidental Markdown code fences if present.
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        # Remove an optional leading "json" language tag.
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    # Isolate the JSON object in case the model added surrounding text.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]

    intent = json.loads(cleaned)

    # Normalise / validate fields.
    specialty = str(intent.get("specialty", "all")).lower().strip()
    vibe = str(intent.get("vibe", "all")).lower().strip()
    keywords = intent.get("search_keywords", [])

    if specialty not in VALID_SPECIALTIES:
        specialty = "all"
    if vibe not in VALID_VIBES:
        vibe = "all"
    if not isinstance(keywords, list):
        keywords = []
    keywords = [str(k) for k in keywords]

    return {"specialty": specialty, "vibe": vibe, "search_keywords": keywords}


def detect_intent(user_prompt: str) -> dict:
    """Run Bedrock with a primary model and fall back to a secondary model."""
    try:
        raw = invoke_bedrock_model(PRIMARY_MODEL_ID, user_prompt)
        return parse_intent(raw)
    except (ClientError, json.JSONDecodeError, KeyError, ValueError) as primary_err:
        logger.warning(
            "Primary model '%s' failed (%s). Falling back to '%s'.",
            PRIMARY_MODEL_ID,
            primary_err,
            FALLBACK_MODEL_ID,
        )
        raw = invoke_bedrock_model(FALLBACK_MODEL_ID, user_prompt)
        return parse_intent(raw)


def fetch_stores() -> list:
    """Scan the DynamoDB table, paginating until all items are retrieved."""
    items = []
    scan_kwargs = {}
    while True:
        response = stores_table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    return items


def store_matches(store: dict, specialty: str, vibe: str) -> bool:
    """Return True when a store matches the detected specialty and vibe.

    A value of "all" acts as a wildcard, so stores are matched inclusively.
    """
    store_specialty = str(store.get("specialty", "")).lower().strip()
    store_vibe = str(store.get("vibe", "")).lower().strip()

    specialty_ok = specialty == "all" or store_specialty == specialty
    vibe_ok = vibe == "all" or store_vibe == vibe

    return specialty_ok and vibe_ok


def filter_stores(stores: list, specialty: str, vibe: str) -> list:
    """Filter stores by intent and project the fields the client needs."""
    results = []
    for store in stores:
        if not store_matches(store, specialty, vibe):
            continue
        results.append(
            {
                "store_id": store.get("store_id"),
                "name": store.get("name"),
                "specialty": store.get("specialty"),
                "vibe": store.get("vibe"),
                "address": store.get("address"),
                "lat": store.get("lat"),
                "lng": store.get("lng"),
            }
        )
    return results


def build_response(status_code: int, body: dict) -> dict:
    """Build an API Gateway / Lambda proxy response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def parse_event_body(event: dict) -> dict:
    """Extract the payload whether invoked directly or via API Gateway proxy."""
    if isinstance(event, dict) and "body" in event and event["body"] is not None:
        body = event["body"]
        if isinstance(body, str):
            return json.loads(body)
        return body
    return event


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------
def lambda_handler(event, context):
    """Entry point for the TacoHunter Lambda."""
    logger.info("Received event: %s", json.dumps(event, default=str))

    # Handle CORS preflight requests.
    http_method = (event or {}).get("httpMethod")
    if http_method == "OPTIONS":
        return build_response(200, {"message": "CORS preflight OK"})

    try:
        payload = parse_event_body(event)
    except (json.JSONDecodeError, TypeError) as err:
        logger.error("Invalid request body: %s", err)
        return build_response(400, {"error": "Invalid JSON in request body."})

    user_prompt = (payload or {}).get("user_prompt")
    user_lat = (payload or {}).get("user_lat")
    user_lng = (payload or {}).get("user_lng")

    if not user_prompt or not str(user_prompt).strip():
        return build_response(400, {"error": "Missing required field 'user_prompt'."})

    # 1. Detect intent with Bedrock.
    try:
        intent = detect_intent(user_prompt)
    except Exception as err:  # noqa: BLE001 - surface a clean 502 to the client
        logger.exception("Bedrock intent detection failed.")
        return build_response(
            502, {"error": "Failed to analyze craving with Bedrock.", "detail": str(err)}
        )

    logger.info("Detected intent: %s", intent)

    # 2. Retrieve and filter stores from DynamoDB.
    try:
        stores = fetch_stores()
    except ClientError as err:
        logger.exception("DynamoDB scan failed.")
        return build_response(
            502, {"error": "Failed to query store catalog.", "detail": str(err)}
        )

    matches = filter_stores(stores, intent["specialty"], intent["vibe"])

    # 3. Build the structured success response.
    response_body = {
        "intent": intent,
        "user_location": {"lat": user_lat, "lng": user_lng},
        "count": len(matches),
        "taquerias": matches,
    }

    return build_response(200, response_body)
