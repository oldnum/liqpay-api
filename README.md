##  About 📌
💸 LiqPayApi is a Python SDK for integrating with the LiqPay payment system.
It provides functionality to generate payment forms or links, handle callbacks, and check order status, making it easy to integrate LiqPay payments into your applications.

# Documentation 💡
- Official LiqPay API Documentation: [https://www.liqpay.ua/doc/api](https://www.liqpay.ua/doc/api)

# Requirements ⚙️
- Python 3.10+
- `aiohttp`

# Installation ☁️
```bash
pip install liqpay-api
```

# Basic Example ⚡
```python
import asyncio
from liqpay_api.client import LiqPayAsync

async def main():
    # Initialize the client
    liqpay = LiqPayAsync("your_public_key", "your_private_key")
    
    params = {
        "action": "pay",
        "amount": 100,
        "currency": "UAH",
        "description": "Payment for order #123",
        "order_id": "ORDER-123",
        "result_url": "https://your-site.com/success",
        "server_url": "https://your-site.com/liqpay-callback"
    }
    
    # 1. Generate direct checkout URL
    checkout_url = liqpay.generate_checkout_url(params)
    print(f"Checkout URL: {checkout_url}")

    # 2. Get payment URL
    payment_url = await liqpay.get_payment_url(params)
    print(f"Payment URL: {payment_url}")
    
    # 3. Check payment status
    status = await liqpay.get_status("ORDER-123")
    print(f"Payment status: {status.get('status')}")

if __name__ == "__main__":
    asyncio.run(main())
```

# Callback Handling 🔗
```python
# Example of handling LiqPay callback (server-to-server)
data = "encoded_data_from_liqpay"
signature = "signature_from_liqpay"

try:
    decoded_params = liqpay.validate_callback(data, signature)
    if decoded_params.get("status") == "success":
        print(f"Order {decoded_params.get('order_id')} paid successfully!")
except ValueError:
    print("Invalid signature!")
```

# Basic methods 🛠️
- `generate_checkout_url(params)`: Generates a direct payment link (GET request).
- `get_payment_url(params)`: Asynchronously performs a POST request and returns the resulting payment URL.
- `generate_cnb_form(params)`: Returns an HTML form with `data` and `signature` for manual redirection.
- `get_status(order_id)`: Asynchronously checks the status of a specific order.
- `pay(params)`: Convenience method for direct API payments (`action="pay"`).
- `hold(params)`: Convenience method for fund blocking (`action="hold"`).
- `subscribe(params)`: Convenience method for creating recurring payments.
- `validate_callback(data, signature)`: Decodes and verifies the signature of the incoming LiqPay server-to-server callback.
- `request(endpoint, params)`: Low-level method for any direct LiqPay API request.

#  Disclaimer 🔰
> The information presented here is intended solely for educational and research purposes. It helps to better understand how systems work and how to apply secure practices in software development. 🔒
>
> The author does not endorse or encourage the use of this information for illegal purposes 🚨
>
> Use this knowledge responsibly and follow best practices in software development. 👀

#  Donation 💰
* 📒 BTC: `bc1qqxzd80fgzqyy4wjfqsweplfmw3av7hxp07eevx`
* 📘 ETH: `0x20be839c0b9d888e5DD153Cc55A4b93bb8496c48`
* 📗 USDT (TRC20): `TY6SjeCBE4TRedVCbqk3XLqk5F4UMSGYqw`