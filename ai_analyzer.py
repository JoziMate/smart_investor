import os
import json
import logging
from google import genai
from google.genai import types

logger_inst = logging.getLogger(__name__)

def generate_market_reflections(performance_data: str) -> dict:
    """
    Analyzes current portfolio performance data using Gemini 2.5 Flash
    and returns professional market reflections in JSON format.

    Args:
        performance_data (str): Formatted string of assets and their % profit/loss.

    Returns:
        dict: A dictionary containing 'co_zadzialalo', 'co_nie_zadzialalo', and 'co_zmieniam'.
              Returns an empty dictionary on failure.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger_inst.error("GEMINI_API_KEY not found in environment variables.")
        return {}

    prompt = f"""
Jesteś profesjonalnym analitykiem portfela inwestycyjnego.
Poniżej znajdują się dane o aktualnych wynikach otwartych pozycji:
{performance_data}

Na podstawie tych danych, wygeneruj krótką, profesjonalną refleksję rynkową (1-2 zdania na sekcję).
Zwróć odpowiedź w czystym formacie JSON o następującej strukturze:
{{
  "co_zadzialalo": "Krótki opis tego, co przynosi zyski lub dobrze wygląda.",
  "co_nie_zadzialalo": "Krótki opis strat i problematycznych pozycji.",
  "co_zmieniam": "Krótkie i konkretne wnioski co do zmiany strategii lub dalszych kroków."
}}
Nie formatuj odpowiedzi w bloki kodu markdown. Zwróć tylko JSON.
"""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
            )
        )

        # Parse JSON
        result = json.loads(response.text)
        logger_inst.info("Successfully generated market reflections via AI.")
        return result

    except genai.errors.APIError as e:
        logger_inst.error(f"Google GenAI API Error during market reflection generation: {e}")
        return {}
    except json.JSONDecodeError as e:
        logger_inst.error(f"Failed to parse JSON response from AI: {e}. Raw response: {response.text}")
        return {}
    except Exception as e:
        logger_inst.error(f"An unexpected error occurred during AI analysis: {e}")
        return {}
