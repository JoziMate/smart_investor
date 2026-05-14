import os
import json
import logging
import google.generativeai as genai
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
            [{'Ticker': '...', 'Direction': 'Long'|'Short', 'Volume': ..., 'EntryPrice': ...}, ...]
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY is not set in the environment or .env file.")
        return []

    genai.configure(api_key=api_key)

    try:
        # Load the model
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Upload the file
        logging.info(f"Uploading image: {image_path}")
        sample_file = genai.upload_file(path=image_path)

        # Craft the prompt
        prompt = (
            "Analyze this screenshot of a brokerage platform and extract the details of all newly opened positions. "
            "The UI elements might be in Polish (e.g., 'Wolumen' for Volume, 'Instrument' for Ticker, "
            "'Kupno' for Long, 'Sprzedaż' for Short). "
            "Return ONLY a raw JSON array of dictionaries, without any markdown formatting or ```json backticks. "
            "The output JSON keys must strictly be in English: 'Ticker', 'Direction', 'Volume', 'EntryPrice'. "
            "The 'Direction' value must strictly be mapped to either 'Long' or 'Short'. "
            "Volume and EntryPrice should be numeric if possible."
        )

        logging.info("Sending request to Gemini API...")
        response = model.generate_content([sample_file, prompt])

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

    except Exception as e:
        logging.error(f"Error during vision parsing: {e}")
        return []
