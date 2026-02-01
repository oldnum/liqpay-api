import base64
import hashlib
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def make_signature(private_key: str, data: str) -> str:
    # Generates a signature for LiqPay API.
    # Formula: base64_encode(sha1(private_key + data + private_key))

    to_sign = f"{private_key}{data}{private_key}"
    sha1 = hashlib.sha1(to_sign.encode("utf-8")).digest()
    sig = base64.b64encode(sha1).decode("ascii")
    return sig

def get_encoded_data(params: Dict[str, Any]) -> str:
    # Encodes parameters to base64.

    json_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
    return base64.b64encode(json_str.encode("utf-8")).decode("utf-8")

def validate_params(params: Dict[str, Any], schema: Dict[str, Any]) -> None:
    # Validates parameters based on a simple schema.
    
    for key, validator in schema.items():
        val = params.get(key)
        if not validator(val):
            logger.error("Validation failed for parameter: %s = %r", key, val)
            raise ValueError(f"Invalid parameter '{key}': {val}")
