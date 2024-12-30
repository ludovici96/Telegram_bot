import http.client
import json
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class CurrencyService:
    def __init__(self, api_key_file: str):
        try:
            with open(api_key_file, 'r') as f:
                self.api_key = f.read().strip()
            logger.debug(f"Initialized CurrencyService with API key from {api_key_file}")
        except Exception as e:
            logger.error(f"Failed to read API key from {api_key_file}: {e}")
            self.api_key = None

    async def get_latest_rates(self, base='USD', currencies=['EUR', 'GBP', 'JPY']):
        try:
            conn = http.client.HTTPSConnection("api.fxratesapi.com")
            currencies_str = ','.join(currencies)
            
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            endpoint = f"/latest?api_key={self.api_key}&base={base}&currencies={currencies_str}"
            logger.debug(f"Making request to: {endpoint}")
            
            conn.request("GET", endpoint, headers=headers)
            res = conn.getresponse()
            data = res.read().decode("utf-8")
            
            logger.debug(f"API Response: {data}")
            
            if res.status != 200:
                raise Exception(f"API Error: {res.status} - {data}")
                
            response_data = json.loads(data)
            if 'error' in response_data:
                raise Exception(f"API Error: {response_data['error']}")
                
            return response_data
            
        except Exception as e:
            logger.error(f"Error in get_latest_rates: {str(e)}")
            raise
        finally:
            conn.close()

    async def convert_currency(self, from_currency: str, to_currency: str, amount: float) -> dict:
        try:
            conn = http.client.HTTPSConnection("api.fxratesapi.com")
            
            endpoint = f"/convert?from={from_currency}&to={to_currency}&amount={amount}&format=json"
            logger.debug(f"Making conversion request to: {endpoint}")
            
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            conn.request("GET", endpoint, headers=headers)
            res = conn.getresponse()
            data = res.read().decode("utf-8")
            
            logger.debug(f"API Response: {data}")
            
            if res.status != 200:
                raise Exception(f"API Error: {res.status} - {data}")
                
            response_data = json.loads(data)
            if 'error' in response_data:
                raise Exception(f"API Error: {response_data['error']}")
                
            # Extract rate from response
            rate = float(response_data.get('rate', 0))
            result = float(response_data.get('result', 0))
            
            return {
                'rate': rate,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error in convert_currency: {str(e)}")
            raise
        finally:
            conn.close()