"""
Core graph operations. All functions accept a _Conn from db.get_db()
and return plain dicts. Nothing here knows the DB is MariaDB.
"""

import json
from typing import Optional


def create_node(conn, name: str, node_type: str = "thing") -> dict:
    cur = conn.execute(
        "INSERT INTO nodes (name, type) VALUES (%s, %s)",
        (name, node_type),
    )
    node_id = cur.lastrowid
    conn.commit()
    return conn.execute("SELECT * FROM nodes WHERE id = %s", (node_id,)).fetchone()


def get_or_create_node(conn, name: str, node_type: str = "thing") -> dict:
    row = conn.execute("SELECT * FROM nodes WHERE name = %s", (name,)).fetchone()
    if row:
        return row
    return create_node(conn, name, node_type)


def set_property(conn, node_id: int, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO properties (node_id, `key`, value) VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE value = VALUES(value)
        """,
        (node_id, key, value),
    )
    conn.execute(
        "UPDATE nodes SET updated_at = NOW() WHERE id = %s", (node_id,)
    )
    conn.commit()


def link_nodes(
    conn,
    source_id: int,
    target_id: int,
    flavour: str = "uses_serves",
    label: Optional[str] = None,
) -> dict:
    _label = label if label is not None else ""
    conn.execute(
        """
        INSERT INTO links (source_id, target_id, flavour, label) VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE flavour = VALUES(flavour)
        """,
        (source_id, target_id, flavour, _label),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM links WHERE source_id = %s AND target_id = %s AND label = %s",
        (source_id, target_id, _label),
    ).fetchone()
    return _normalise_link(row)


def _normalise_link(row: dict) -> dict:
    """Convert empty-string label back to None for API consistency."""
    if row and row.get("label") == "":
        row = dict(row)
        row["label"] = None
    return row


def _node_with_props(conn, node_id: int) -> Optional[dict]:
    node = conn.execute("SELECT * FROM nodes WHERE id = %s", (node_id,)).fetchone()
    if not node:
        return None
    props = conn.execute(
        "SELECT `key`, value FROM properties WHERE node_id = %s", (node_id,)
    ).fetchall()
    return {
        **node,
        "properties": {r["key"]: r["value"] for r in props},
    }


def get_node_with_neighbours(conn, node_id: int) -> Optional[dict]:
    node = _node_with_props(conn, node_id)
    if not node:
        return None

    out_links = conn.execute(
        "SELECT * FROM links WHERE source_id = %s", (node_id,)
    ).fetchall()
    in_links = conn.execute(
        "SELECT * FROM links WHERE target_id = %s", (node_id,)
    ).fetchall()

    neighbours = []
    for lnk in out_links:
        neighbour = _node_with_props(conn, lnk["target_id"])
        if neighbour:
            neighbours.append({"direction": "out", "link": _normalise_link(lnk), "node": neighbour})
    for lnk in in_links:
        neighbour = _node_with_props(conn, lnk["source_id"])
        if neighbour:
            neighbours.append({"direction": "in", "link": _normalise_link(lnk), "node": neighbour})

    return {**node, "neighbours": neighbours}


def update_node(
    conn,
    node_id: int,
    name: Optional[str] = None,
    node_type: Optional[str] = None,
    properties: Optional[dict] = None,
) -> Optional[dict]:
    if name is not None or node_type is not None:
        sets, params = ["updated_at = NOW()"], []
        if name is not None:
            sets.append("name = %s")
            params.append(name)
        if node_type is not None:
            sets.append("type = %s")
            params.append(node_type)
        params.append(node_id)
        conn.execute(f"UPDATE nodes SET {', '.join(sets)} WHERE id = %s", params)

    if properties is not None:
        for key, value in properties.items():
            if value is None:
                conn.execute(
                    "DELETE FROM properties WHERE node_id = %s AND `key` = %s",
                    (node_id, key),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO properties (node_id, `key`, value) VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE value = VALUES(value)
                    """,
                    (node_id, key, value),
                )
    conn.commit()
    return _node_with_props(conn, node_id)


def delete_node(conn, node_id: int) -> int:
    link_count = conn.execute(
        "SELECT COUNT(*) AS cnt FROM links WHERE source_id = %s OR target_id = %s",
        (node_id, node_id),
    ).fetchone()["cnt"]
    conn.execute("DELETE FROM nodes WHERE id = %s", (node_id,))
    conn.commit()
    return link_count


