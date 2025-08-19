# Tester DNS dla ustawy hazardowej

`hazard_tester.py` pobiera plik XML z opublikowanej przez Ministerstwo Finansów listy domen hazardowych, a następnie **sprawdza odpowiedzi DNS** dla każdej domeny.  
Skrypt weryfikuje, czy każda domena wskazuje na oficjalny adres sinkhole **145.237.235.240**.  

Na końcu wypisuje podsumowanie: liczba poprawnych odpowiedzi, liczba błędów, średni czas odpowiedzi oraz całkowity czas działania.  
Wyniki mogą być wyświetlane w formacie tekstowym (domyślnie) lub JSON.

---

## Szybki start

### 1. Pobranie skryptu i instalacja zależności

```bash
git clone https://github.com/kapitankaszanka/isp.git
cd isp/hazard-gov
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Uruchamianie skryptu

Sprawdzenie przy użyciu lokalnego serwera DNS (127.0.0.1):

```bash
python3 hazard_tester.py
```

Określenie innego serwera DNS:

```bash
python3 hazard_tester.py -d 8.8.8.8
```

Wskazanie wielu serwerów DNS (używane kolejno):

```bash
python3 hazard_tester.py -d 8.8.8.8 1.1.1.1
```

Zwiększenie liczby równoległych zapytań (domyślnie: 64):

```bash
python3 hazard_tester.py -c 256
```

Format JSON:

```bash
python3 hazard_tester.py -f json
```

### 3. Przykładowy wynik

**Tekst**
```
DNS=8.8.8.8  OK=15200  BAD=3  TIME: AVG_RES=25.3ms TOTAL=8.1s
Errors: bad-domain1.com bad-domain2.net ...
```

**JSON**
```json
{
  "DNS": ["8.8.8.8", "1.1.1.1"],
  "OK": 15200,
  "BAD": 3,
  "TIME": {"AVG_RES": 25.3, "TOTAL": 8.1},
  "ERRORS": ["bad-domain1.com", "bad-domain2.net"]
}
```

---

## Opcje CLI

| Opcja | Opis | Domyślnie |
|-------|------|-----------|
| `-d`, `--dns-server` | Jeden lub więcej serwerów DNS do zapytań | `127.0.0.1` |
| `-c`, `--conn_number` | Liczba równoległych zapytań DNS | `64` |
| `-f`, `--format` | Format wyjściowy: `text` lub `json` | `text` |