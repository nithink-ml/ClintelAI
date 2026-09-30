"""Document parsing, text cleaning, metadata extraction, and semantic chunking."""

import json
import re
from pathlib import Path

from app.rag.models import ClinicalDocument, EvidenceChunk


class DocumentParser:
    """Parses authoritative clinical guidelines and chunks them for vector indexing."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Cleans and normalizes clinical text."""
        if not text:
            return ""
        # Normalize multiple spaces, tabs, and newlines
        cleaned = re.sub(r"[\r\t]+", " ", text)
        cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned)
        cleaned = re.sub(r" +", " ", cleaned)
        return cleaned.strip()

    @staticmethod
    def extract_keywords(text: str, title: str, section_title: str) -> list[str]:
        """Extracts medical and operational keywords for hybrid lexical matching."""
        combined = f"{title} {section_title} {text}".lower()
        # Common clinical tokens to capture
        tokens = re.findall(r"\b[a-z0-9\-\+]{3,}\b", combined)
        
        # Stopwords filter
        stopwords = {
            "the", "and", "for", "with", "that", "this", "from", "are", "not",
            "have", "has", "had", "was", "were", "been", "will", "would", "should",
            "can", "could", "may", "might", "must", "shall", "into", "onto", "upon",
            "about", "above", "after", "again", "also", "any", "each", "other",
            "such", "than", "then", "their", "there", "these", "they", "them",
        }
        
        filtered = [t for t in tokens if t not in stopwords and not t.isdigit()]
        # Frequency count to return top distinct keywords
        freq: dict[str, int] = {}
        for token in filtered:
            freq[token] = freq.get(token, 0) + 1
        
        sorted_tokens = sorted(freq.keys(), key=lambda k: freq[k], reverse=True)
        return sorted_tokens[:15]

    @classmethod
    def chunk_document(cls, doc: ClinicalDocument, max_chunk_chars: int = 700, overlap_chars: int = 120) -> list[EvidenceChunk]:
        """Chunks document sections while preserving clinical context and metadata."""
        chunks: list[EvidenceChunk] = []
        chunk_idx = 1

        for section in doc.sections:
            clean_content = cls.clean_text(section.content)
            if not clean_content:
                continue

            # If section content is small enough, retain as single chunk
            if len(clean_content) <= max_chunk_chars:
                chunk_id = f"{doc.document_id}-chk-{chunk_idx:02d}"
                contextual_content = (
                    f"[{doc.source_name} | {doc.title} > {section.title}]\n{clean_content}"
                )
                keywords = cls.extract_keywords(clean_content, doc.title, section.title)
                chunks.append(
                    EvidenceChunk(
                        chunk_id=chunk_id,
                        document_id=doc.document_id,
                        source_name=doc.source_name,
                        authority_tier=doc.authority_tier,
                        title=doc.title,
                        section_title=section.title,
                        url=doc.url,
                        published_date=doc.published_date,
                        content=contextual_content,
                        keywords=keywords,
                    )
                )
                chunk_idx += 1
            else:
                # Split along sentence boundaries
                sentences = re.split(r"(?<=[.!?])\s+", clean_content)
                current_chunk = []
                current_len = 0

                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue

                    if current_len + len(sentence) > max_chunk_chars and current_chunk:
                        # Flush current chunk
                        chunk_text = " ".join(current_chunk)
                        chunk_id = f"{doc.document_id}-chk-{chunk_idx:02d}"
                        contextual_content = (
                            f"[{doc.source_name} | {doc.title} > {section.title}]\n{chunk_text}"
                        )
                        keywords = cls.extract_keywords(chunk_text, doc.title, section.title)
                        chunks.append(
                            EvidenceChunk(
                                chunk_id=chunk_id,
                                document_id=doc.document_id,
                                source_name=doc.source_name,
                                authority_tier=doc.authority_tier,
                                title=doc.title,
                                section_title=section.title,
                                url=doc.url,
                                published_date=doc.published_date,
                                content=contextual_content,
                                keywords=keywords,
                            )
                        )
                        chunk_idx += 1

                        # Retain overlap from end of previous chunk
                        overlap_tokens = []
                        running_overlap = 0
                        for s in reversed(current_chunk):
                            if running_overlap + len(s) < overlap_chars:
                                overlap_tokens.insert(0, s)
                                running_overlap += len(s)
                            else:
                                break
                        current_chunk = overlap_tokens + [sentence]
                        current_len = sum(len(s) for s in current_chunk) + len(current_chunk)
                    else:
                        current_chunk.append(sentence)
                        current_len += len(sentence) + 1

                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    chunk_id = f"{doc.document_id}-chk-{chunk_idx:02d}"
                    contextual_content = (
                        f"[{doc.source_name} | {doc.title} > {section.title}]\n{chunk_text}"
                    )
                    keywords = cls.extract_keywords(chunk_text, doc.title, section.title)
                    chunks.append(
                        EvidenceChunk(
                            chunk_id=chunk_id,
                            document_id=doc.document_id,
                            source_name=doc.source_name,
                            authority_tier=doc.authority_tier,
                            title=doc.title,
                            section_title=section.title,
                            url=doc.url,
                            published_date=doc.published_date,
                            content=contextual_content,
                            keywords=keywords,
                        )
                    )
                    chunk_idx += 1

        return chunks

    @classmethod
    def load_sources_from_directory(cls, dir_path: Path | str) -> tuple[list[ClinicalDocument], list[EvidenceChunk]]:
        """Loads and chunks all JSON source files from a directory."""
        directory = Path(dir_path)
        all_docs: list[ClinicalDocument] = []
        all_chunks: list[EvidenceChunk] = []

        if not directory.exists():
            return all_docs, all_chunks

        for json_file in sorted(directory.glob("*.json")):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            doc = ClinicalDocument(**item)
                            all_docs.append(doc)
                            chunks = cls.chunk_document(doc)
                            all_chunks.extend(chunks)
                    elif isinstance(data, dict):
                        doc = ClinicalDocument(**data)
                        all_docs.append(doc)
                        chunks = cls.chunk_document(doc)
                        all_chunks.extend(chunks)
            except Exception as e:
                print(f"Error parsing source file {json_file}: {e}")

        return all_docs, all_chunks
