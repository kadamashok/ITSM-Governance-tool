from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.incident import Incident


SIMILARITY_THRESHOLD = 0.80


@dataclass
class _Node:
    incident_id: int
    number: str
    short_description: str


def detect_and_store_duplicates(db: Session) -> dict[str, Any]:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except Exception as exc:
        raise RuntimeError("scikit-learn is not available in this environment") from exc

    incidents = db.execute(select(Incident).order_by(Incident.id.asc())).scalars().all()
    nodes = _build_nodes(incidents)

    if len(nodes) < 2:
        for incident in incidents:
            incident.duplicate_flag = False
            incident.duplicate_cluster_id = None
        db.commit()
        return {
            "success": True,
            "threshold": SIMILARITY_THRESHOLD,
            "total_incidents_scanned": len(incidents),
            "duplicate_clusters": [],
            "duplicate_count": 0,
        }

    corpus = [node.short_description for node in nodes]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(corpus)
    similarities = cosine_similarity(matrix)

    parent = list(range(len(nodes)))
    pair_links: list[dict[str, Any]] = []

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            score = float(similarities[i, j])
            if score > SIMILARITY_THRESHOLD:
                _union(parent, i, j)
                pair_links.append(
                    {
                        "incident_a": nodes[i].number,
                        "incident_b": nodes[j].number,
                        "similarity": round(score, 4),
                    }
                )

    groups: dict[int, list[int]] = {}
    for idx in range(len(nodes)):
        root = _find(parent, idx)
        groups.setdefault(root, []).append(idx)

    cluster_members = [members for members in groups.values() if len(members) > 1]
    cluster_members.sort(key=lambda c: min(nodes[idx].incident_id for idx in c))

    by_id = {incident.id: incident for incident in incidents}

    for incident in incidents:
        incident.duplicate_flag = False
        incident.duplicate_cluster_id = None

    response_clusters: list[dict[str, Any]] = []
    duplicate_count = 0

    for cluster_index, members in enumerate(cluster_members, start=1):
        member_payload: list[dict[str, Any]] = []
        for idx in members:
            node = nodes[idx]
            incident = by_id[node.incident_id]
            incident.duplicate_flag = True
            incident.duplicate_cluster_id = cluster_index
            duplicate_count += 1
            member_payload.append(
                {
                    "id": incident.id,
                    "number": node.number,
                    "short_description": node.short_description,
                }
            )

        response_clusters.append(
            {
                "cluster_id": cluster_index,
                "size": len(member_payload),
                "members": member_payload,
            }
        )

    db.commit()

    return {
        "success": True,
        "threshold": SIMILARITY_THRESHOLD,
        "total_incidents_scanned": len(incidents),
        "duplicate_count": duplicate_count,
        "pair_matches": pair_links,
        "duplicate_clusters": response_clusters,
    }


def _build_nodes(incidents: list[Incident]) -> list[_Node]:
    nodes: list[_Node] = []
    for incident in incidents:
        text = (incident.short_description or "").strip()
        if not text:
            continue
        nodes.append(
            _Node(
                incident_id=incident.id,
                number=incident.number,
                short_description=text,
            )
        )
    return nodes


def _find(parent: list[int], i: int) -> int:
    if parent[i] != i:
        parent[i] = _find(parent, parent[i])
    return parent[i]


def _union(parent: list[int], a: int, b: int) -> None:
    root_a = _find(parent, a)
    root_b = _find(parent, b)
    if root_a != root_b:
        parent[root_b] = root_a
