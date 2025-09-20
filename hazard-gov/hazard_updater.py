#!/usr/bin/env python3
# ---------------------------------------------------------------------------
#  hazard_updater.py
#
#  Copyright (c) 2025 Mateusz Krupczyński
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
# ---------------------------------------------------------------------------

import hashlib
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import idna
import requests
import xmltodict

#################################################################

ZONE_PATH: str = "/etc/bind/db.hazard-rpz"
TTL: int = 300
LOGLEVEL: int = logging.INFO
URL_REGISTER: str = "https://hazard.mf.gov.pl/api/Register"
SINK_IP: str = "145.237.235.240"
RNDC_CMD: list[str] = ["rndc", "reload", "hazard-rpz"]

#################################################################


def fetch_xml(
    url: str, timeout: float | int | tuple[int, int] = (5, 60)
) -> list[dict[str, Any]]:
    """
    The function download records and return parsed dict.

    :param str url: url from where xml will be downladed.
    :param timeout: timeout for GET Request, defualt 5, 60.
    :type timeout: float | int | tuple[int, int]
    :return: list object with dict that contains info about domain.
    :rtype: list[dict[str, str]]
    """

    with requests.Session() as s:
        logging.debug("Trying download domain list.")
        try:
            _response: requests.Response = s.get(url, timeout=timeout)
            _response.raise_for_status()
            logging.debug("Parsing the downloaded domain list.")
            parsed: Any = xmltodict.parse(_response.content)
            return parsed["Rejestr"]["PozycjaRejestru"]
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error: {e}")
            raise
        except Exception as e:
            logging.error(f"Error occurred when parsing XML file: {e}")
            raise


def make_domain_set(
    domain_list: list[dict[str, str]], domain_key: str = "AdresDomeny"
) -> set[str]:
    """
    The function pulls out all domains from the parsd dictionary.

    :params list[dict[str,str]] domain_list: parsed dictionary.
    :params str domain_key: key name from domain_list, from which
                            the domain will be pulled out.
    :return: all domains.
    :rtype: set[str]
    """

    out: set[str] = set()
    logging.debug("Creating domains set from downloaded list.")
    logging.debug("Checking idna standard.")
    for entry in domain_list:
        raw: str = entry[domain_key].lower()
        try:
            out.add(idna.encode(raw).decode())
        except idna.IDNAError:
            if all(c.isalnum() or c in "-._" for c in raw):
                out.add(raw)
    logging.info(f"Active domains in register: {len(out)}")
    return out


def render_zone_file(domains: set[str], sink_ip: str, zone_ttl: int) -> str:
    """
    The function is responsible for creating string object with data
    that will be saved to zone file.
    The created object is later used to verify whether the zone file
    should be updated. In case of changes, you should also check whether
    the change is also required in compare_zones() function.

    :param set[str] domains: set with all domains that will be addred to
                              zone file.
    :param str sink_ip: ip with bind will response.
    :param int zone_ttl: ttl for entry in zone.
    :return: multiline string object.
    :rtype: str
    """

    logging.debug("Creating zone file string object.")
    serial: int = int(time.time())
    head: str = f"""$TTL {zone_ttl}
@ SOA localhost. root.localhost. ( 
                {serial}
                3600
                600
                30D
                3600
                )
@ IN NS localhost.
sink IN A {sink_ip}

; --- BEGIN DATA ---

"""
    body = "\n".join(f"{d} IN CNAME sink" for d in sorted(domains))
    return head + body + "\n"


def compare_zones(zone_path: Path, new_zone_obj: str) -> bool:
    """
    The function is responsible for checking whether there
    has been a change of zone. SHA1 is calculated from the
    'sink' entry to the end of the file.

    :param Path zone_path: path to file to compare.
    :param new_zone_obj: the objec with wich the file will be compared.
    :return: False if file don't need to be overwriten.
             True if file need to be overwriten.
    :rtype: bool
    """

    logging.debug("Loading current zone file.")
    zone_file: str = zone_path.read_text() if zone_path.exists() else ""
    split_string: str = "; --- BEGIN DATA ---"
    try:
        zone_data: str = zone_file.split(split_string)[1]
        new_zone_data: str = new_zone_obj.split(split_string)[1]
    except Exception as e:
        logging.warning(f"Error ocurred when comparing files: {e}")
        logging.warning("Can't compare zones. Zone file will be overwriten.")
        return True
    logging.debug("Comparing zones.")
    old_file_hash: bytes = hashlib.sha1(zone_data.encode()).digest()
    new_file_hash: bytes = hashlib.sha1(new_zone_data.encode()).digest()
    result: bool = old_file_hash != new_file_hash

    return result


def write_if_changed(zone_path: Path, zone_content: str) -> bool:
    """
    The function checks whether there are changes in the file given.
    If the changes occur, the file is overwritten.

    :params Path zone_path: path with the file to compare.
    :params str zone_content: new created file to compare.
    :return: the file has been changed?
    :rtype: bool
    """

    logging.debug("Starting compare zones.")
    changed: bool = compare_zones(zone_path, zone_content)
    if changed:
        logging.debug("Changes in zone detected. Overwriting zone file.")
        zone_path.write_text(zone_content)
        logging.info(f"File {zone_path} was updated ({len(zone_content) // 1024}kB).")
        return True
    else:
        logging.info("No changes to the file.")
        return False


def main() -> int:
    """
    Run the script.

    :return: succes or not, exit code.
    :rtype: int
    """

    logging.info("Executing script.")
    try:
        domains_list: list[dict[str, Any]] = fetch_xml(URL_REGISTER)
        domains: set[str] = make_domain_set(domains_list)
        zone_txt: str = render_zone_file(domains, SINK_IP, TTL)
        if write_if_changed(Path(ZONE_PATH), zone_txt):
            logging.debug("Reloading the zone file.")
            subprocess.run(RNDC_CMD, check=True, stdout=subprocess.DEVNULL)
            logging.info("The launch of the script was successful")
        else:
            logging.info("The launch of the script was successful")
        return 0
    except Exception as e:
        logging.critical(f"Fatal error ocure: {e}")
        return 1


if __name__ == "__main__":
    logging.basicConfig(
        level=LOGLEVEL,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )
    sys.exit(main())
