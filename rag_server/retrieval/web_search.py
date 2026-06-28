import httpx


async def search_duckduckgo(query: str, num_results: int = 5) -> list[dict]:
    """Search DuckDuckGo HTML (no JS needed)."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            url = "https://html.duckduckgo.com/html/"
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9"
            }
            data = {"q": query, "b": "", "kl": "us-en"}

            response = await client.post(url, data=data, headers=headers)
            response.raise_for_status()

            import re
            from urllib.parse import unquote, parse_qs, urlparse
            html = response.text

            # Match <a class="result__a" href="..."> ... </a> and following snippet
            block_re = re.compile(
                r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>'
                r'.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
                re.DOTALL
            )
            tag_re = re.compile(r'<[^>]+>')

            results = []
            for m in block_re.finditer(html):
                raw_url = m.group(1)
                title = tag_re.sub('', m.group(2)).strip()
                snippet = tag_re.sub('', m.group(3)).strip()

                # DDG wraps real URL as /l/?uddg=<encoded>
                real_url = raw_url
                if raw_url.startswith("//duckduckgo.com/l/") or raw_url.startswith("/l/"):
                    qs = parse_qs(urlparse(raw_url).query)
                    if "uddg" in qs:
                        real_url = unquote(qs["uddg"][0])

                if real_url and real_url.startswith("http"):
                    results.append({
                        "title": title[:120],
                        "url": real_url,
                        "snippet": snippet[:300]
                    })
                if len(results) >= num_results:
                    break

            return results
    except Exception as e:
        print(f"DDG search error: {e}")
        return []


async def search_bing(query: str, num_results: int = 5) -> list[dict]:
    """Search Bing as fallback."""
    try:
        async with httpx.AsyncClient() as client:
            url = "https://www.bing.com/search"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            params = {"q": query}

            response = await client.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            import re
            results = []

            html = response.text
            pattern = r'<h2><a[^>]*href="([^"]*)"[^>]*>([^<]*)</a></h2>.*?<p>([^<]*)</p>'
            matches = re.findall(pattern, html, re.DOTALL)

            for url, title, snippet in matches[:num_results]:
                if url.startswith('http'):
                    results.append({
                        "title": title.strip()[:100],
                        "url": url,
                        "snippet": snippet.strip()[:200]
                    })

            return results[:num_results]
    except Exception as e:
        return []


async def web_search(query: str, num_results: int = 5) -> list[dict]:
    """Try multiple search engines."""
    results = await search_duckduckgo(query, num_results)

    if not results:
        results = await search_bing(query, num_results)

    return results
