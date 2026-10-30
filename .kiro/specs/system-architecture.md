# TacoHunter - System Architecture Spec

## Core Goal
Provide a context-aware taquería recommendation engine based on user natural language queries and geographical coordinates.

## Workflow
1. User enters natural language request (e.g., "Tengo mucha hambre, quiero suadero grasosito y abierto ahorita").
2. API Gateway forwards request to `TacoHunter-Core-Engine` Lambda.
3. Lambda queries Amazon Bedrock (Nova Micro / Claude) to extract search intent parameters (category, vibe, urgency, open_now).
4. Lambda queries DynamoDB to fetch nearby taquerías and filters them based on extracted intent parameters.
5. Bedrock synthesizes a personalized recommendation text ("Te recomiendo X porque...").
6. Lambda returns structured JSON containing recommended spots + map markers payload.