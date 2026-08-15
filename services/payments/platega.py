import aiohttp
from config import PLATEGA_MERCHANT_ID, PLATEGA_API_KEY, PLATEGA_BASE_URL, BOT_USERNAME
import json

async def generate_payment_link_platega(amount: int):
    create_link_url = PLATEGA_BASE_URL + 'v2/transaction/process'

    headers = {
        'X-MerchantId': PLATEGA_MERCHANT_ID,
        'X-Secret': PLATEGA_API_KEY,
        'Content-Type': 'application/json'
    }

    payload = {
        "paymentDetails": {
            "amount": amount,
            "currency": "RUB"
        },
        "description": f"Оплата VPN подписки",
        "return": f"https://t.me/{BOT_USERNAME}",
        "failedUrl": f"https://t.me/{BOT_USERNAME}",
        "payload": "Оплата VPN подписки"}

    async with aiohttp.ClientSession() as session:
            async with session.post(
                create_link_url, json=payload, headers=headers
            ) as response:
    
                data = await response.json()
    
                return {
                    "invoice_id": data["transactionId"],
                    "url": data["url"],
                }


async def get_payment_status(invoice_id: str):
    get_status_url = PLATEGA_BASE_URL + f'transaction/{invoice_id}'

    headers = {
            'X-MerchantId': PLATEGA_MERCHANT_ID,
            'X-Secret': PLATEGA_API_KEY,
            'Content-Type': 'application/json'
        }

    async with aiohttp.ClientSession() as session:
            async with session.get(
                get_status_url, headers=headers
            ) as response:
    
                data = await response.json()

                print(data)

                return data['status']