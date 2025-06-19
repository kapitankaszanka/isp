# hazard-rpz • Aktualizator strefy BIND dla Rejestru Stron Hazardowych  
*(English version below)*

> **Cel**  
> Skrypt **`hazard_rpz_update.py`** pobiera dzienny rejestr stron hazardowych z API Ministerstwa Finansów, buduje strefę **RPZ** (`hazard-rpz`) i przekierowuje **każdą** domenę na adres *145.237.235.240*.  
> Dodatkowy skrypt **`hazard_async_tester.py`** sprawdza asynchronicznie, czy przekierowanie działa dla wszystkich wpisów.

---

## Spis treści
1. [Wymagania](#wymagania)  
2. [Instalacja](#instalacja)  
3. [Konfiguracja BIND-a](#konfiguracja-bind-a)  
4. [Uruchamianie](#uruchamianie)  
5. [Tester](#tester)  
6. [Typowe problemy](#typowe-problemy)  
7. [Licencja](#licencja)  

---

### Wymagania
| komponent | wersja minimalna |
|-----------|-----------------|
| Python    | **3.10** |
| BIND      | **9.18** (z obsługą RPZ) |
| PIP-pakiety| `requests xmltodict idna aiohttp dnspython` |

```bash
python3 -m pip install -r requirements.txt
