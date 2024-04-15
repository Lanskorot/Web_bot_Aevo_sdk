import asyncio
import json
import sys
from loguru import logger

from aevo import AevoClient

async def main():
    aevo = AevoClient(
        signing_key="", # Paste your signing key here
        wallet_address="", # Paste your wallet address here
        api_key="", # Paste your api key here
        api_secret="", # Paste your api secret here
        env="",
    )

    if not aevo.signing_key:
        raise Exception(
            "Signing key is not set. Please set the signing key in the AevoClient constructor."
        )

    logger.info("Creating order...")

    response = aevo.rest_create_order(
        instrument_id=3396,
        is_buy=True,
        limit_price=60000,
        quantity=0.01,
        post_only=False,
    )
    logger.info(response)

    await aevo.open_connection()
    await aevo.subscribe_ticker("ticker:BTC:PERPETUAL")

    async for msg in aevo.read_messages():
        msg = json.loads(msg)

        if "channel" in msg and msg['channel'] == "ticker:BTC:PERPETUAL":
            current_price = float(msg['data']['tickers'][0]['mark']['price'])

            if current_price < 65700:
                response = aevo.rest_create_market_order(
                    instrument_id=3396,
                    is_buy=False,
                    quantity=0.01,
                )
                logger.info(response)

                sys.exit("Stop bot") 

if __name__ == "__main__":
    asyncio.run(main())