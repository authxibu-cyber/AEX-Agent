"""
Web Tools for Merlin Agent.
Real-time web search and full HTML-to-clean-text reader.
"""
from __future__ import annotations

import re
import urllib.parse
from typing import Optional
from bs4 import BeautifulSoup
import httpx

from merlin_agent.tools.base import ToolResult, tool


@tool(name="web_search", description="Search the web for technical information, documentation, and news.", toolset="web")
async def web_search(query: str, max_results: int = 5) -> ToolResult:
    """Performs DuckDuckGo HTML web search with user-agent emulation."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code != 200:
            return ToolResult(
                success=False,
                output="",
                error=f"Web search returned status code {resp.status_code}",
            )

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for r in soup.select(".result"):
            title_tag = r.select_one(".result__title")
            snippet_tag = r.select_one(".result__snippet")
            url_tag = r.select_one(".result__url")

            title = title_tag.get_text(strip=True) if title_tag else "No Title"
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            raw_href = title_tag.find("a")["href"] if (title_tag and title_tag.find("a")) else ""

            # Unquote DuckDuckGo redirect link
            link = raw_href
            if "uddg=" in raw_href:
                m = re.search(r"uddg=([^&]+)", raw_href)
                if m:
                    link = urllib.parse.unquote(m.group(1))

            if title and link:
                results.append(f"### {title}\nLink: {link}\n{snippet}\n")
                if len(results) >= max_results:
                    break

        if not results:
            return ToolResult(success=True, output=f"No results found for query: '{query}'")

        return ToolResult(success=True, output="\n".join(results))
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Web search failed: {e}")


@tool(name="fetch_web_page", description="Fetch a web page URL and extract its clean markdown text.", toolset="web")
async def fetch_web_page(url: str, max_chars: int = 10000) -> ToolResult:
    """Fetch URL and clean HTML markup into readable text."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code >= 400:
            return ToolResult(success=False, output="", error=f"HTTP error {resp.status_code} fetching {url}")

        soup = BeautifulSoup(resp.text, "html.parser")

        # Strip unneeded elements
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = "\n".join(lines)

        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + f"\n\n[... Truncated content beyond {max_chars} chars ...]"

        return ToolResult(success=True, output=cleaned, metadata={"url": url, "chars": len(cleaned)})
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Failed to fetch webpage: {e}")
