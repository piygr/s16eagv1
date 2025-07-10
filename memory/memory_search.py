import json
import random
from pathlib import Path
from typing import List, Dict
from memory.memory_indexer import build_or_update_index, INDEX_BASE
from rapidfuzz import process, fuzz
import re
import spacy
nlp = spacy.load("en_core_web_sm")

def extract_named_entities(text: str) -> set:
    doc = nlp(text)
    return {ent.text.lower() for ent in doc.ents if ent.label_ in {"GPE", "ORG", "PERSON"}}

def normalize_query(text: str) -> str:
    text = re.sub(r"query\s*\d+:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower().strip()


class MemorySearch:
    def __init__(self):
        self.index_data = self.load_index()

    def load_index(self) -> List[Dict]:
        build_or_update_index()  # Ensure latest index
        all_entries = []
        for index_file in sorted(INDEX_BASE.glob("*.json")):
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                    valid_entries = [e for e in entries if isinstance(e, dict)]
                    all_entries.extend(valid_entries)
            except Exception as e:
                print(f"[ERROR] Failed to read {index_file}: {e}")
        return all_entries

    def search_memory(self, query: str, top_k: int = 3) -> List[Dict]:
        if not self.index_data:
            return []

        norm_query = normalize_query(query)
        query_ents = extract_named_entities(query)

        def hybrid_score(q1, q2, named_ents):
            score = fuzz.token_set_ratio(q1, q2)
            if query_ents & set(named_ents):
                score += 100  # NER boost
            return score

        candidates = [
            (entry["normalized_query"], entry["named_entities"])
            for entry in self.index_data
        ]

        scored = []
        for i, (norm_candidate, candidate_ents) in enumerate(candidates):
            score = hybrid_score(norm_query, norm_candidate, candidate_ents)
            scored.append((score, i))

        # Sort and filter by NER overlap
        scored.sort(reverse=True)
        top_matches = [
            (score, i) for (score, i) in scored
            if query_ents & set(self.index_data[i].get("named_entities", []))
        ][:top_k]

        if not top_matches:
            top_matches = scored[:top_k]

        return [
            {
                "score": score,
                "session_id": self.index_data[i].get("session_id"),
                "original_query": self.index_data[i].get("original_query"),
                "summary_output": self.index_data[i].get("summary_output"),
                "timestamp": self.index_data[i].get("timestamp")
            }
            for score, i in top_matches
        ]


if __name__ == "__main__":
    ms = MemorySearch()
    user_query = input("Enter your search query: ")
    results = ms.search_memory(user_query)
    for i, r in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(f"Session ID: {r['session_id']}")
        print(f"Original Query: {r['original_query']}")
        print(f"Timestamp: {r['timestamp']}")
        print(f"Summary: {r['summary_output'][:500]}...\n")
