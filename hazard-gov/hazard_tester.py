#!/usr/bin/env python3
# ---------------------------------------------------------------------------
#  hazard_bind.py
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
import asyncio
import idna
import xmltodict
import requests
import dns.resolver
import dns.asyncresolver
from typing import cast
from dns.rdtypes.IN.A import A

#################################################################

URL: str = "https://hazard.mf.gov.pl/api/Register"
DNS_SERVER: str = "127.0.0.1"
SINK_IP: str = "145.237.235.240"
CONC: int = 254  # connections number
TIMEOUT: float | int = 5.0  # dns timeout

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
) -> tuple[str, bool]:
    """
    The function try resolve fqdn.

    :param resolver: object resolver.
    :param str domain: fqdn to resolve.
    :return: FQDN and the value of bool or a returned IP address is correct.
    :rtype: tuple[str, bool]
    """

    try:
        ans: dns.resolver.Answer = await resolver.resolve(
            domain, "A", lifetime=TIMEOUT, tcp=False
        )
        return domain, [cast(A, r).address for r in ans] == [SINK_IP]
    except Exception:
        return domain, False


async def main() -> None:
    """
    The main function that runs the script.

    :return: None
    :rtype: None
    """

    domains: set[str] = await get_domains()
    res: dns.asyncresolver.Resolver = dns.asyncresolver.Resolver(
        configure=False
    )
    res.nameservers = [DNS_SERVER]

    sem: asyncio.Semaphore = asyncio.Semaphore(CONC)

    async def worker(domain):
        """The function for limit connections."""
        async with sem:
            return await ask(res, domain)

    tasks = [asyncio.create_task(worker(d)) for d in domains]

    bad = []
    t0 = time.time()
    for fut in asyncio.as_completed(tasks):
        name, ok = await fut
        if not ok:
            bad.append(name)
    dt = time.time() - t0

    if bad:
        print("Errors:", *bad[:20], "...", file=sys.stderr)
    print(f"OK={len(domains)-len(bad)}  BAD={len(bad)}  ({dt:.1f}s)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    asyncio.run(main())
