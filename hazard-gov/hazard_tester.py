#!/usr/bin/env python3
import sys
import time
import asyncio
import dns.resolver
import idna
import xmltodict
import requests
import dns.asyncresolver

URL: str = "https://hazard.mf.gov.pl/api/Register"
DNS_SERVER: str = "127.0.0.1"
SINK_IP: str = "145.237.235.240"
CONC: int = 50
TIMEOUT: float | int = 5.0


async def get_domains() -> set[str]:
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


async def ask(resolver: dns.asyncresolver.Resolver, domain: str):
    try:
        ans: dns.resolver.Answer = await resolver.resolve(
            domain, "A", lifetime=TIMEOUT, tcp=False
        )
        return domain, [r.address for r in ans] == [SINK_IP]
    except Exception:
        return domain, False


async def main():
    domains: set[str] = await get_domains()
    res: dns.asyncresolver.Resolver = dns.asyncresolver.Resolver(
        configure=False
    )
    res.nameservers = [DNS_SERVER]

    sem: asyncio.Semaphore = asyncio.Semaphore(CONC)

    async def worker(domain):
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