def delete_link(conn, link_id: int) -> bool:
    cur = conn.execute("DELETE FROM links WHERE id = %s", (link_id,))
    conn.commit()
    return cur.rowcount > 0


def get_types(conn) -> list:
    rows = conn.execute(
        "SELECT type, COUNT(*) AS count FROM nodes GROUP BY type ORDER BY count DESC, type ASC"
    ).fetchall()
    return [{"type": r["type"], "count": r["count"]} for r in rows]


def get_type_fields(conn, node_type: str) -> list:
    rows = conn.execute(
        """
        SELECT p.`key` AS `key`, COUNT(DISTINCT n.id) AS freq
        FROM nodes n
        JOIN properties p ON p.node_id = n.id
        WHERE n.type = %s
        GROUP BY p.`key`
        ORDER BY freq DESC, p.`key` ASC
        """,
        (node_type,),
    ).fetchall()
    return [r["key"] for r in rows]


def get_link_labels(conn) -> list:
    rows = conn.execute(
        """
        SELECT label, COUNT(*) AS cnt
        FROM links
        WHERE label IS NOT NULL AND label != ''
        GROUP BY label
        ORDER BY cnt DESC, label ASC
        """
    ).fetchall()
    return [r["label"] for r in rows]


def search_nodes(conn, query: str) -> list:
    q = f"%{query}%"
    rows = conn.execute(
        """
        SELECT id, MIN(rank) AS rank FROM (
            SELECT n.id,
                   CASE
                     WHEN LOWER(n.name) = LOWER(%s) THEN 0
                     WHEN LOWER(n.name) LIKE LOWER(%s)  THEN 1
                     ELSE 2
                   END AS rank
            FROM nodes n
            WHERE LOWER(n.name) = LOWER(%s)
               OR LOWER(n.name) LIKE LOWER(%s)
            UNION ALL
            SELECT n.id, 3 AS rank
            FROM nodes n
            JOIN properties p ON p.node_id = n.id
            WHERE LOWER(p.value) LIKE LOWER(%s)
            UNION ALL
            SELECT n.id, 4 AS rank
            FROM nodes n
            JOIN links l ON l.source_id = n.id OR l.target_id = n.id
            JOIN nodes nb ON nb.id = CASE
                               WHEN l.source_id = n.id THEN l.target_id
                               ELSE l.source_id
                             END
            WHERE LOWER(nb.name) LIKE LOWER(%s)
        ) AS ranked
        GROUP BY id
        ORDER BY rank, id
        """,
        (query, q, query, q, q, q),
    ).fetchall()

    seen: set = set()
    results = []
    for r in rows:
        if r["id"] not in seen:
            seen.add(r["id"])
            node = _node_with_props(conn, r["id"])
            if node:
                results.append(node)
    return results


# ── session helpers (moved from main.py to keep SQL out of the API layer) ──

def session_get(conn) -> dict:
    row = conn.execute("SELECT focus_id, trail FROM session WHERE id = 1").fetchone()
    if not row:
        return {"focus_id": None, "trail": []}
    return {"focus_id": row["focus_id"], "trail": json.loads(row["trail"])}


def session_put(conn, focus_id: Optional[int], trail: list) -> None:
    conn.execute(
        """
        INSERT INTO session (id, focus_id, trail) VALUES (1, %s, %s)
        ON DUPLICATE KEY UPDATE focus_id = VALUES(focus_id), trail = VALUES(trail)
        """,
        (focus_id, json.dumps(trail)),
    )
    conn.commit()


def get_roots(conn, min_links: int, limit: int) -> list:
    rows = conn.execute(
        """
        SELECT n.id, n.name, n.type, COUNT(l.id) AS total
        FROM nodes n
        JOIN links l ON l.source_id = n.id OR l.target_id = n.id
        GROUP BY n.id, n.name, n.type
        HAVING total > %s
        ORDER BY total DESC
        LIMIT %s
        """,
        (min_links, limit),
    ).fetchall()
    return [{"id": r["id"], "name": r["name"], "type": r["type"], "link_count": r["total"]} for r in rows]
