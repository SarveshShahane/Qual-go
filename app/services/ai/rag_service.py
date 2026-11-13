import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.ai_tutor import AISourceReference


@dataclass
class RAGDocumentChunk:
    chunk_id: str
    module_id: str
    module_name: str
    chapter_id: str
    chapter_name: str
    title: str
    content: str
    token_set: Set[str]
    term_frequencies: Dict[str, float]


class RAGService:
    """
    In-memory, grounded Retrieval-Augmented Generation service indexing QualGo's
    learning curriculum (Mathematics, Qubits, Superposition, Algorithms, Gates).
    Supports tokenized BM25/TF-IDF similarity ranking and source citation extraction.
    """

    def __init__(self, modules_dir: Optional[str] = None):
        if modules_dir:
            self.modules_dir = Path(modules_dir)
        else:
            # Auto-detect modules folder in repository
            backend_dir = Path(__file__).resolve().parent.parent.parent.parent
            candidate_1 = backend_dir / "modules"
            candidate_2 = backend_dir.parent / "modules"
            self.modules_dir = candidate_1 if candidate_1.exists() else candidate_2

        self.chunks: List[RAGDocumentChunk] = []
        self.doc_frequencies: Dict[str, int] = {}
        self.num_docs: int = 0
        self._is_indexed = False
        self._index_curriculum()

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s\+\-\*\/\^\|\>\<\\]", " ", text.lower())
        tokens = [t for t in cleaned.split() if len(t) > 1]
        return tokens

    def _index_curriculum(self) -> None:
        if not self.modules_dir.exists():
            return

        raw_chunks: List[Tuple[str, str, str, str, str, str]] = []

        # Recursively scan markdown files in modules
        for md_file in self.modules_dir.rglob("*.md"):
            try:
                rel_path = md_file.relative_to(self.modules_dir)
                parts = rel_path.parts
                if not parts:
                    continue

                module_name = parts[0]
                module_id = module_name.lower().replace(" ", "-")

                chapter_name = parts[1] if len(parts) > 1 else "Overview"
                chapter_id = chapter_name.lower().replace(" ", "-")

                file_type = md_file.stem  # e.g., 'theory', 'README', 'questions'

                content = md_file.read_text(encoding="utf-8", errors="ignore")
                sections = re.split(r"\n(?=#{1,3}\s+)", content)

                for sec_idx, section in enumerate(sections):
                    trimmed = section.strip()
                    if not trimmed or len(trimmed) < 40:
                        continue

                    # Extract section heading
                    first_line = trimmed.split("\n")[0]
                    title_match = re.match(r"^#{1,3}\s+(.+)$", first_line)
                    title = title_match.group(1).strip() if title_match else f"{chapter_name} ({file_type})"

                    raw_chunks.append((
                        module_id,
                        module_name,
                        chapter_id,
                        chapter_name,
                        title,
                        trimmed,
                    ))
            except Exception:
                continue

        self.num_docs = len(raw_chunks)
        self.doc_frequencies.clear()
        self.chunks.clear()

        for idx, (m_id, m_name, c_id, c_name, title, text) in enumerate(raw_chunks):
            tokens = self._tokenize(text + " " + title + " " + c_name)
            token_set = set(tokens)
            term_freqs: Dict[str, float] = {}

            for tok in tokens:
                term_freqs[tok] = term_freqs.get(tok, 0.0) + 1.0

            # Normalize term frequencies
            total_tokens = max(1, len(tokens))
            for tok in term_freqs:
                term_freqs[tok] /= total_tokens

            for tok in token_set:
                self.doc_frequencies[tok] = self.doc_frequencies.get(tok, 0) + 1

            self.chunks.append(RAGDocumentChunk(
                chunk_id=f"chunk_{idx}",
                module_id=m_id,
                module_name=m_name,
                chapter_id=c_id,
                chapter_name=c_name,
                title=title,
                content=text,
                token_set=token_set,
                term_frequencies=term_freqs,
            ))

        self._is_indexed = True

    def search(
        self,
        query: str,
        top_k: int = 3,
        module_filter: Optional[str] = None,
    ) -> List[Tuple[RAGDocumentChunk, float, AISourceReference]]:
        """
        Retrieves top_k relevant curriculum chunks matching query using TF-IDF scoring.
        """
        if not self._is_indexed or not self.chunks:
            self._index_curriculum()

        if not self.chunks:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores: List[Tuple[RAGDocumentChunk, float]] = []

        for chunk in self.chunks:
            if module_filter and module_filter.lower() not in chunk.module_id.lower():
                continue

            score = 0.0
            for q_tok in query_tokens:
                if q_tok in chunk.term_frequencies:
                    tf = chunk.term_frequencies[q_tok]
                    df = self.doc_frequencies.get(q_tok, 1)
                    idf = math.log((self.num_docs + 1.0) / (df + 0.5)) + 1.0
                    score += tf * idf

            if score > 0.0:
                scores.append((chunk, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        top_results = scores[:top_k]

        results_with_sources: List[Tuple[RAGDocumentChunk, float, AISourceReference]] = []
        for chunk, s in top_results:
            snippet = chunk.content[:280].strip().replace("\n", " ") + "..."
            source_ref = AISourceReference(
                module_id=chunk.module_id,
                module_name=chunk.module_name,
                chapter_id=chunk.chapter_id,
                chapter_name=chunk.chapter_name,
                snippet=snippet,
            )
            results_with_sources.append((chunk, s, source_ref))

        return results_with_sources

    def format_context_for_prompt(
        self,
        query: str,
        top_k: int = 3,
        module_filter: Optional[str] = None,
    ) -> Tuple[str, List[AISourceReference]]:
        """
        Builds grounded context block for LLM prompt and extracts sources.
        """
        results = self.search(query, top_k=top_k, module_filter=module_filter)
        if not results:
            return "", []

        context_blocks = []
        sources: List[AISourceReference] = []

        for chunk, score, src in results:
            sources.append(src)
            context_blocks.append(
                f"[Source: {chunk.module_name} > {chunk.chapter_name} - {chunk.title}]\n{chunk.content}"
            )

        full_context = "\n\n---\n\n".join(context_blocks)
        return full_context, sources


# Global singleton instance
rag_service = RAGService()
