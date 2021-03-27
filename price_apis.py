import json
import logging
import os
import requests
import sys


# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


API_CLASS_MAP = {'coinmarketcap': 'CoinMarketCap',
                 'coingecko': 'CoinGecko', 'alphavantage': 'AlphaVantage'}


def get_api_cls(api_name):
    """

    Args:
        api_name (str): The name of the API to use.
    """
    if api_name not in API_CLASS_MAP:
        raise RuntimeError(f'"{api_name}" api is not implemented.')
    return getattr(sys.modules[__name__], API_CLASS_MAP[api_name])


class PriceAPI:
    """The base class for Price API"""

    def __init__(self, symbols, currency, stocks):
        self.symbols = symbols
        self.stocks = stocks
        self.currency = currency

        self.validate_currency(currency)

    def fetch_price_data(self):
        """Fetch new price data from the API.

        Returns:
            A list of dicts that represent price data for a single asset. For example:

            [{'symbol': .., 'price': .., 'change_24h': ..}]
        """
        raise NotImplementedError

    @property
    def supported_currencies(self):
        raise NotImplementedError

    def validate_currency(self, currency):
        if currency not in self.supported_currencies:
            raise ValueError(
                f"CURRENCY={currency} is not supported. Options are: {self.supported_currencies}."
            )


class CoinMarketCap(PriceAPI):
    API = 'https://pro-api.coinmarketcap.com'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Confirm an API key is present
        try:
            self.api_key = os.environ['CMC_API_KEY']
        except KeyError:
            raise RuntimeError('CMC_API_KEY environment variable must be set.')

    @property
    def supported_currencies(self):
        return ["usd"]

    def fetch_price_data(self):
        """Fetch new price data from the CoinMarketCap API"""
        logger.info('`fetch_price_data` called.')

        response = requests.get(
            f'{self.API}/v1/cryptocurrency/quotes/latest',
            params={'symbol': self.symbols},
            headers={'X-CMC_PRO_API_KEY': self.api_key},
        )
        price_data = []

        try:
            items = response.json().get('data', {}).items()
        except json.JSONDecodeError:
            logger.error(f'JSON decode error: {response.text}')
            return

        for symbol, data in items:
            try:
                price = f"${data['quote']['USD']['price']:,.2f}"
                change_24h = f"{data['quote']['USD']['percent_change_24h']:.1f}%"
            except KeyError:
                # TODO: Add error logging
                continue
            price_data.append(
                dict(symbol=symbol, price=price, change_24h=change_24h))

        return price_data


class CoinGecko(PriceAPI):
    CG_API = 'https://api.coingecko.com/api/v3'
    FH_API = 'https://finnhub.io/api/v1/'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fetch the coin list and cache data for our symbols
        # response = requests.get(f'{self.CG_API}/coins/list')

        # The CoinGecko API uses ids to fetch price data
        symbol_map = {'bitcoin': 'BTC', 'ethereum': 'ETH'}

        self.symbol_map = symbol_map

        # Confirm an API key is present
        try:
            self.api_key = os.environ['FINNHUB_API_KEY']
        except KeyError:
            raise RuntimeError(
                'FINNHUB_API_KEY environment variable must be set.')

    @property
    def supported_currencies(self):
        return ["usd"]

    def fetch_price_data(self):
        """Fetch new price data from the CoinGecko and FinnHub API"""
        logger.info('`fetch_price_data` called.')
        logger.info(f'Fetching data for {self.symbol_map} and {self.stocks}.')

        # Make the API request
        CG_response = requests.get(
            f'{self.CG_API}/simple/price',
            params={
                'ids': ','.join(list(self.symbol_map.keys())),
                'vs_currencies': self.currency,
                'include_24hr_change': 'true',
            },
        ).json()

        price_data = []

        for coin_id, data in CG_response.items():
            try:
                price = f"${data['usd']:,.2f}"
                change_24h = f"{data['usd_24h_change']:.1f}%"
            except KeyError:
                continue

            price_data.append(
                dict(symbol=self.symbol_map[coin_id],
                     price=price, change_24h=change_24h)
            )

        for stock in self.stocks.split(','):
            response = requests.get(
                f'{self.FH_API}/quote',
                params={'symbol': stock,
                        'token': self.api_key},
            ).json()

            try:
                price_recent = response['c']
                price_open = response['o']
                change_24h = f"{100*((price_recent/price_open)-1):.1f}%"
                price_data.append(
                    dict(symbol=stock,
                         price=f"${price_recent:,.2f}",
                         change_24h=change_24h))
            except KeyError:
                # TODO: Add error logging
                continue

        logger.info(price_data)

        return price_data


