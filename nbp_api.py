import requests
import logging

logger_inst = logging.getLogger(__name__)

def fetch_usd_pln_rate() -> float:
    """
    Fetches the current mid exchange rate for USD/PLN from the NBP API.
    Returns 4.00 as a fallback if the API call fails.
    """
    url = "http://api.nbp.pl/api/exchangerates/rates/A/USD/?format=json"
    fallback_rate = 4.00

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        rate = data['rates'][0]['mid']
        logger_inst.info(f"Successfully fetched USD/PLN rate from NBP: {rate}")
        return float(rate)
    except Exception as e:
        logger_inst.warning(f"Failed to fetch USD/PLN rate from NBP API: {e}. Using fallback rate: {fallback_rate}")
        return fallback_rate
