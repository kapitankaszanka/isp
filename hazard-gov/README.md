# BIND updater for the Polish gambling blacklist

`hazard_updater.py` downloads the XML blacklist published by Poland’s Ministry of Finance (“Rejestr Stron Hazardowych”), parses it and builds a **Response-Policy Zone** named **hazard-rpz**.  
Every domain in that list is redirected to **145 .237 .235 .240**.

---

## Quick start

### 1. Install the script

```bash
git colone https://github.com/kapitankaszanka/isp.git
cd isp/hazard-gov.
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
```

### 2. Install the script
Add RPZ configuration to BIND
Create hazard zone configuration file.
```bash
touch /etc/bind/hazard-rpz.conf
```
Add configuration to file.
```bash
zone "hazard-rpz" {
        type master;
        file "/etc/bind/db.hazard-rpz";
        check-names ignore;         // accepts labels with “_”
};

response-policy {
        zone "hazard-rpz";
} break-dnssec yes;
```

and include it from your main config, e.g.:
```bash
include "/etc/bind/hazard-rpz.conf";
```

Reload BIND so it sees the new include:
```bash
sudo rndc reconfig
```

### 3. Run once and set up systemd

Manual check
```bash
sudo /opt/isp/hazard-gov/.venv/bin/python3 /opt/isp/hazard-gov/hazard_updater.py
rndc zonestatus hazard-rpz     # should report “loaded serial …”
```

Systemd service & timer.
```bash
sudo touch /etc/systemd/system/hazard-rpz.service
sudo touch /etc/systemd/system/hazard-rpz.timer
```

```ini
[Unit]
Description=Update the hazard RPZ zone
After=network-online.target named.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/opt/isp/hazard-gov/.venv/bin/python3 /opt/isp/hazard-gov/hazard_updater.py

[Install]
WantedBy=multi-user.target
```
And timer configuration
```ini
[Unit]
Description=Run hazard_rpz every 15 minutes

[Timer]
OnCalendar=*:0/15
Unit=hazard-rpz.service
AccuracySec=5min
Persistent=true

[Install]
WantedBy=timers.target

```
Reload systemd
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hazard-rpz.timer
```
The timer now updates the blacklist every hour; any change automatically triggers
rndc reload hazard-rpz.
