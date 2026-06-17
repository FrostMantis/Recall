from contextlib import asynccontextmanager
from typing import Annotated, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import get_db, init_db
from ops import (
    create_node, update_node, delete_node,
    get_node_with_neighbours, search_nodes,
    link_nodes, delete_link, get_type_fields, get_types, get_link_labels,
    session_get, session_put, get_roots, get_graph,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Recall", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── request models ────────────────────────────────────────────────────────────

class NodeCreate(BaseModel):
    name: str
    type: str = "thing"
    properties: dict[str, str] = {}


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    # values may be None to delete a key, str to upsert
    properties: Optional[dict[str, Optional[str]]] = None


class LinkCreate(BaseModel):
    source_id: int
    target_id: int
    label: Optional[str] = None


# ── read endpoints ────────────────────────────────────────────────────────────

@app.get("/search")
def search(q: Annotated[str, Query(min_length=1)]):
    with get_db() as conn:
        results = search_nodes(conn, q)
    return {"query": q, "results": results}


@app.get("/types")
def types_list():
    with get_db() as conn:
        return {"types": get_types(conn)}


@app.get("/types/{type}/fields")
def type_fields(type: str):
    with get_db() as conn:
        fields = get_type_fields(conn, type)
    return {"type": type, "fields": fields}


ROOTS_MIN_LINKS = 2
ROOTS_LIMIT     = 8

@app.get("/graph")
def graph():
    with get_db() as conn:
        return get_graph(conn)


@app.get("/roots")
def roots():
    with get_db() as conn:
        return {"roots": get_roots(conn, ROOTS_MIN_LINKS, ROOTS_LIMIT)}


@app.get("/nodes/{node_id}")
def node_detail(node_id: int):
    with get_db() as conn:
        node = get_node_with_neighbours(conn, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


# ── write endpoints ───────────────────────────────────────────────────────────

@app.post("/nodes", status_code=201)
def node_create(body: NodeCreate):
    with get_db() as conn:
        node = create_node(conn, body.name, body.type)
        for key, value in body.properties.items():
            from ops import set_property
            set_property(conn, node["id"], key, value)
        # Return with neighbours (empty at creation)
        return get_node_with_neighbours(conn, node["id"])


@app.patch("/nodes/{node_id}")
def node_update(node_id: int, body: NodeUpdate):
    with get_db() as conn:
        existing = get_node_with_neighbours(conn, node_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Node not found")
        updated = update_node(
            conn,
            node_id,
            name=body.name,
            node_type=body.type,
            properties=body.properties,
        )
    return updated


@app.delete("/nodes/{node_id}")
def node_delete(node_id: int):
    with get_db() as conn:
        existing = get_node_with_neighbours(conn, node_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Node not found")
        links_removed = delete_node(conn, node_id)
    return {"deleted": True, "links_removed": links_removed}


class SessionSave(BaseModel):
    focus_id: Optional[int] = None
    trail: list[dict] = []


@app.get("/session")
def session_get_route():
    with get_db() as conn:
        return session_get(conn)


@app.put("/session", status_code=204)
def session_put_route(body: SessionSave):
    with get_db() as conn:
        session_put(conn, body.focus_id, body.trail)
    return None


@app.get("/links/labels")
def link_labels():
    with get_db() as conn:
        return {"labels": get_link_labels(conn)}


@app.post("/links", status_code=201)
def link_create(body: LinkCreate):
    with get_db() as conn:
        for nid in (body.source_id, body.target_id):
            if not conn.execute("SELECT 1 FROM nodes WHERE id = %s", (nid,)).fetchone():
                raise HTTPException(status_code=404, detail=f"Node {nid} not found")
        link = link_nodes(conn, body.source_id, body.target_id, "other", body.label)
    return link


@app.delete("/links/{link_id}")
def link_delete(link_id: int):
    with get_db() as conn:
        removed = delete_link(conn, link_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"deleted": True}
