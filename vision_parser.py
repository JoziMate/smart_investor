import os
import json
import logging
from google import genai
from google.genai import errors
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')

def extract_trades_from_image(image_path: str) -> list[dict]:
    """
    Extracts trade data from a screenshot of a brokerage platform using Gemini Vision API.

    Args:
        image_path (str): The path to the screenshot image.

    Returns:
        list[dict]: A list of dictionaries containing trade data:
            [{'Platform': '...', 'Ticker': '...', 'OrderType': '...', 'Direction': 'Long'|'Short', 'Volume': ..., 'Price': ..., 'Justification': '...'}, ...]
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY is not set in the environment or .env file.")
        return []

    # The new SDK automatically picks up GEMINI_API_KEY from environment,
    # or you can pass it explicitly. We rely on the env var after load_dotenv().
    client = genai.Client()

    try:
        # Load the image locally
        logging.info(f"Loading image locally: {image_path}")
        try:
            image = Image.open(image_path)
        except Exception as e:
            logging.error(f"Failed to load image {image_path}: {e}")
            return []

        # Craft the prompt
        prompt = (
            "Analyze this screenshot of a brokerage platform and extract the details of all newly opened positions. "
            "The UI elements might be in Polish (e.g., 'Wolumen' for Volume, 'Instrument' for Ticker, "
            "'Kupno' for Long, 'Sprzedaż' for Short). "
            "Return ONLY a raw JSON array of dictionaries, without any markdown formatting or ```json backticks. "
            "The output JSON keys must strictly be in English: 'Platform', 'Ticker', 'OrderType', 'Direction', 'Volume', 'Price', 'Justification'. "
            "The 'Platform' value should be inferred from the screenshot UI (e.g., 'Interactive Brokers', 'Binance', 'Saxo', or 'GPW Trader'). "
            "The 'OrderType' value should be inferred (e.g., 'Market', 'Limit') or default to 'Market'. "
            "The 'Direction' value must strictly be mapped to either 'Long' or 'Short'. "
            "The 'Volume' and 'Price' values must strictly be formatted as numerical values (floats/integers) rather than strings. "
            "The 'Justification' value should be a very brief, 1-sentence technical justification generated based on the extracted data (e.g., 'Zajęcie pozycji zgodnie ze strategią v2')."
        )

        logging.info("Sending request to Gemini API...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[image, prompt]
        )

        # Parse the JSON response
        response_text = response.text.strip()

        # Sometimes the model might still include backticks despite instructions, clean it up just in case
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        response_text = response_text.strip()

        try:
            trades = json.loads(response_text)
            if not isinstance(trades, list):
                logging.error(f"Expected a JSON array, got: {type(trades)}")
                return []
            return trades
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON response: {e}")
            logging.debug(f"Raw response was: {response_text}")
            return []

    except errors.APIError as e:
        logging.error(f"API Error during vision parsing: {e}")
        return []
    except Exception as e:
        logging.error(f"Error during vision parsing: {e}")
        return []
