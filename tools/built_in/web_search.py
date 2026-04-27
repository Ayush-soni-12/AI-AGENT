import traceback
from pydantic import BaseModel, Field
from tools.base import Tool, ToolInvocation, ToolResult, ToolKind

class WebSearchParams(BaseModel):
    query: str = Field(..., description="The search query to look up on the web.")
    max_results: int = Field(5, description="Maximum number of results to retrieve (1-10).")

class WebSearchTool(Tool):
    name = "web_search"
    description = (
        "Search the live internet using DuckDuckGo and return relevant information snippets. "
        "Use this to find latest documentation, library updates, error explanations, tutorials, or any current information."
    )
    kind = ToolKind.WEB
    schema = WebSearchParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = WebSearchParams(**invocation.params)
        max_results = max(1, min(10, params.max_results))

        # --- Primary: ddgs (new official package) ---
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                search_results = list(ddgs.text(params.query, max_results=max_results))
            if search_results:
                return self._format_results(search_results, params.query)
        except Exception as e:
            primary_error = str(e)
        else:
            primary_error = "No results from ddgs"

        # --- Fallback: Scrape DuckDuckGo lite HTML page directly ---
        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"}
            url = f"https://lite.duckduckgo.com/lite/?q={params.query.replace(' ', '+')}"
            resp = requests.get(url, headers=headers, timeout=8)
            soup = BeautifulSoup(resp.text, "html.parser")

            results = []
            for row in soup.select("tr"):
                link_tag = row.select_one("a.result-link")
                snip_tag = row.select_one("td.result-snippet")
                if link_tag and snip_tag:
                    results.append({
                        "title": link_tag.get_text(strip=True),
                        "href": link_tag["href"],
                        "body": snip_tag.get_text(strip=True)
                    })
                    if len(results) >= max_results:
                        break

            if results:
                return self._format_results(results, params.query)

            return ToolResult.error_result(
                f"Web search returned no results for '{params.query}'.\n"
                f"Primary error: {primary_error}\n"
                "The network may be restricted or DuckDuckGo is rate-limiting this machine."
            )

        except Exception as e:
            return ToolResult.error_result(
                f"Web search completely failed.\n"
                f"Primary (ddgs) error: {primary_error}\n"
                f"Fallback (html scrape) error: {e}\n"
                f"{traceback.format_exc()}"
            )

    def _format_results(self, results: list[dict], query: str) -> ToolResult:
        import requests
        from bs4 import BeautifulSoup

        lines = [f"🔎 Web search results for: **{query}**\n"]
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"}

        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            href = r.get("href", "")
            snippet = r.get("body", "").strip()
            
            lines.append(f"**[{i}] {title}**\n🔗 {href}\n📋 Snippet: {snippet}\n")

            # Scrape actual page content for top 3 results
            if i <= 3 and href:
                try:
                    resp = requests.get(href, headers=headers, timeout=6)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        # Remove garbage tags
                        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                            tag.decompose()
                        # Try to extract main article content first
                        main = soup.find("article") or soup.find("main") or soup.find(id="content") or soup.body
                        if main:
                            text = main.get_text(separator=" ", strip=True)
                            # Collapse whitespace
                            import re
                            text = re.sub(r'\s+', ' ', text).strip()
                            text = text[:2000] + ("..." if len(text) > 2000 else "")
                            lines.append(f"📄 **Page Content:**\n{text}\n")
                except Exception:
                    pass  # silently skip if scraping fails

        return ToolResult.success_result("\n---\n".join(lines))

