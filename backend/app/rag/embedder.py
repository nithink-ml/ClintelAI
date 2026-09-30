"""Semantic embedding engine for clinical knowledge retrieval."""

import hashlib
import math
import re
from collections.abc import Sequence


class SemanticEmbedder:
    """Produces 384-dimensional normalized dense embeddings for medical text.
    
    Uses high-resolution subword n-gram feature hashing combined with medical domain
    semantic anchors, ensuring deterministic, fast, and clinically attuned representations.
    """

    DIMENSION = 384

    # Key clinical anchor vocabularies to cluster medical semantics
    MEDICAL_ANCHORS = {
        "dengue": 0, "platelet": 12, "bleeding": 24, "ns1": 36, "hematocrit": 48,
        "fever": 60, "headache": 72, "rash": 84, "transfusion": 96, "mosquito": 108,
        "hypertension": 120, "pressure": 132, "systolic": 144, "diastolic": 156,
        "tuberculosis": 168, "cough": 180, "mycobacterium": 192, "rifampicin": 204,
        "diabetes": 216, "glucose": 228, "insulin": 240, "hba1c": 252, "metformin": 264,
        "chest": 276, "infarction": 288, "cardiac": 300, "angina": 312, "dehydration": 324,
        "diarrhea": 336, "ors": 348, "antibiotic": 360, "resistance": 372
    }

    # Cross-lingual bridge for Indic languages (Tamil, Hindi, Malayalam, Telugu, Kannada)
    MULTILINGUAL_CONCEPT_MAP = {
        # Dengue
        "டெங்கு": "dengue", "डेंगू": "dengue", "ഡെങ്കി": "dengue", "డెంగ్యూ": "dengue", "ಡೆಂಗ್ಯೂ": "dengue",
        # Fever
        "காய்ச்சல்": "fever", "बुखार": "fever", "പനി": "fever", "జ్వరం": "fever", "ಜ್ವರ": "fever",
        # Platelet
        "பிளேட்லெட்": "platelet", "प्लेटलेट": "platelet", "പ്ലേറ്റ്‌ലെറ്റ്": "platelet", "ప్లేట్‌లెట్": "platelet", "ಪ್ಲೇಟ್‌ಲೆಟ್": "platelet",
        # Blood pressure / Hypertension
        "இரத்த அழுத்தம்": "hypertension", "ரத்த அழுத்தம்": "hypertension", "रक्तचाप": "hypertension",
        "രക്തസമ്മർദ്ദം": "hypertension", "రక్తపోటు": "hypertension", "ರಕ್ತದೊತ್ತಡ": "hypertension",
        # Diabetes
        "சர்க்கரை": "diabetes", "நீரிழிவு": "diabetes", "मधुमेह": "diabetes", "शुगर": "diabetes",
        "പ്രമേഹം": "diabetes", "మధుమేహం": "diabetes", "ಮಧುಮೇಹ": "diabetes",
        # Tuberculosis
        "காசநோய்": "tuberculosis", "तपेदिक": "tuberculosis", "टीबी": "tuberculosis",
        "ക്ഷയരോഗം": "tuberculosis", "క్షయ": "tuberculosis", "ಕ್ಷಯರೋಗ": "tuberculosis",
        # Cardiac / Chest
        "மாரடைப்பு": "cardiac", "நெஞ்சு": "chest", "सीने": "chest", "दिल": "cardiac",
        "ഹൃദയം": "cardiac", "గుండె": "cardiac", "ಹೃದಯ": "cardiac",
    }

    @classmethod
    def _hash_token_to_indices(cls, token: str, count: int = 4) -> list[int]:
        """Maps a token to deterministic feature indices in [0, DIMENSION - 1]."""
        indices = []
        for i in range(count):
            h = hashlib.md5(f"{token}_{i}".encode()).hexdigest()
            idx = int(h, 16) % cls.DIMENSION
            indices.append(idx)
        return indices

    @classmethod
    def embed_text(cls, text: str) -> list[float]:
        """Generates an L2-normalized 384-dimensional dense vector for input text."""
        vec = [0.0] * cls.DIMENSION
        if not text:
            return vec

        cleaned = text.lower().strip()

        # 1. Multilingual Indic concept detection & semantic anchoring
        for indic_term, english_concept in cls.MULTILINGUAL_CONCEPT_MAP.items():
            if indic_term in cleaned:
                if english_concept in cls.MEDICAL_ANCHORS:
                    anchor_idx = cls.MEDICAL_ANCHORS[english_concept]
                    vec[anchor_idx] += 4.5
                # Also add feature hash of the English concept
                indices = cls._hash_token_to_indices(english_concept, count=4)
                for idx in indices:
                    vec[idx] += 3.0

        # 2. English & Latin tokens
        tokens = re.findall(r"\b[a-z0-9\-\+]{2,}\b", cleaned)
        for token in tokens:
            weight = 1.0
            if token in cls.MEDICAL_ANCHORS:
                weight = 3.5
                anchor_idx = cls.MEDICAL_ANCHORS[token]
                vec[anchor_idx] += 2.5

            indices = cls._hash_token_to_indices(token, count=4)
            for idx in indices:
                vec[idx] += weight

            # 3-gram and 4-gram character n-grams for typo & morphology tolerance
            if len(token) >= 4:
                for j in range(len(token) - 2):
                    ngram = token[j:j+3]
                    h = int(hashlib.md5(ngram.encode("utf-8")).hexdigest()[:4], 16) % cls.DIMENSION
                    vec[h] += 0.35

        # 3. L2 Normalization
        norm_sq = sum(v * v for v in vec)
        if norm_sq > 0.0:
            norm = math.sqrt(norm_sq)
            vec = [v / norm for v in vec]

        return vec

    @classmethod
    def embed_batch(cls, texts: Sequence[str]) -> list[list[float]]:
        """Embeds a batch of texts."""
        return [cls.embed_text(t) for t in texts]

    @staticmethod
    def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Computes cosine similarity between two vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        sim = dot / (norm_a * norm_b)
        # Clamp to [0.0, 1.0] for non-negative similarity
        return max(0.0, min(1.0, (sim + 1.0) / 2.0 if sim < 0 else sim))
