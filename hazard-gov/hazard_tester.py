#!/usr/bin/env python3
# ---------------------------------------------------------------------------
#  hazard_tester.py
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

import sys
import time
import json
import asyncio
import idna
import xmltodict
import requests
import argparse
import dns.resolver
import dns.asyncresolver
from typing import Any, cast
from dns.rdtypes.IN.A import A

#################################################################

URL: str = "https://hazard.mf.gov.pl/api/Register"
DEFAULT_DNS_SERVER: str = "127.0.0.1"
SINK_IP: str = "145.237.235.240"
CONN: int = 64  # connections number
DNS_TIMEOUT: float | int = 5.0  # dns timeout

ARGUMENTS: dict[tuple[str, ...], dict[str, Any]] = {
    ("-d", "--dns-server"): {
        "dest": "dns_server",
        "nargs": "+",
        "default": DEFAULT_DNS_SERVER,
        "help": "Specify one or more DNS server addresses (default 127.0.0.1).",
    },
    ("-c", "--conn_number"): {
        "dest": "conn_number",
        "type": int,
        "default": CONN,
        "help": "Specify asynchronous connection number (default 128).",
    },
    ("-f", "--format"): {
        "dest": "format_type",
        "default": "text",
        "choices": ["text", "json"],
        "help": "Output format: text (default) or json.",
    },
}

#################################################################


async def get_domains() -> set[str]:
    """
    The function download records and return set.

    :return: set object that contains all fqdns.
    :rtype: set[str]
    """

    try:
        with requests.Session() as s:
            response: requests.Response = s.get(URL, timeout=(5, 60))
            response.raise_for_status()
            xml: list[dict[str, str]] = xmltodict.parse(response.text)[
                "Rejestr"
            ]["PozycjaRejestru"]
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        sys.exit(1)
    out: set[str] = set()
    for entry in xml:
        raw: str = entry["AdresDomeny"].lower()
        try:
            out.add(idna.encode(raw).decode())
        except idna.IDNAError:
            if all(c.isalnum() or c in "-._" for c in raw):
                out.add(raw)
    return out


async def ask(
    resolver: dns.asyncresolver.Resolver, domain: str
) -> tuple[str, bool, float]:
    """
    Try resolve FQDN.

    :param resolver: object resolver.
    :param str domain: fqdn to resolve.
    :return: (domain, ok, elapsed_seconds)
             ok == True if the A-answer is exactly [SINK_IP]
    :rtype: tuple[str, bool, float]
    """

    req_t0: float = time.perf_counter()
    try:
        ans: dns.resolver.Answer = await resolver.resolve(
            domain, "A", lifetime=DNS_TIMEOUT, tcp=False
        )
        req_dt0: float = time.perf_counter() - req_t0
        ok: bool = [cast(A, r).address for r in ans] == [SINK_IP]
        return domain, ok, req_dt0
    except Exception:
        req_dt0: float = time.perf_counter() - req_t0
        return domain, False, req_dt0


async def main(
    dns_server: list[str], conn_number: int, format_type: str
) -> None:
    """
    The main function that runs the script.

    :param tuple[Any, ...] args: all arguments.
    :return: None
    :rtype: None
    """

    domains: set[str] = await get_domains()
    res: dns.asyncresolver.Resolver = dns.asyncresolver.Resolver(
        configure=False
    )
    res.nameservers = dns_server

    sem: asyncio.Semaphore = asyncio.Semaphore(conn_number)

    async def worker(domain):
        """The function for limit connections."""
        async with sem:
            return await ask(res, domain)

    tasks = [asyncio.create_task(worker(d)) for d in domains]

    bad: list[str] = []
    req_counter: int = 0
    req_timer: float = 0.0

    t0: float = time.perf_counter()
    for fut in asyncio.as_completed(tasks):
        name, ok, req_dt = await fut
        req_counter += 1
        req_timer += req_dt
        if not ok:
            bad.append(name)
    dt_total: float = time.perf_counter() - t0

    avg_ms = (req_timer / req_counter * 1000.0) if req_counter else 0.0

    if format_type == "text":
        if bad:
            print("Errors:", *bad[:20], "...", file=sys.stderr)
        print(
            f"DNS={dns_server}  OK={len(domains)-len(bad)}  BAD={len(bad)}  "
            f"TIMERS: AVG_RES={avg_ms:.1f}ms TOTAL={dt_total:.1f}s"
        )
    if format_type == "json":
        output: dict[str, Any] = {
            "dns": dns_server,
            "ok": len(domains) - len(bad),
            "bad": len(bad),
            "timers": {
                "avg_res": round(avg_ms, 2),
                "total": round(dt_total, 2),
            },
            "errors": bad,
        }
        print(json.dumps(output))

    sys.exit(1 if bad else 0)


def get_parser() -> tuple[Any, ...]:
    """
    The function return parser object.

    :return: argmuent parser object.
    :rtype: tuple[Any, ...]
    """

    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="The script checks the correctness of answers for "
        " gambling domains made available on the journal hazard.mf.gov.pl"
    )
    for flags, params in ARGUMENTS.items():
        parser.add_argument(*flags, **params)
    args = parser.parse_args()

    return args.dns_server, args.conn_number, args.format_type


if __name__ == "__main__":
    dns_server, conn_number, format_type = get_parser()
    asyncio.run(main(dns_server, conn_number, format_type))
