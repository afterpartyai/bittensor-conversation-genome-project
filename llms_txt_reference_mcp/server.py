"""
MCP server for the llms_txt_store SQLite database.

Tools:
  - search_sites(query)       Full-text search across all fields
  - get_site(domain)          Get raw llms.txt content for an exact domain
  - lookup_domain(domain)     Same as get_site but also tries subdomain variants
  - list_sites(tld?)          List all domains, optionally filtered by TLD
"""

import logging
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("llms-txt-mcp")

DB_PATH = Path(__file__).parent / "llms_txt.db"
STORE_DIR = Path(__file__).parent / "llms_txt_store"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db() -> None:
    """Run ingest if the database doesn't exist yet."""
    if not DB_PATH.exists():
        log.info("Database not found — running ingest from %s", STORE_DIR)
        from ingest import ingest
        n = ingest(STORE_DIR, DB_PATH)
        log.info("Ingest complete: %d sites loaded into %s", n, DB_PATH)
    else:
        conn = get_db()
        n = conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        conn.close()
        log.info("Database ready: %d sites indexed (%s)", n, DB_PATH)


mcp = FastMCP("llms-txt-reference")


@mcp.tool()
def search_sites(query: str, limit: int = 20) -> list[dict]:
    """
    Full-text search across domain, title, description, summary, and content.
    Returns a list of matches with domain, title, and description.
    """
    log.info("search_sites query=%r limit=%d", query, limit)
    conn = get_db()
    rows = conn.execute(
        """
        SELECT s.domain, s.title, s.description, s.tld
        FROM sites_fts f
        JOIN sites s ON s.id = f.rowid
        WHERE sites_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()
    conn.close()
    log.info("search_sites returned %d results for %r", len(rows), query)
    return [dict(r) for r in rows]


@mcp.tool()
def get_site(domain: str) -> dict:
    """
    Get the full llms.txt content for an exact domain name (e.g. "imperial.ac.uk").
    Returns domain, title, description, summary, and the full raw content.
    """
    log.info("get_site domain=%r", domain)
    conn = get_db()
    row = conn.execute(
        "SELECT domain, title, description, summary, content FROM sites WHERE domain = ?",
        (domain.lower().strip(),),
    ).fetchone()
    conn.close()
    if row is None:
        log.warning("get_site: no entry for domain %r", domain)
        return {"error": f"No entry found for domain '{domain}'"}
    log.info("get_site: found %r (%s)", row["domain"], row["title"])
    return dict(row)


@mcp.tool()
def lookup_domain(domain: str) -> dict:
    """
    Look up a domain by name. Tries an exact match first, then strips 'www.' prefix.
    Returns domain, title, description, summary, and full content.
    """
    log.info("lookup_domain domain=%r", domain)
    domain = domain.lower().strip()
    conn = get_db()

    row = conn.execute(
        "SELECT domain, title, description, summary, content FROM sites WHERE domain = ?",
        (domain,),
    ).fetchone()

    if row is None and domain.startswith("www."):
        stripped = domain[4:]
        log.info("lookup_domain: no exact match, retrying without www. -> %r", stripped)
        row = conn.execute(
            "SELECT domain, title, description, summary, content FROM sites WHERE domain = ?",
            (stripped,),
        ).fetchone()

    conn.close()
    if row is None:
        log.warning("lookup_domain: no entry for domain %r", domain)
        return {"error": f"No entry found for domain '{domain}'"}
    log.info("lookup_domain: found %r (%s)", row["domain"], row["title"])
    return dict(row)


@mcp.tool()
def list_sites(tld: str = "", limit: int = 200) -> list[dict]:
    """
    List all indexed sites. Optionally filter by TLD (e.g. "ac.uk", "com", "io").
    Returns a list of {domain, title, tld}.
    """
    log.info("list_sites tld=%r limit=%d", tld or "*", limit)
    conn = get_db()
    if tld:
        rows = conn.execute(
            "SELECT domain, title, tld FROM sites WHERE tld = ? ORDER BY domain LIMIT ?",
            (tld.lower().strip(), limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT domain, title, tld FROM sites ORDER BY domain LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    log.info("list_sites returned %d sites", len(rows))
    return [dict(r) for r in rows]


if __name__ == "__main__":
    log.info("Starting llms-txt-reference MCP server")
    ensure_db()
    log.info("MCP server ready, listening on stdio")
    mcp.run()
