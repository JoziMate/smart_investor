# 📈 Gra Inwestycyjna - Portfolio & Risk Manager

Automatyczne narzędzie wspierające zarządzanie wirtualnym portfelem inwestycyjnym o charakterystyce instytucjonalnej ("v2"). Projekt stworzony w ramach zajęć akademickich **"Smart Inwestor"**.

Aplikacja integruje pobieranie danych rynkowych w czasie rzeczywistym, bezpieczną manipulację arkuszami kalkulacyjnymi oraz zaawansowaną analizę obrazu (AI Vision) do automatycznego księgowania nowych transakcji w pliku `Dziennik_inwestora.xlsx`.

## ✨ Główne funkcjonalności

* **Pobieranie Danych Rynkowych (API):** Skrypt śledzi na żywo wyceny amerykańskich gigantów technologicznych (MSFT, GOOGL, TSLA), polskich spółek dywidendowych i dłużnych na GPW (.WA) oraz kryptowalut (BTC/USDT) z giełdy Binance.
* **Integracja z programem Excel:** Bezinwazyjne aktualizowanie pliku `.xlsx` (zakładka "Pozycje otwarte"). Program modyfikuje wyłącznie wybrane komórki (aktualna cena, data aktualizacji), zachowując formatowanie i inne arkusze z refleksjami.
* **Automatyzacja Księgowania AI (Vision Mode):** Wykorzystanie modelu **Gemini 2.5 Flash** do analizy zrzutów ekranu z platform brokerskich (np. Interactive Brokers, Saxo). AI samodzielnie odczytuje Ticker, Kierunek, Wolumen oraz Cenę wejścia, a następnie dopisuje nową pozycję w pierwszym wolnym wierszu Excela.
* **Architektura Dual-Mode:** Program można uruchomić poprzez nowoczesny, ciemny interfejs graficzny (GUI) lub za pomocą szybkiego interfejsu wiersza poleceń (CLI).

## 🛠️ Architektura Techniczna i Biblioteki

System został napisany w języku Python z naciskiem na modularność i rygorystyczną obsługę błędów.

* `yfinance` - Pobieranie notowań giełdowych (Wall Street & GPW).
* `ccxt` - Połączenie z publicznym API Binance.
* `openpyxl` - Bezpieczna edycja pliku Excel.
* `google-genai` & `Pillow` - Autonomiczny moduł OCR/AI do przetwarzania zrzutów ekranu w pamięci RAM.
* `customtkinter` - Renderowanie interfejsu graficznego (Dark Mode).
* `python-dotenv` - Bezpieczne zarządzanie poświadczeniami i kluczami API.

## 🚀 Instrukcja instalacji

1. **Sklonuj repozytorium:**
   ```bash
   git clone https://github.com/JoziMate/smart_investor
   cd smart_investor
   ```

2. **Wygeneruj szablon danych (Data Template):**
   ```bash
   python create_template.py
   ```
   *Ten krok tworzy pusty plik `Dziennik_inwestora_template.xlsx` z odpowiednimi nagłówkami.*
