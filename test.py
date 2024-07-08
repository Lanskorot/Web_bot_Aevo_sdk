import asyncio
import sys
import traceback

from loguru import logger
from aevo import AevoClient
from web3 import Web3
from flask import Flask, request, jsonify
import keys  # Импортируем файл конфигурации
import requests

# Настройка логирования
logger.add("app.log", rotation="10 MB", level="DEBUG")

# Генерация ключа (можно удалить, если он не нужен)
signing_key = Web3.solidity_keccak(['string'], ['my random string']).hex()

# Создание клиента Aevo с использованием значений из config.py
aevo = AevoClient(
    signing_key=keys.signing_key,
    wallet_address=keys.wallet_address,
    api_key=keys.api_key,
    api_secret=keys.api_secret,
    env="mainnet",
)

# Проверка наличия ключа подписи
if not aevo.signing_key:
    logger.error("Signing key is not set. Please set the signing key in the AevoClient constructor.")
    sys.exit("Signing key is not set")


async def buy_market(instrument_id, quantity):
    try:
        logger.info("Creating market buy order...")
        response = aevo.rest_create_market_order(
            instrument_id=instrument_id,
            is_buy=True,
            # quantity=quantity,!!!!!!!!!
            quantity=0.01,

        )
        logger.info("Market buy order request sent successfully")
        logger.info("Response: {}".format(response))
        return {"message": "Buy order executed successfully"}
    except Exception as e:
        logger.exception("An error occurred while creating market buy order: {}", e)
        return {"message": f"Error: {e}"}


async def sell_market(instrument_id, quantity):
    try:
        logger.info("Creating market sell order...")
        response = aevo.rest_create_market_order(
            instrument_id=instrument_id,
            is_buy=False,
            # quantity=quantity,!!!!!!!!!
            quantity=0.01,
        )
        logger.info("Market sell order request sent successfully")
        logger.info("Response: {}".format(response))
        return {"message": "Sell order executed successfully"}
    except Exception as e:
        logger.exception("An error occurred while creating market sell order: {}", e)
        return {"message": f"Error: {e}"}


async def close_positions():
    try:
        logger.info("Fetching open positions...")

        url = "https://api.aevo.xyz/positions"
        headers = {
            "accept": "application/json",
            "AEVO-KEY": keys.api_key,
            "AEVO-SECRET": keys.api_secret
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            positions = response.json().get("positions", [])
            if not positions:
                logger.info("No open positions found.")
                return {"status": "success", "message": "No open positions found."}

            logger.info(f"Found {len(positions)} open positions.")

            for position in positions:
                logger.info(f"Open position: {position}")

                instrument_id = position.get("instrument_id")
                is_buy = position.get("side") == "buy"

                # Создать рыночный ордер для закрытия позиции
                try:
                    result = aevo.rest_create_market_order(
                        instrument_id=instrument_id,
                        is_buy=not is_buy,  # Противоположная сторона для закрытия позиции
                        quantity=keys.quantity,
                    )
                    logger.info(f"Closed position: {position}")
                    logger.info(f"Result: {result}")
                except Exception as e:
                    logger.error(f"Failed to close position: {position}")
                    logger.error(f"Error: {e}")

            return {"status": "success", "message": "Closed all open positions successfully."}
        else:
            logger.error(f"Failed to fetch positions. Status code: {response.status_code}")
            return {"status": "error", "message": f"Failed to fetch positions. Status code: {response.status_code}"}

    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        logger.error(traceback.format_exc())
        return {"status": "error", "message": f"Failed to fetch positions: {str(e)}"}


async def buy_limit(instrument_id, quantity, limit_price):
    try:
        logger.info("Creating limit buy order...")
        response = aevo.rest_create_order(
            instrument_id=instrument_id,
            is_buy=True,
            limit_price=limit_price,
            quantity=quantity,
            post_only=False,
        )
        logger.info("Limit buy order request sent successfully")
        logger.info("Response: {}".format(response))
        return {"message": "Limit buy order executed successfully"}
    except Exception as e:
        logger.exception("An error occurred while creating limit buy order: {}", e)
        return {"message": f"Error: {e}"}


async def sell_limit(instrument_id, quantity, limit_price):
    try:
        logger.info("Creating limit sell order...")
        response = aevo.rest_create_order(
            instrument_id=instrument_id,
            is_buy=False,
            limit_price=limit_price,
            quantity=quantity,
            post_only=False,
        )
        logger.info("Limit sell order request sent successfully")
        logger.info("Response: {}".format(response))
        return {"message": "Limit sell order executed successfully"}
    except Exception as e:
        logger.exception("An error occurred while creating limit sell order: {}", e)
        return {"message": f"Error: {e}"}


app = Flask(__name__)


@app.route('/long', methods=['POST'])
def buy():
    data = request.json
    quan = data.get('quantity')
    print(quan)
    print(type(quan))
    print(keys.quantity)
    print(type(keys.quantity))
    result = asyncio.run(buy_market(keys.instrument_id, quan))
    return jsonify(result)


@app.route('/short', methods=['POST'])
def sell():
    data = request.json
    quan = data.get('quantity')
    print(quan)
    print(type(quan))
    print(keys.quantity)
    print(type(keys.quantity))
    result = asyncio.run(sell_market(keys.instrument_id, quan))
    return jsonify(result)


@app.route('/sell_all', methods=['POST'])
def close():
    result = asyncio.run(close_positions())
    return jsonify(result)


@app.route('/long_limit', methods=['POST'])
def buy_limit_route():
    data = request.json
    instrument_id = data.get("instrument_id", keys.instrument_id)
    quantity = data.get("quantity", keys.quantity)
    limit_price = data.get("limit_price")
    if limit_price is None:
        return jsonify({"error": "Limit price is required"}), 400
    result = asyncio.run(buy_limit(instrument_id, quantity, limit_price))
    return jsonify(result)


@app.route('/short_limit', methods=['POST'])
def sell_limit_route():
    data = request.json
    instrument_id = data.get("instrument_id", keys.instrument_id)
    quantity = data.get("quantity", keys.quantity)
    limit_price = data.get("limit_price")
    if limit_price is None:
        return jsonify({"error": "Limit price is required"}), 400
    result = asyncio.run(sell_limit(instrument_id, quantity, limit_price))
    return jsonify(result)


@app.route('/money_account', methods=['GET'])
def money_account():
    url = "https://api.aevo.xyz/portfolio"

    headers = {
        "accept": "application/json",
        "AEVO-KEY": keys.api_key,
        "AEVO-SECRET": keys.api_secret
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        balance = data.get("balance")
        if balance:
            return jsonify({"balance": balance})
        else:
            return jsonify({"error": "Balance not found in response"}), 500
    else:
        return jsonify({"error": f"Request failed with status code: {response.status_code}"}), 500


@app.route('/positions', methods=['GET'])
def get_positions():
    url = "https://api.aevo.xyz/positions"

    headers = {
        "accept": "application/json",
        "AEVO-KEY": keys.api_key,
        "AEVO-SECRET": keys.api_secret
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        positions = data.get("positions", [])
        with app.app_context():
            return jsonify({"positions": positions})
    else:
        return jsonify({"error": f"Request failed with status code: {response.status_code}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)

