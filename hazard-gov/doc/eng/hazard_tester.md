# DNS tester for the Polish gambling blacklist

`hazard_tester.py` downloads the XML blacklist published by Poland’s Ministry of Finance (“Rejestr Stron Hazardowych”), parses it and then **tests DNS responses** for every domain in the list.  
The script checks whether each domain resolves to the official sinkhole address **145.237.235.240**.  

It prints a summary: number of correct answers, number of errors, average response time, and total execution time.  
Output can be formatted as plain text (default) or JSON.

---

## Quick start

### 1. Download the script, install Python requirements

```bash
git clone https://github.com/kapitankaszanka/isp.git
cd isp/hazard-gov
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the script

Check all domains using local DNS (127.0.0.1):

```bash
python3 hazard_tester.py
```

Specify a different DNS server:

```bash
python3 hazard_tester.py -d 8.8.8.8
```

Specify multiple DNS servers (fallback order):

```bash
python3 hazard_tester.py -d 8.8.8.8 1.1.1.1
```

Increase number of concurrent queries (default: 64):

```bash
python3 hazard_tester.py -c 256
```

JSON output:

```bash
python3 hazard_tester.py -f json
```

### 3. Example output

**Text**
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
  "TIME": {"AVG_RES_ms": 25.3, "TOTAL_s": 8.1},
  "ERRORS": ["bad-domain1.com", "bad-domain2.net"]
}
```

---

## CLI options

| Option | Description | Default |
|--------|-------------|---------|
| `-d`, `--dns-server` | One or more DNS servers to query | `127.0.0.1` |
| `-c`, `--conn_number` | Number of concurrent DNS requests | `64` |
| `-f`, `--format` | Output format: `text` or `json` | `text` |