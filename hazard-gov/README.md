# BIND updater for the Polish gambling blacklist
The repository contains two scripts useful for initiating blocking of gambling domains in accordance with the Polish registry of domains used to offer gambling games in violation of the Act.
Currently, only bind9 is supported as a DNS server.

- hazard_updater.py - a script that updates the RPZ zone for the bind9 daemon.
- hazard_tester.py - a script that verifies the correctness of responses from the DNS server.

---

## Documentation:
#### ENG
 - [Hazard updater](./doc/eng/hazard_updater.md)
 - [Hazard tester](./doc/eng/hazard_tester.md)
#### PL
 - [Hazard updater](./doc/pl/hazard_updater-pl.md)
 - [Hazard tester](./doc/pl/hazard_tester-pl.md)
