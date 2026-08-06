#!/usr/bin/env python3
"""
Extract content straight out of a raw Drupal mysqldump .sql file — no
database server required. Written while rebuilding coastsincrisis.net
from a Drupal 9 backup into a static 11ty site.

Why this exists instead of just restoring the dump to MySQL and querying it:
that's honestly the more approachable route if you're not comfortable
regex-parsing SQL (see the note at the bottom of this file). This script
is the "no database available" fallback — it treats the .sql file as text
and pattern-matches the INSERT statements directly.

Two gotchas this script exists to handle:

1. mysqldump splits large tables across MULTIPLE `INSERT INTO` statements.
   If you naively grab the first one with re.search(), you will silently
   miss rows. (This is exactly how a chunk of site content went missing
   on the first pass — the People page's INSERT happened to land in the
   second statement.) `find_insert_statements()` below always collects
   ALL of them for a table before parsing rows.

2. Drupal's body field content is stored as literal SQL-escaped text
   (\' \" \\r\\n etc.), not real newlines/quotes. `unescape_sql_string()`
   undoes that.

Usage:
    python3 drupal_extract.py path/to/dump.sql --bundle page --nid 6
    python3 drupal_extract.py path/to/dump.sql --alias-for 6 12 24
"""

import argparse
import re
import sys


def find_insert_statements(sql_text: str, table: str) -> list[str]:
    """Return every `INSERT INTO `table`...;` statement for a table.

    mysqldump batches large tables into several INSERT statements when a
    single one would exceed max_allowed_packet. Grabbing only the first
    (e.g. via re.search) silently drops rows from later batches — always
    collect all of them.
    """
    pattern = r"INSERT INTO `%s`.*?;\n" % re.escape(table)
    return re.findall(pattern, sql_text, re.S)


def unescape_sql_string(value: str) -> str:
    """Undo mysqldump's escaping of a single-quoted string literal.

    Drupal body content comes out of the dump with literal backslash
    sequences (\\', \\", \\r\\n) rather than real characters.
    """
    return (
        value.replace("\\'", "'")
        .replace('\\"', '"')
        .replace("\\r\\n", "\n")
        .replace("\\n", "\n")
    )


def get_node_body_deltas(
    sql_text: str, bundle: str, nid: int, rewrite_image_path: str | None = None
) -> list[str]:
    """Get every body "delta" (paragraph/block) for one node, in order.

    Drupal stores a multi-value body field as one row per delta (0, 1, 2,
    ...) in `node__body`. A single node's content is usually spread
    across several of these — e.g. a hero image, a curator statement, an
    embedded video, and a rotating icon might each be their own delta.

    `bundle` is the content type machine name (e.g. "page",
    "creative_resistance_content") and is part of node__body's own
    composite key, so it must match or the row won't be found.

    Pass `rewrite_image_path` (e.g. "/assets/images/") to rewrite Drupal's
    "/sites/default/files/inline-images/" src prefix to your own — handy
    when re-hosting the same images in a different static-site layout.
    """
    statements = find_insert_statements(sql_text, "drup_node__body")
    full_body = "\n".join(statements)

    row_pattern = (
        r"\('%s', 0, %d, \d+, 'en', (\d+), '((?:[^'\\]|\\.)*)', "
        r"'((?:[^'\\]|\\.)*)', '(\w+)'\)" % (re.escape(bundle), nid)
    )
    rows = re.findall(row_pattern, full_body)
    rows.sort(key=lambda r: int(r[0]))  # order by delta

    deltas = []
    for _delta, value, _summary, _format in rows:
        text = unescape_sql_string(value)
        if rewrite_image_path:
            text = text.replace(
                "/sites/default/files/inline-images/", rewrite_image_path
            )
        deltas.append(text)
    return deltas


def get_path_alias(sql_text: str, nid: int) -> str | None:
    """Look up the clean URL alias for a node (e.g. /node/6 -> /entangledecologies)."""
    statements = find_insert_statements(sql_text, "drup_path_alias")
    full_body = "\n".join(statements)
    matches = re.findall(
        r"\(\d+, \d+, '[^']+', 'en', '/node/%d', '([^']+)'" % nid, full_body
    )
    return matches[0] if matches else None


def get_node_titles(sql_text: str) -> list[tuple[int, str, str]]:
    """List every (nid, bundle, title) in the site — a quick way to see
    what content exists before you go extracting individual nodes."""
    statements = find_insert_statements(sql_text, "drup_node_field_data")
    full_body = "\n".join(statements)
    rows = re.findall(
        r"\((\d+), \d+, '([a-z_]+)', 'en', \d+, \d+, '((?:[^'\\]|\\.)*)'", full_body
    )
    return [(int(nid), bundle, unescape_sql_string(title)) for nid, bundle, title in rows]


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sql_file", help="path to the mysqldump .sql file")
    parser.add_argument("--bundle", help="content type machine name, e.g. 'page'")
    parser.add_argument("--nid", type=int, help="node id")
    parser.add_argument(
        "--rewrite-images",
        default="/assets/images/",
        help="prefix to replace '/sites/default/files/inline-images/' with",
    )
    parser.add_argument(
        "--alias-for", type=int, nargs="+", help="one or more nids to look up path aliases for"
    )
    parser.add_argument(
        "--list-titles", action="store_true", help="list every node's (nid, bundle, title)"
    )
    args = parser.parse_args()

    with open(args.sql_file, "r", errors="ignore") as f:
        sql_text = f.read()

    if args.list_titles:
        for nid, bundle, title in get_node_titles(sql_text):
            print(f"{nid}\t{bundle}\t{title}")
        return

    if args.alias_for:
        for nid in args.alias_for:
            alias = get_path_alias(sql_text, nid)
            print(f"{nid}\t{alias or '(none)'}")
        return

    if args.bundle and args.nid:
        deltas = get_node_body_deltas(
            sql_text, args.bundle, args.nid, rewrite_image_path=args.rewrite_images
        )
        for i, delta in enumerate(deltas):
            print(f"<!-- delta {i} -->")
            print(delta)
            print()
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    _main()


# ---------------------------------------------------------------------------
# The lower-barrier alternative, for next time
# ---------------------------------------------------------------------------
#
# Regex-parsing a raw SQL dump (what this script does) is a shortcut, not
# the "correct" way in — it's fragile against anything unusual in the
# escaping. The friendlier path for a non-programmer: actually restore the
# dump into a real database and browse/query it normally.
#
#   1. Install MySQL or MariaDB locally (or run one in Docker).
#   2. Create an empty database and import the dump:
#        mysql -u root -p your_db_name < dump.sql
#   3. Point a GUI like TablePlus, Sequel Ace, or phpMyAdmin at it and
#      browse the tables directly — no scripting required.
#
# The Drupal-specific tables worth knowing about:
#   drup_node_field_data     - node id, content type ("bundle"), title
#   drup_node__body          - the actual rich-text body content, one row
#                               per "delta" (paragraph/block) per node
#   drup_path_alias          - maps /node/123 to clean URLs like /about
#   drup_block_content*      - custom blocks (nav, footer, etc.), if used
