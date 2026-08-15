import aiohttp
from config import CRYPTOBOT_API_TOKEN, CRYPTOBOT_BASE_URL


async def generate_payment_link(
    amount: int | float,
    tg_id: int,
    description: str = "VPN subscription",
):
    '''
    return {
                "invoice_id": invoice["invoice_id"],
                "url": invoice["bot_invoice_url"],
            }
    '''


    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_API_TOKEN,
    }

    payload = {
        "currency_type": "fiat",
        "fiat": "RUB",
        "amount": amount,

        "accepted_assets": "TON,USDT",

        "description": description,

        "payload": str(tg_id),

        "expires_in": 1200,
    }

    url = CRYPTOBOT_BASE_URL + 'createInvoice'

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url=url,
            headers=headers,
            json=payload
        ) as response:

            data = await response.json()

            if not data["ok"]:
                raise Exception(data)

            invoice = data["result"]

            return {
                "invoice_id": invoice["invoice_id"],
                "url": invoice["bot_invoice_url"],
            }



async def get_payment_status_cryptobot(invoice_id: str):
    url = CRYPTOBOT_BASE_URL + f'getInvoices?invoice_ids={invoice_id}'
    headers = {'Crypto-Pay-API-Token': CRYPTOBOT_API_TOKEN}

    async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers) as response:
                result = await response.json()
                print(result)
                invoice = result['result']['items'][0]
                return(invoice['status'] == 'paid')
