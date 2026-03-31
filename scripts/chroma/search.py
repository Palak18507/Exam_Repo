"""
Semantic search against ChromaDB question vectors.
"""

from chroma.client import get_collection
from chroma.builder import get_model


def semantic_search(query, filters=None, top_k=10):
    """Search questions by meaning, not just keywords.

    Args:
        query: Natural language search string
        filters: Optional dict of ChromaDB where filters
                 e.g. {"department": "CSE"} or {"semester": 3}
        top_k: Number of results to return

    Returns:
        List of dicts with id, text, score, and metadata
    """
    model = get_model()
    embedding = model.encode([query]).tolist()

    kwargs = {
        "query_embeddings": embedding,
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }

    if filters:
        # ChromaDB needs non-empty filters
        clean_filters = {k: v for k, v in filters.items() if v}
        if clean_filters:
            kwargs["where"] = clean_filters

    results = get_collection().query(**kwargs)

    # Flatten into a clean list
    items = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 0
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity score: 1 = identical, 0 = unrelated
            similarity = max(0, 1 - distance / 2)

            items.append({
                "id": doc_id,
                "text": results["documents"][0][i] if results["documents"] else "",
                "similarity": round(similarity, 3),
                "paper_id": meta.get("paper_id", ""),
                "type": meta.get("type", ""),
                "subject_name": meta.get("subject_name", ""),
                "department": meta.get("department", ""),
                "semester": meta.get("semester", 0),
                "exam_type": meta.get("exam_type", ""),
                "academic_year": meta.get("academic_year", ""),
                "unit": meta.get("unit", ""),
            })

    return items


def find_similar(question_text, filters=None, top_k=10):
    """Find questions similar to a given question text."""
    return semantic_search(question_text, filters=filters, top_k=top_k)


def find_topic_clusters(filters, similarity_threshold=0.65, max_questions=200):
    """Cluster questions by topic similarity within a filter scope.

    Returns groups of questions that are about the same concept,
    even if worded differently. Used by Frequently Asked tab.

    Args:
        filters: ChromaDB where filters (e.g. {"subject_name": "DBMS"})
        similarity_threshold: Min cosine similarity to group (0.7 = 70%)
        max_questions: Max questions to fetch for clustering

    Returns:
        List of topic clusters, sorted by size (most frequent first).
        Each cluster: {topic_label, questions: [{id, text, paper_id, ...}], count}
    """
    import re
    import numpy as np

    model = get_model()

    # Get all questions matching the filter
    clean_filters = {k: v for k, v in filters.items() if v} if filters else {}

    get_kwargs = {
        "limit": max_questions,
        "include": ["documents", "metadatas", "embeddings"],
    }
    if clean_filters:
        get_kwargs["where"] = clean_filters

    try:
        data = get_collection().get(**get_kwargs)
    except Exception:
        return []

    if not data["ids"]:
        return []

    ids = data["ids"]
    docs = data["documents"]
    metas = data["metadatas"]
    embeddings = np.array(data["embeddings"])

    n = len(ids)
    if n < 2:
        return []

    # Compute pairwise cosine similarity matrix
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    sim_matrix = normalized @ normalized.T

    # Greedy clustering: pick the question with most similar neighbors
    assigned = [False] * n
    clusters = []

    # Score each question by how many neighbors it has above threshold
    neighbor_counts = [(sim_matrix[i] >= similarity_threshold).sum() for i in range(n)]
    order = sorted(range(n), key=lambda i: neighbor_counts[i], reverse=True)

    for center_idx in order:
        if assigned[center_idx]:
            continue

        # Find all unassigned questions similar to this one
        cluster_indices = [center_idx]
        assigned[center_idx] = True

        for j in range(n):
            if not assigned[j] and sim_matrix[center_idx][j] >= similarity_threshold:
                cluster_indices.append(j)
                assigned[j] = True

        if len(cluster_indices) < 2:
            continue  # Only show topics that appear 2+ times

        # Skip clusters with garbage/short labels
        center_doc = docs[center_idx]
        label_check = re.search(r"Question:\s*(.+?)\.\s*Concepts:", center_doc)
        label_preview = label_check.group(1).strip() if label_check else ""
        if len(label_preview) < 10:
            continue

        # Extract question text from the embedding document for the label
        center_doc = docs[center_idx]
        label_match = re.search(r"Question:\s*(.+?)\.\s*Concepts:", center_doc)
        topic_label = label_match.group(1) if label_match else center_doc[:100]

        questions = []
        for idx in cluster_indices:
            meta = metas[idx]
            doc = docs[idx]
            q_match = re.search(r"Question:\s*(.+?)\.\s*Concepts:", doc)
            q_text = q_match.group(1) if q_match else doc[:100]

            questions.append({
                "id": ids[idx],
                "text": q_text,
                "paper_id": meta.get("paper_id", ""),
                "subject_name": meta.get("subject_name", ""),
                "department": meta.get("department", ""),
                "academic_year": meta.get("academic_year", ""),
                "exam_type": meta.get("exam_type", ""),
                "unit": meta.get("unit", ""),
            })

        clusters.append({
            "topic_label": topic_label,
            "count": len(questions),
            "questions": questions,
        })

    # Sort by cluster size
    clusters.sort(key=lambda c: c["count"], reverse=True)
    return clusters
