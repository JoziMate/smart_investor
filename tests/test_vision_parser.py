import pytest
import json
from vision_parser import extract_trades_from_image

def test_extract_trades_from_image_success(mocker, tmp_path):
    # Mock environment variable and client
    mocker.patch('os.getenv', return_value='dummy_key')

    mock_client = mocker.Mock()
    mock_response = mocker.Mock()

    # Dummy trades JSON
    dummy_trades = [
        {
            "Platform": "Binance",
            "Ticker": "BTC/USDT",
            "OrderType": "Limit",
            "Direction": "Long",
            "Volume": 0.5,
            "Price": 60000,
            "Justification": "Support level bounce."
        }
    ]

    # Gemini sometimes returns backticks, we simulate a raw json return
    mock_response.text = json.dumps(dummy_trades)
    mock_client.models.generate_content.return_value = mock_response

    mocker.patch('vision_parser.get_client', return_value=mock_client)

    # Create a dummy image file
    image_file = tmp_path / "dummy.png"
    import PIL.Image
    img = PIL.Image.new('RGB', (10, 10))
    img.save(image_file)

    trades = extract_trades_from_image(str(image_file))

    assert isinstance(trades, list)
    assert len(trades) == 1
    assert trades[0]['Ticker'] == "BTC/USDT"

def test_extract_trades_from_image_invalid_json(mocker, tmp_path):
    mocker.patch('os.getenv', return_value='dummy_key')

    mock_client = mocker.Mock()
    mock_response = mocker.Mock()

    # Simulate bad json response
    mock_response.text = "This is not json"
    mock_client.models.generate_content.return_value = mock_response

    mocker.patch('vision_parser.get_client', return_value=mock_client)

    image_file = tmp_path / "dummy.png"
    import PIL.Image
    img = PIL.Image.new('RGB', (10, 10))
    img.save(image_file)

    trades = extract_trades_from_image(str(image_file))

    assert trades == []
