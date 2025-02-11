import aiohttp
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class CryptoPriceService:
    def __init__(self, api_key_file: str):
        try:
            with open(api_key_file, 'r') as f:
                self.api_key = f.read().strip()
            logger.debug(f"Initialized CryptoPriceService with API key from {api_key_file}")
        except Exception as e:
            logger.error(f"Failed to read API key from {api_key_file}: {e}")
            self.api_key = None
        self.base_url = 'https://pro-api.coinmarketcap.com/v1'

    async def get_price(self, ticker: str) -> Dict:
        """Get latest price for a cryptocurrency"""
        try:
            if not self.api_key:
                logger.error("No API key available")
                return {
                    'status': 'error',
                    'message': 'API key not configured'
                }

            if not ticker:
                return {
                    'status': 'error',
                    'message': 'No ticker symbol provided'
                }

            url = f'{self.base_url}/cryptocurrency/quotes/latest'
            headers = {
                'X-CMC_PRO_API_KEY': self.api_key,
                'Accept': 'application/json'
            }
            params = {
                'symbol': ticker.upper(),
                'convert': 'USD'
            }

            logger.debug(f"Making request to CoinMarketCap API for ticker: {ticker}")
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request params: {params}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    logger.debug(f"Response status: {response.status}")
                    data = await response.json()
                    logger.debug(f"Raw API response: {data}")
                    
                    # Check for API error response
                    if 'status' in data and data['status'].get('error_code', 0) != 0:
                        error_msg = data['status'].get('error_message', f'No data found for {ticker}')
                        logger.error(f"API error: {error_msg}")
                        return {
                            'status': 'error',
                            'message': error_msg
                        }

                    # Get the first coin data (API returns object with numeric keys)
                    if not data.get('data'):
                        logger.error(f"No data field in response for ticker {ticker}")
                        return {
                            'status': 'error',
                            'message': f'No data found for {ticker}'
                        }

                    ticker_data = data['data'].get(ticker.upper())
                    if not ticker_data:
                        logger.error(f"No ticker data found for {ticker}")
                        return {
                            'status': 'error',
                            'message': f'No data found for {ticker}'
                        }

                    quote = ticker_data.get('quote', {}).get('USD', {})
                    if not quote:
                        logger.error(f"No USD quote data found for {ticker}")
                        return {
                            'status': 'error',
                            'message': f'No USD price data available for {ticker}'
                        }

                    result = {
                        'status': 'success',
                        'data': {
                            'name': ticker_data.get('name', ''),
                            'symbol': ticker_data.get('symbol', ticker.upper()),
                            'price': quote.get('price', 0.0),
                            'percent_change_24h': quote.get('percent_change_24h', 0.0),
                            'market_cap': quote.get('market_cap', 0.0),
                            'volume_24h': quote.get('volume_24h', 0.0)
                        }
                    }
                    logger.debug(f"Processed result: {result}")
                    return result

        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching crypto price: {e}")
            return {
                'status': 'error',
                'message': 'Network error while fetching price data'
            }
        except Exception as e:
            logger.error(f"Error fetching crypto price: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': 'Unexpected error while fetching price data'
            }