class FinnHub(PriceAPI):
    API = 'https://finnhub.io/api/v1/'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Confirm an API key is present
        try:
            self.api_key = os.environ['FINNHUB_API_KEY']
        except KeyError:
            raise RuntimeError(
                'FINNHUB_API_KEY environment variable must be set.')
    
    @property
    def supported_currencies(self):
        return ["usd"]

    def fetch_price_data(self):
        """Fetch new price data from the FinnHub API"""
        logger.info('`fetch_price_data` called.')

        price_data = []

        for stock in self.stocks.split(','):
            response = requests.get(
                f'{self.API}/quote',
                params={'symbol': stock,
                        'token': self.api_key},
            ).json()

            try:
                price_recent = response['c']
                price_open = response['o']
                change_24h = f"{100*((price_recent/price_open)-1):.1f}%"
                price_data.append(
                    dict(symbol=stock,
                         price=f"${price_recent:,.2f}",
                         change_24h=change_24h))
            except KeyError:
                # TODO: Add error logging
                continue

        return price_data


class AlphaVantage(PriceAPI):
    API = 'https://www.alphavantage.co'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Confirm an API key is present
        try:
            self.api_key = os.environ['ALPHA_VANTAGE_API_KEY']
        except KeyError:
            raise RuntimeError(
                'ALPHA_VANTAGE_API_KEY environment variable must be set.')

    @property
    def supported_currencies(self):
        return ["usd"]

    def fetch_price_data(self):
        """Fetch new price data from the Alpha Vantage API"""
        logger.info('`fetch_price_data` called.')

        price_data = []

        for stock in self.stocks.split(','):
            response = requests.get(
                f'{self.API}/query?function=TIME_SERIES_INTRADAY',
                params={'symbol': stock,
                        'interval': '30min',
                        'outputsize': 'full',
                        'apikey': self.api_key},
            ).json()

            try:
                last_refreshed = response['Meta Data']['3. Last Refreshed']
                price_recent = response['Time Series (30min)'][last_refreshed]['1. open']
                price_open = response['Time Series (30min)'].get(
                    f"{last_refreshed[:10]} 09:30:00", {}).get('1. open', price_recent)
                change_24h = f"{100*((float(price_recent)/float(price_open))-1):.1f}%"
                price_data.append(
                    dict(symbol=stock,
                         price=f"${float(price_recent):,.2f}",
                         change_24h=change_24h))
            except KeyError:
                # TODO: Add error logging
                continue

        for symbol in self.symbols.split(','):
            response_current = requests.get(
                f'{self.API}/query?function=CURRENCY_EXCHANGE_RATE',
                params={'from_currency': symbol,
                        'to_currency': 'USD',
                        'apikey': self.api_key},
            ).json()

            response_daily = requests.get(
                f'{self.API}/query?function=DIGITAL_CURRENCY_DAILY',
                params={'symbol': symbol,
                        'market': 'USD',
                        'apikey': self.api_key},
            ).json()

            try:
                last_refreshed = response_daily['Meta Data']['6. Last Refreshed'][:10]
                price_recent = response_current['Realtime Currency Exchange Rate']['5. Exchange Rate']
                price_open = response_daily['Time Series (Digital Currency Daily)'][
                    last_refreshed]['1a. open (USD)']
                change_24h = f"{100*((float(price_recent)/float(price_open))-1):.1f}%"
                price_data.append(
                    dict(symbol=symbol,
                         price=f"${float(price_recent):,.2f}",
                         change_24h=change_24h))
            except KeyError:
                # TODO: Add error logging
                continue

        return price_data
