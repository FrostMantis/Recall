"""
Seed the chatcli cluster.

chatcli (project)
  ├─ runs on    → homelab-pc (server)
  ├─ backend    → proxmox-vm-chatcli (server)
  ├─ update procedure → chatcli-deploy-procedure (procedure)
  ├─ tagged     → Python (tag)
  └─ tagged     → CLI (tag)

proxmox-vm-chatcli
  ├─ lives in   → proxmox-host (server)
  └─ tagged     → Proxmox (tag)
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from db import get_db, init_db
from ops import create_node, get_or_create_node, link_nodes, set_property


def seed():
    init_db()
    conn = get_db()

    # ── core project node ──────────────────────────────────────────────
    chatcli = get_or_create_node(conn, "chatcli", "project")
    set_property(conn, chatcli["id"], "description", "Personal CLI chat app backed by an LLM API")
    set_property(conn, chatcli["id"], "language", "Python")
    set_property(conn, chatcli["id"], "repo", "/mnt/projects-sys2/Coding/chatcli")
    set_property(conn, chatcli["id"], "status", "active")

    # ── the PC it runs on locally ──────────────────────────────────────
    homelab_pc = get_or_create_node(conn, "homelab-pc", "pc")
    set_property(conn, homelab_pc["id"], "description", "Main homelab desktop, runs dev builds")
    set_property(conn, homelab_pc["id"], "os", "Nobara Linux")

    link_nodes(conn, chatcli["id"], homelab_pc["id"], flavour="uses_serves",
               label="runs on (dev)")

    # ── Proxmox VM that hosts the backend ─────────────────────────────
    proxmox_vm = get_or_create_node(conn, "proxmox-vm-chatcli", "server")
    set_property(conn, proxmox_vm["id"], "description", "LXC/VM on Proxmox serving chatcli backend")
    set_property(conn, proxmox_vm["id"], "ip", "192.168.1.50")
    set_property(conn, proxmox_vm["id"], "port", "8080")

    link_nodes(conn, chatcli["id"], proxmox_vm["id"], flavour="uses_serves",
               label="backend runs on")

    # ── Proxmox host ───────────────────────────────────────────────────
    proxmox_host = get_or_create_node(conn, "proxmox-host", "server")
    set_property(conn, proxmox_host["id"], "description", "Bare-metal Proxmox hypervisor")
    set_property(conn, proxmox_host["id"], "ip", "192.168.1.10")

    link_nodes(conn, proxmox_vm["id"], proxmox_host["id"], flavour="lives_in",
               label="hosted on")

    # ── deploy procedure ───────────────────────────────────────────────
    deploy_proc = get_or_create_node(conn, "chatcli-deploy-procedure", "procedure")
    set_property(conn, deploy_proc["id"], "steps",
        "1. bump version in pyproject.toml  "
        "2. git tag vX.Y.Z && git push --tags  "
        "3. SSH into proxmox-vm-chatcli  "
        "4. cd /opt/chatcli && git pull  "
        "5. systemctl restart chatcli")
    set_property(conn, deploy_proc["id"], "last_run", "2026-05-10")

    link_nodes(conn, deploy_proc["id"], chatcli["id"], flavour="uses_serves",
               label="deploy procedure for")

    # ── tags (tag-nodes) ──────────────────────────────────────────────
    for tag_name in ("Python", "CLI", "self-hosted"):
        tag = get_or_create_node(conn, tag_name, "tag")
        link_nodes(conn, chatcli["id"], tag["id"], flavour="other", label="tagged")

    proxmox_tag = get_or_create_node(conn, "Proxmox", "tag")
    link_nodes(conn, proxmox_vm["id"], proxmox_tag["id"], flavour="other", label="tagged")

    conn.close()
    print("Seeded chatcli cluster.")


if __name__ == "__main__":
    seed()
