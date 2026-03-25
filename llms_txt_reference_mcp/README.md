# llms_txt_reference_mcp

A minimal MCP server that ingests the [llms_txt_store](https://github.com/afterpartyai/llms_txt_store) dataset into SQLite and exposes it as queryable MCP tools.

## Setup

```bash
pip install -r requirements.txt
```

The server will automatically clone `llms_txt_store/` from GitHub on first run. Requires `git` to be installed.

**If git is not installed:**
- macOS: `brew install git`
- Ubuntu: `sudo apt install git`
- Windows: https://git-scm.com/download/win

## Running

```bash
python server.py
```

On first run the server will clone the [llms_txt_store](https://github.com/afterpartyai/llms_txt_store) repo and ingest all `llms.txt` files into `llms_txt.db`. On subsequent runs it fetches any new commits and re-ingests only if the store has changed. If the store is already up to date, the existing database is used as-is.

To sync and re-ingest manually:

```bash
python ingest.py
```

## MCP Tools

| Tool | Args | Description |
|------|------|-------------|
| `search_sites` | `query: str`, `limit: int = 20` | Full-text search across domain, title, description, and content |
| `get_site` | `domain: str` | Get full llms.txt content for an exact domain |
| `lookup_domain` | `domain: str` | Like `get_site` but also tries stripping `www.` prefix |
| `list_sites` | `tld: str = ""`, `limit: int = 200` | List all sites, optionally filtered by TLD |

## Database Schema

- `sites` — one row per domain (domain, tld, subdomain, title, description, summary, content)
- `links` — extracted hyperlinks per site and section
- `sites_fts` — FTS5 full-text index over sites

## MCP Config (Claude Desktop / other clients)

```json
{
  "mcpServers": {
    "llms-txt-reference": {
      "command": "python",
      "args": ["/path/to/llms_txt_reference_mcp/server.py"]
    }
  }
}
```
