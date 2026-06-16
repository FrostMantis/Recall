# Project Brief & Context Primer
### (a personal "summon-first" knowledge tool — name TBD)

> **If you are an AI reading this cold:** this document is the complete context for a project in **active build** — the design is settled and a working app already exists. Read all of it before responding. Treat the decisions below as decisions, not openings for debate. Do not reintroduce ideas marked as rejected (especially: no LLMs inside the tool, no *third-party* cloud — the owner's own homelab server is the data home, see §7 — and no browse-first UI). When a new design choice comes up, judge it against the north star in §1 and the constraints in §7. The person you're helping is the builder; match the working style in §3.

---

## 1. The one-sentence pitch (north star)

**A box you throw a word into, and it *summons* the thing you meant — and the cluster of related stuff around it lights up.** Browsing exists, but only on the side. The front door is search, not a folder tree you navigate.

The guiding test for every decision: ***does it serve the summon?***

The single most important framing: this is a tool you **summon** from, not a tool you **navigate**. That one distinction is the whole personality of the product and the reason existing tools (see §9) feel "close but not it."

---

## 2. What it's for (purpose)

A personal **recall** system. The driving need is not "organise everything" — it's ***stop losing knowledge you already had.*** Almost every motivating use case is phrased "I wish I knew…": where a file is, which PC runs which server, what mods a modpack had, how a thing was built, how to redo a procedure.

Representative real use cases from the owner:
- Where all my coding files live; which drive has which capacity and is still usable.
- Which PC stores my Minecraft creative server; what mods/plugins/version it runs.
- The procedure to push a new version of my CLI app; to update its backend on Proxmox; to update a dashboard.
- How I built my connected doorbell (documentation was bad — recover that knowledge).
- Which Linux apps replace which Windows apps.
- A modpack as a recoverable recipe of mods + versions.

It spans **digital and physical** things: files/folders, drives, loose CPUs in a drawer, whole PCs, servers, software projects, build procedures, hardware specs.

---

## 3. Who's building it / working style

- A solo technical hobbyist (homelab, Proxmox, Minecraft servers, IoT/ESP32, self-hosting). Comfortable "vibe-coding" with AI assistance.
- **Prefers concrete, example-driven reasoning** over abstract jargon. If a term is fuzzy, ground it in one of their real examples (chatcli, the gaming drive, a Minecraft server).
- **Dislikes over-engineering and manual busywork.** A feature that makes the user hand-configure each case (e.g., "list every app to detect") is considered a failure, because at that point they'd just do it by hand.
- **Values predictable, auditable, rule-based systems.** Has a firm stance against AI/LLMs making decisions inside the tool.
- Gets overwhelmed by too many open threads at once — introduce one decision at a time, keep momentum, don't dump.
- This design was developed slowly *on purpose* — the explicit goal was to get the idea fully clear **before** building, to avoid producing another polished-but-wrong tool (see §9, Landmark).

---

## 4. The data model (the core)

Everything reduces to **nodes** connected by **links**. That's it.

### Nodes ("things")
Every entity is a node of the same underlying kind: a folder, a drive, a CPU, a PC, a server, a software project, a procedure, a modpack — and even abstract things like "Minecraft" or a category. There is no privileged special-case entity (this is the key lesson from the failed PoC, which hardcoded "folder" as the only thing).

### Types
- Each node has a **type** (server, drive, procedure, project, …).
- A type carries a **template of default fields** — e.g. a new `server` arrives with blanks for name, version, type, main mods, players, date created.
- Fields are **optional/nullable** (leave blank when unknown) and **user-extensible** (add ad-hoc fields to any node).
- **Types accrete** — the user creates them as needed; there is no fixed master list defined up front. A type is just a reusable set of default fields. If the same ad-hoc field keeps getting added, that's a signal the template should grow (the template can learn from usage).

### Property sheet
- A node's fields are its description. **Values are mostly plain text** the user types. Deliberately low-ceremony — not everything needs to be structured.

### Links (edges)
Links connect nodes and are what form the "cluster" a summon reveals. They come in **three flavours — a guide, not a cage**:
1. **Where it lives** (containment/storage): a save is *in* a folder; a backup is *on* the NAS.
2. **One uses or serves the other** (functional): a server *runs on* a PC; an update note *is for* chatcli; a doorbell *talks to* a phone app. This is a **single directional relationship read from either end** — "the server uses the PC" and "the PC serves the server" are the same link; the label shown flips depending on which node you're standing on.
3. **What it's made of** (composition): a modpack *is* this list of mods at these versions.

Any link that doesn't fit neatly just carries its own **plain label** (e.g. *backup of*). Don't force a fourth flavour.

### The field-vs-link rule (important)
A detail becomes a **link** only if the far end **deserves to exist on its own and be summoned**. Otherwise it's just **text on the property sheet**.
- The PC a server runs on → its own node → a **link** (you'll summon the PC to ask "what runs on this?").
- The mod list → you just read it → **text field** (you don't want a standalone "create mod" hub; and text is still searchable, so you can still find "the server that had Create").

### Tags are just links
Tagging a node "Minecraft" *is* linking it to the Minecraft node. There is **no separate tag system** — a tag is just another node, and tagging is drawing an edge. "Everything tagged Minecraft" and "everything linked to the Minecraft node" are the same set, fetched the same way.

### Copies are just separate nodes
A thing that exists in several places (a save on the PC *and* on the NAS) is simply **several nodes, linked** (one a *backup of* another). This is intended, not a problem: recall *wants* to show that it lives in both spots. There is **no** single-source-of-truth / dedup / sync requirement — this is a recall tool, not a sync tool.

---

## 5. The interaction model

### Summon (the primary action)
- Type a **specific handle**, land on **one node**, and its cluster lights up *around* it.
- **The cluster is the result you get after landing — not the search query.** Typing a broad theme word ("Minecraft") to find one specific item is searching a self-made haystack and is the wrong mental model. You summon the specific thing; the related stuff comes along for free because it's linked.

### Retrieval when you don't know the exact name
Two supported paths:
- **Narrow by type:** "Minecraft servers" → a browsable list to scan.
- **Recall by neighbour/attribute:** "the server that had those mods." Search must match a node by its **name, its property text, AND its neighbours** — every node in a cluster is also a *handle into* it. (Search "Create" → get back the servers that ran it.)

### Navigate (browse-on-the-side)
- Click any neighbour to **move** onto it: it becomes the new centre and its own cluster opens.
- The node you came *from* stays a linked neighbour, so **"back" is free** — no separate history machinery needed conceptually.

### Depth vs breadth (why it never overwhelms)
- You **walk** the graph one hop at a time; you never render the whole thing.
- The view is a **shallow local window that moves with you.**
- Overwhelm comes from **breadth** (a node with many neighbours, like "Minecraft"), not depth. Wide nodes show their direct ring as a list you scan (and can be tamed by filtering that ring by type); narrow/tidy nodes (like chatcli) can show a few hops deep comfortably.

---

## 6. Capture (getting things in)

### Manual creation
- Adding a thing is **just a creation form** driven by the node's type template.
- **Links are the thing that makes the tool work** — a node nothing links to never appears in any cluster and is effectively invisible. So link-creation friction is the critical risk.
- Mitigation: **create nodes in context** — when you're on chatcli and hit "add backup," that link to chatcli is made for free.

### The suggester (bulk import, e.g. pointing it at a whole drive)
A built-in helper that **proposes nodes/links**, under a hard rule: **rules/heuristics only, NEVER an LLM.**

The rules must read **shape, not names** (no allowlist of known apps/games — that's the failure mode, see §9):
- **Look-alike detection:** if a folder's children are structurally similar (e.g. 40 sibling folders each holding an `.exe`, similar layout/size), the *sameness itself* signals "a library of ~40 peer things" → offer all of them. No need to recognise any specific game.
- **Generic "self-contained thing" markers:** `.exe`, `.git`, a save folder, a manifest — any folder carrying one is probably its own node, whatever it's named.

Governing principle: **optimise for recall, not precision — over-offer and let the user cull.** A false positive costs one click to dismiss; a missed folder defeats the entire tool. Therefore culling must be fast (bulk-reject, "ignore everything under here").

The **specific** rules (thresholds, exact markers, aggressiveness) are deliberately **deferred to build time** and tuned against the owner's real drives. They must not be invented in the abstract — doing so blind is exactly how the PoC's rules became useless.

---

## 7. Hard constraints (non-negotiable)

1. **Self-hosted on the owner's own infrastructure — no third-party cloud.** Data lives in the owner's **MariaDB instance running 24/7 in a Proxmox container** on their home network, so it's reachable from any machine in the house. "Local-first" was the original framing; the accurate framing is **homelab-first** — the owner's own server, never someone else's cloud. (The app therefore depends on that server being reachable; it is a LAN tool, not an offline-anywhere tool. This was a deliberate, eyes-open choice.)
2. **Three detached layers, and they stay detached.** (a) A **web frontend** that talks *only* to the backend's HTTP API and knows nothing about the database. (b) A **backend service** (Python/FastAPI) that can be run on any machine and owns all logic. (c) The **MariaDB** database. The frontend must never need to change when the database changes — the data layer (`db.py`/`ops.py`) is the only thing that knows what the DB is. This separation is load-bearing and must be preserved.
3. **No LLMs anywhere in the tool's runtime** — above all, never for deciding links or detecting nodes. All such intelligence is rules / heuristics / algorithms. This is a firm value (predictability + auditability), not a preference to negotiate.
4. **Single user, multiple machines.** One person, but reachable from several of their own devices on the home network. No multi-tenant / collaboration / accounts requirements.
5. **Must read the owner's drives** for the capture suggester (it scans real folders on the machine the backend runs on).

> Note for a cold reader: an earlier version of this brief said "local-first, SQLite, no cloud." That has been superseded. Storage is **MariaDB on the homelab**; the frontend stays detached behind the API; the backend is portable. Do **not** "helpfully" revert this to a local SQLite file — the homelab DB is the whole point of being able to reach the data from any machine.

---

## 8. Design philosophy (the vibe)

- **Summon over browse.** Retrieval-by-association is the soul of the tool.
- **One domain-agnostic kernel.** Don't build per-domain features (a "file module," a "hardware module"). There is one model — nodes, types, property sheets, links — and every use case (file indexing, hardware inventory, procedures, servers) is just *data on that kernel*. Get the kernel right and every new use case is nearly free.
- **Capture friction is the silent killer.** Minimise effort to add things and especially to create links. When in doubt, over-suggest.
- **Recall, not organisation or sync.** It helps you find what you already have; it is not a file manager, not a sync engine, not an everything-organiser.
- **Predictable beats clever.** Rule-based and inspectable over opaque and "smart."

---

## 9. What this is NOT (anti-patterns from real reference points)

- **Not "Landmark"** (the owner's abandoned proof-of-concept). Its failures, all to avoid:
  - Files-only; "folder" was hardcoded as the sole entity (every item required a filesystem path). The new model treats a folder as just one *type* of node.
  - **Browse-first** UI (a tagged sidebar you walk through) instead of summon-first.
  - A scanner built on an **allowlist** of known patterns — it found ~2 useful folders on an entire drive (massive under-recall) and could only ever find things someone pre-taught it. Extending it meant manually naming every app, i.e. the same labour as tagging by hand. This is the canonical mistake the new suggester must not repeat.
- **Not Anytype / Tana / Notion-style tools** — structured object workspaces you **build and organise in**.
- **The unifying flaw of all the above:** they are tools you *navigate*. This is a tool you *summon*.

---

## 10. Status — settled vs open

**Settled (do not reopen):** the entire data model (§4), the interaction model (§5), the capture *principles* (§6), and all hard constraints (§7). **The stack is now decided and built:** Python + **FastAPI** backend, **MariaDB** storage (on the homelab, §7), a plain **HTML/JS frontend** (no build step) wrapped in a **pywebview** desktop window, talking to the backend over local HTTP. CRUD, summon/search, the cluster view, learned property-templates and link-labels, and home-screen "hub" nodes are all built.

**Open / next:**
- The **specific detection rules** for the capture suggester — still deferred, tuned against real drives once there's real data in the system.
- **Living in it with real data** — the current priority. The tool is complete enough to use; real use is what should drive what gets built next.
- Tuning knobs already identified (all to be set against real data, not guessed): the home-screen link-count threshold, and a future min-occurrence threshold for template/label suggestions to filter one-off typos.

---

## 11. If you're an AI being asked to help build or extend this

- Respect §7 absolutely. Never propose an LLM-driven feature inside the tool, a *third-party* cloud backend (the owner's own homelab MariaDB is the intended data home — see §7), or a browse-first redesign.
- Anchor explanations in the owner's real examples; avoid abstract jargon; introduce one decision at a time.
- For any new feature, ask: *does it serve the summon? does it add capture friction? does it over- or under-offer?*
- Prefer simple, local, rule-based, inspectable solutions. Predictable over clever.
- The model is a property-graph at heart (typed nodes + labelled directional edges + per-node property sheets), but the user thinks in "things, clusters, summon" — speak that language.
