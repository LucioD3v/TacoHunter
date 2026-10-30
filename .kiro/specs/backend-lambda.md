# Lambda Implementation Spec: `lambda_function.py`

## Requirements
- Runtime: Python 3.12 using `boto3` for DynamoDB and Bedrock Runtime.
- Input Event Payload:
```json
{
  "user_prompt": "string",
  "user_lat": 19.4100,
  "user_lng": -99.1700
}