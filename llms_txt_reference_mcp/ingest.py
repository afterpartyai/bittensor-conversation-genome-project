"""
Ingest llms_txt_store into an SQLite database.

Path scheme: /{tld}/{subdomain_if_any}/{char-exploded-domain}/llms.txt
- Single-char segments spell out the domain name
- Multi-char segments (after the tld) are subdomains
"""

import logging
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("llms-txt-ingest")

STORE_DIR = Path(__file__).parent / "llms_txt_store"
DB_PATH = Path(__file__).parent / "llms_txt.db"
REPO_URL = "https://github.com/afterpartyai/llms_txt_store.git"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY,
    domain TEXT UNIQUE,
    tld TEXT,
    subdomain TEXT,
    title TEXT,
    description TEXT,
    summary TEXT,
    content TEXT,
    file_path TEXT
);

CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES sites(id),
    section TEXT,
    url TEXT,
    link_title TEXT,
    link_description TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS sites_fts USING fts5(
    domain, title, description, summary, content,
    content=sites, content_rowid=id
);
"""


def path_to_domain(rel_path: Path) -> tuple[str, str, str | None]:
    """
    Convert a relative path (from store root, excluding llms.txt) to (domain, tld, subdomain).

    Examples:
      ae/a/i/r/b/n/b          -> ("airbnb.ae", "ae", None)
      ac.uk/i/m/p/e/r/i/a/l   -> ("imperial.ac.uk", "ac.uk", None)
      ac.uk/blogs/k/c/l       -> ("blogs.kcl.ac.uk", "ac.uk", "blogs")
    """
    parts = rel_path.parts  # e.g. ("ae", "a", "i", "r", "b", "n", "b")
    tld = parts[0]
    rest = parts[1:]

    subdomain = None
    domain_chars = []

    for seg in rest:
        if len(seg) == 1:
            domain_chars.append(seg)
        else:
            subdomain = seg

    domain_name = "".join(domain_chars) + "." + tld
    if subdomain:
        domain_name = subdomain + "." + domain_name

    return domain_name, tld, subdomain


def parse_llms_txt(content: str) -> dict:
    """Parse an llms.txt file into structured fields."""
    lines = content.splitlines()
    result = {
        "title": None,
        "description": None,
        "summary": None,
        "sections": [],  # list of {"heading": str, "links": [...], "topics": [...]}
    }

    current_section = None
    i = 0

    while i < len(lines):
        line = lines[i]

        # H1 title
        if line.startswith("# ") and result["title"] is None:
            result["title"] = line[2:].strip()

        # Blockquote description (first one)
        elif line.startswith(">") and result["description"] is None:
            result["description"] = line.lstrip("> ").strip()

        # H2 section
        elif line.startswith("## "):
            current_section = {"heading": line[3:].strip(), "links": [], "topics": []}
            result["sections"].append(current_section)

        # Bullet item
        elif line.startswith("- ") and current_section is not None:
            item = line[2:].strip()
            # Check if it's a markdown link: [title](url): description
            link_match = re.match(r'\[([^\]]+)\]\(([^)]+)\)(?::\s*(.+))?', item)
            if link_match:
                current_section["links"].append({
                    "title": link_match.group(1),
                    "url": link_match.group(2),
                    "description": (link_match.group(3) or "").strip(),
                })
            else:
                current_section["topics"].append(item)

        # First non-empty paragraph after description (summary)
        elif (
            result["description"] is not None
            and result["summary"] is None
            and line.strip()
            and not line.startswith("#")
            and not line.startswith(">")
            and not line.startswith("-")
        ):
            result["summary"] = line.strip()

        i += 1

    return result


def sync_store(store_dir: Path = STORE_DIR, repo_url: str = REPO_URL) -> bool:
    """
    Clone or fetch the llms_txt_store repo.
    Returns True if data was updated (clone or new commits pulled), False if already up to date.
    Raises RuntimeError if git is not installed.
    """
    git = shutil.which("git")
    if git is None:
        raise RuntimeError(
            "git is not installed or not on PATH.\n"
            "Install git:\n"
            "  macOS:   brew install git\n"
            "  Ubuntu:  sudo apt install git\n"
            "  Windows: https://git-scm.com/download/win\n"
            "Then re-run this script."
        )

    def run(*args, **kwargs):
        return subprocess.run([git, *args], capture_output=True, text=True, **kwargs)

    # Clone if not present
    if not (store_dir / ".git").exists():
        log.info("Cloning %s -> %s", repo_url, store_dir)
        result = run("clone", "--depth=1", repo_url, str(store_dir))
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed:\n{result.stderr.strip()}")
        log.info("Clone complete")
        return True

    # Fetch and check for new commits
    log.info("Fetching latest commits from origin ...")
    fetch = run("fetch", "--quiet", cwd=str(store_dir))
    if fetch.returncode != 0:
        raise RuntimeError(f"git fetch failed:\n{fetch.stderr.strip()}")

    local = run("rev-parse", "HEAD", cwd=str(store_dir)).stdout.strip()
    remote = run("rev-parse", "FETCH_HEAD", cwd=str(store_dir)).stdout.strip()

    if local == remote:
        log.info("Already up to date (HEAD=%s)", local[:8])
        return False

    log.info("New commits available (%s -> %s), pulling ...", local[:8], remote[:8])
    pull = run("merge", "--ff-only", "FETCH_HEAD", cwd=str(store_dir))
    if pull.returncode != 0:
        raise RuntimeError(f"git merge failed:\n{pull.stderr.strip()}")
    log.info("Pull complete")
    return True


def ingest(store_dir: Path = STORE_DIR, db_path: Path = DB_PATH) -> int:
    """Walk store_dir, parse all llms.txt files, insert into SQLite. Returns count."""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    count = 0
    for llms_file in store_dir.rglob("llms.txt"):
        # Skip README or any non-data file
        rel = llms_file.relative_to(store_dir)
        # rel looks like: ae/a/i/r/b/n/b/llms.txt
        path_without_filename = rel.parent

        try:
            domain, tld, subdomain = path_to_domain(path_without_filename)
        except Exception:
            continue

        content = llms_file.read_text(encoding="utf-8", errors="replace")
        parsed = parse_llms_txt(content)

        try:
            cur = conn.execute(
                """INSERT OR REPLACE INTO sites
                   (domain, tld, subdomain, title, description, summary, content, file_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    domain,
                    tld,
                    subdomain,
                    parsed["title"],
                    parsed["description"],
                    parsed["summary"],
                    content,
                    str(llms_file),
                ),
            )
            site_id = cur.lastrowid

            for section in parsed["sections"]:
                for link in section["links"]:
                    conn.execute(
                        """INSERT INTO links (site_id, section, url, link_title, link_description)
                           VALUES (?, ?, ?, ?, ?)""",
                        (site_id, section["heading"], link["url"], link["title"], link["description"]),
                    )

            count += 1
        except Exception as e:
            print(f"Warning: skipped {llms_file}: {e}")

    # Populate FTS index
    conn.execute("INSERT INTO sites_fts(sites_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()
    return count


if __name__ == "__main__":
    updated = sync_store()
    if updated:
        log.info("Store updated, running ingest ...")
    else:
        log.info("Store unchanged, running ingest ...")
    n = ingest()
    log.info("Done. Ingested %d sites into %s", n, DB_PATH)
