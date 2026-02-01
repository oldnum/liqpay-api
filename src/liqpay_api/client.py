import logging

from copy import deepcopy
from typing import Any, Dict, Tuple, Optional
from urllib.parse import urljoin

import base64
import json


import aiohttp

from .utils import get_encoded_data, make_signature, validate_params

logger = logging.getLogger(__name__)

class LiqPayAsync:
    # Asynchronous LiqPay Python SDK.

    SUPPORTED_CURRENCIES = {"UAH", "USD", "EUR"}
    SUPPORTED_LANGUAGES = {"uk", "en"}
    SUPPORTED_ACTIONS = {"pay", "hold", "subscribe", "paydonate", "auth", "status"}
    
    FORM_TEMPLATE = """
        <form method="POST" action="{action}" accept-charset="utf-8">
            <input type="hidden" name="data" value="{data}" />
            <input type="hidden" name="signature" value="{signature}" />
            <script type="text/javascript" src="https://static.liqpay.ua/libjs/sdk_button.js"></script>
            <sdk-button label="{label}" background="#77CC5D" onClick="submit()"></sdk-button>
        </form>
    """

    BUTTON_LABELS = {"uk": "Сплатити", "en": "Pay"}

    def __init__(
        self,
        public_key: str,
        private_key: str,
        host: str = "https://www.liqpay.ua/api/",
        timeout: float = 10.0,
    ):
        # Initialize the client.
        
        self.public_key = public_key.strip()
        self.private_key = private_key.strip()
        self.host = host.rstrip("/") + "/"
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        logger.info("[LiqPayAsync][__init__]: Initialized client for public_key: %s...", self.public_key[:6])

    def _prepare_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Prepare parameters for API request.

        params = deepcopy(params)
        params.setdefault("version", 3)
        params.setdefault("public_key", self.public_key)
        
        # Auto-encode dae if it's a dict
        if "dae" in params and isinstance(params["dae"], dict):
            dae_json = json.dumps(params["dae"], ensure_ascii=False)
            params["dae"] = base64.b64encode(dae_json.encode("utf-8")).decode("utf-8")
            
        return params

    def _validate(self, params: Dict[str, Any]) -> None:
        # Basic validation for common required fields

        schema = {
            "version": lambda v: v in (3, "3"),
            "public_key": lambda v: v == self.public_key,
            "action": lambda v: v in self.SUPPORTED_ACTIONS,
        }
        
        action = params.get("action")
        
        # Checkout specific requirements
        if action in {"pay", "hold", "subscribe", "paydonate"}:
            schema.update({
                "amount": lambda v: v is not None and float(v) > 0,
                "currency": lambda v: v in self.SUPPORTED_CURRENCIES,
                "description": lambda v: isinstance(v, str) and 0 < len(v) <= 510,
                "order_id": lambda v: isinstance(v, str) and 0 < len(v) <= 255,
            })

        # Add validation for common optional fields
        schema.update({
            "expired_date": lambda v: v is None or (isinstance(v, str) and len(v) == 19),
            "language": lambda v: v is None or v in self.SUPPORTED_LANGUAGES,
            "paytypes": lambda v: v is None or isinstance(v, str),
            "server_url": lambda v: v is None or (isinstance(v, str) and len(v) <= 510),
            "result_url": lambda v: v is None or (isinstance(v, str) and len(v) <= 510),
        })

        # Recurring payment requirements
        if action == "subscribe" or params.get("subscribe") == "1":
            schema.update({
                "subscribe_date_start": lambda v: isinstance(v, str) and len(v) > 0,
            })

        validate_params(params, schema)

        # Advanced validation for objects
        if "rro_info" in params:
            rro = params["rro_info"]
            if not isinstance(rro, dict) or "items" not in rro:
                raise ValueError("Invalid rro_info: must be a dict with 'items'")
            for item in rro.get("items", []):
                for field in ["amount", "cost", "id", "price"]:
                    if field not in item:
                        raise ValueError("[LiqPayAsync][_validate]: Missing rro_info item field: {}".format(field))

        if "split_rules" in params:
            rules = params["split_rules"]
            # If rules is a string, it should be valid JSON
            if isinstance(rules, str):
                try:
                    json.loads(rules)
                except Exception as exc:
                    raise ValueError("[LiqPayAsync][_validate]: Invalid split_rules: must be a valid JSON string or list") from exc

    def _get_data_and_signature(self, params: Dict[str, Any]) -> Tuple[str, str]:
        encoded_data = get_encoded_data(params)
        signature = make_signature(self.private_key, encoded_data)
        return encoded_data, signature

    async def fetch_url(
        self,
        url: str,
        payload: Dict[str, Any],
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Dict[str, Any]:
        # Low-level helper to perform HTTP POST request.

        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession(timeout=self.timeout)

        try:
            async with session.post(url, data=payload) as resp:
                resp.raise_for_status()
                result = await resp.json()
                logger.debug("[LiqPayAsync][fetch_url]: HTTP Success | status=%s", result.get("status"))
                # Always include the final URL in the result
                result["_url"] = str(resp.url)
                return result
        except Exception as exc:
            logger.error("[LiqPayAsync][fetch_url]: HTTP Error: %s", exc)
            raise
        finally:
            if own_session:
                await session.close()

    async def request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Dict[str, Any]:
        # Call LiqPay API endpoint.

        params = self._prepare_params(params)
        self._validate(params)
        
        encoded_data, signature = self._get_data_and_signature(params)
        url = urljoin(self.host, endpoint.lstrip("/"))
        
        payload = {
            "data": encoded_data,
            "signature": signature
        }

        logger.info("[LiqPayAsync][api]: API Request → %s | action=%s", url, params.get("action"))
        return await self.fetch_url(url, payload, session)

    async def get_status(self, order_id: str, session: Optional[aiohttp.ClientSession] = None) -> Dict[str, Any]:
        # Check status of the payment.
        
        params = {"action": "status", "order_id": order_id}
        return await self.request("request", params, session)

    async def pay(self, params: Dict[str, Any], session: Optional[aiohttp.ClientSession] = None) -> Dict[str, Any]:
        # Direct API payment.
        
        params["action"] = "pay"
        return await self.request("request", params, session)

    async def hold(self, params: Dict[str, Any], session: Optional[aiohttp.ClientSession] = None) -> Dict[str, Any]:
        # Hold funds on sender account.
        
        params["action"] = "hold"
        return await self.request("request", params, session)

    async def subscribe(self, params: Dict[str, Any], session: Optional[aiohttp.ClientSession] = None) -> Dict[str, Any]:
        # Regular (recurring) payment.
        
        params["action"] = "subscribe"
        return await self.request("request", params, session)

    def generate_cnb_form(self, params: Dict[str, Any]) -> str:
        # Generate HTML form for checkout.

        params = self._prepare_params(params)
        self._validate(params)

        lang = params.get("language", "uk").lower()
        if lang not in self.SUPPORTED_LANGUAGES:
            logger.warning("[LiqPayAsync][cnb_form]: Unsupported language: %s, using default 'uk'", lang)
            lang = "uk"
        
        encoded_data, signature = self._get_data_and_signature(params)
        
        checkout_url = urljoin(self.host, "3/checkout")

        return self.FORM_TEMPLATE.format(
            action=checkout_url,
            data=encoded_data,
            signature=signature,
            label=self.BUTTON_LABELS.get(lang, "Pay")
        )

    def generate_checkout_url(self, params: Dict[str, Any]) -> str:
        # Generate direct checkout URL (GET request).

        params = self._prepare_params(params)
        self._validate(params)
        
        encoded_data, signature = self._get_data_and_signature(params)
        checkout_base = urljoin(self.host, "3/checkout")
        return f"{checkout_base}?data={encoded_data}&signature={signature}"

    async def get_payment_url(self, params: Dict[str, Any], session: Optional[aiohttp.ClientSession] = None) -> str:
        # Perform POST to checkout and return the resulting URL.

        params = self._prepare_params(params)
        self._validate(params)
        
        encoded_data, signature = self._get_data_and_signature(params)
        url = urljoin(self.host, "3/checkout")
        
        payload = {
            "data": encoded_data,
            "signature": signature
        }

        logger.info("[LiqPayAsync][get_payment_url]: Requesting payment URL via POST → %s", url)
        result = await self.fetch_url(url, payload, session)
        return result.get("_url", "")

    def validate_callback(self, data: str, signature: str) -> Dict[str, Any]:
        # Validate and decode LiqPay callback.

        expected_signature = make_signature(self.private_key, data)
        if expected_signature != signature:
            logger.error("[LiqPayAsync][validate_callback]: Invalid signature in callback")
            raise ValueError("[LiqPayAsync][validate_callback]: Invalid signature")

        decoded_json = base64.b64decode(data).decode("utf-8")
        return json.loads(decoded_json)
