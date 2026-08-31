import os
import argparse
import httpx
import uvicorn
import mcp.types as types
from mcp.server import Server, ServerRequestContext
from mcp.server.transport_security import TransportSecuritySettings, TransportSecurityMiddleware


async def search_searxng(query: str) -> list[types.ContentBlock]:
    """Perform a web search using SearXNG."""
    searxng_url = os.getenv("SEARXNG_URL")
    
    if not searxng_url:
        return [types.TextContent(type="text", text="Error: SEARXNG_URL environment variable is not set.")]
    
    if not searxng_url.startswith("http"):
        searxng_url = f"http://{searxng_url}"
    
    params = {
        "q": query,
        "format": "json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{searxng_url}/search", params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if not results:
                return [types.TextContent(type="text", text=f"No results found for '{query}'.")]
            
            output_parts = []
            for res in results[:5]:  # Limit to top 5 results
                title = res.get("title", "No title")
                url = res.get("url", "No URL")
                snippet = res.get("content", "")
                output_parts.append(f"Title: {title}\nURL: {url}\nSnippet: {snippet}")
            
            result_text = "\n\n---\n\n".join(output_parts)
            return [types.TextContent(type="text", text=result_text)]
            
    except httpx.HTTPStatusError as e:
        return [types.TextContent(type="text", text=f"Error: SearXNG returned status {e.response.status_code}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: An unexpected error occurred: {str(e)}")]


async def handle_list_tools(
    ctx: ServerRequestContext, params: types.PaginatedRequestParams | None
) -> types.ListToolsResult:
    """Handle the list_tools request."""
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="search",
                title="SearXNG Search",
                description="Perform a web search using SearXNG. Accepts 'query' or 'q' as arguments.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "q": {"type": "string", "description": "Alias for query"}
                    },
                },
            )
        ]
    )


async def handle_call_tool(
    ctx: ServerRequestContext, params: types.CallToolRequestParams
) -> types.CallToolResult:
    """Handle the call_tool request."""
    if params.name != "search":
        raise ValueError(f"Unknown tool: {params.name}")
    
    arguments = params.arguments or {}
    actual_query = arguments.get("query") or arguments.get("q")
    
    if not actual_query:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="Error: No query provided. Please provide a search query using 'query' or 'q'.")]
        )
    
    result_content = await search_searxng(actual_query)
    return types.CallToolResult(content=result_content)


def main(host: str = "0.0.0.0", port: int = 8000):
    """Main entry point for the MCP server."""
    security_settings=TransportSecuritySettings(enable_dns_rebinding_protection=False),

    app = Server(
        "searxng-search",
        on_list_tools=handle_list_tools,
        on_call_tool=handle_call_tool,
    )

    app.add_middleware(TransportSecurityMiddleware, settings=security_settings)
    
    # Use Streamable HTTP transport (MCP v2 standard)
    uvicorn.run(app.streamable_http_app(), host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--searxng-url", type=str, help="SearXNG base URL (e.g., http://localhost:8888)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to listen on")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    args = parser.parse_args()

    if args.searxng_url:
        os.environ["SEARXNG_URL"] = args.searxng_url

    main(host=args.host, port=args.port)
