from __future__ import annotations
import re
import math
from collections import Counter
from typing import Dict, List, Optional, Tuple, Set
import textstat
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

try:
    import language_tool_python
    _LT = language_tool_python.LanguageToolPublicAPI('en-US')
except Exception:
    _LT = None

try:
    import spacy
    _NLP = spacy.load("en_core_web_sm")
except Exception:
    _NLP = None

# WordNet for intelligent uncountable noun detection (no hardcoding)
try:
    from nltk.corpus import wordnet as wn
    _ABSTRACT_LEXNAMES = {
        'noun.state', 'noun.feeling', 'noun.cognition', 'noun.act',
        'noun.attribute', 'noun.phenomenon', 'noun.communication', 'noun.process',
    }
    _WN_AVAILABLE = True
except Exception:
    _WN_AVAILABLE = False

# Sentence-transformers for semantic topic relevance (loaded once at startup)
try:
    from sentence_transformers import SentenceTransformer, util as st_util
    _ST_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    _ST_AVAILABLE = True
except Exception:
    _ST_MODEL = None
    _ST_AVAILABLE = False

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import os

_ANALYZER = SentimentIntensityAnalyzer()
ML_MODEL_PATH = os.path.join(os.path.dirname(__file__), "ml", "essay_scorer.pkl")
_wn_cache: Dict[str, bool] = {}


def _is_uncountable(word: str) -> bool:
    if not _WN_AVAILABLE:
        return False
    word = word.lower()
    if word in _wn_cache:
        return _wn_cache[word]
    syns = wn.synsets(word, pos=wn.NOUN)
    if not syns:
        _wn_cache[word] = False
        return False
    lexnames = [s.lexname() for s in syns]
    abstract_count = sum(1 for l in lexnames if l in _ABSTRACT_LEXNAMES)
    result = abstract_count >= len(lexnames) * 0.5
    _wn_cache[word] = result
    return result


def readability_metrics(text: str) -> Dict[str, float]:
    if not text or len(text.split()) < 5:
        return {"flesch": 0.0, "grade_level": 0.0, "readability_score": 0.0}
    flesch = textstat.flesch_reading_ease(text)
    grade = textstat.text_standard(text, float_output=True)
    if grade <= 4:
        grade_score = max(10.0, grade / 4.0 * 50.0)
    elif grade <= 10:
        grade_score = 50.0 + (grade - 4) / 6.0 * 43.0
    elif grade <= 14:
        grade_score = 93.0 + (grade - 10) / 4.0 * 2.0
    else:
        grade_score = max(70.0, 95.0 - (grade - 14) * 3.0)
    flesch_scaled = max(0.0, min(100.0, flesch))
    readability = round(0.8 * grade_score + 0.2 * flesch_scaled, 2)
    return {
        "flesch": round(flesch, 2),
        "grade_level": round(grade, 2),
        "readability_score": round(readability, 2),
    }


def sentiment_score(text: str) -> Dict[str, float]:
    if not text or len(text.split()) < 3:
        return {"compound": 0.0, "positivity": 50.0}
    s = _ANALYZER.polarity_scores(text)
    comp = s["compound"]
    positivity = round((comp + 1) * 50, 2)
    return {"compound": round(comp, 3), "positivity": positivity}


def _spacy_grammar_issues(text: str) -> List[Dict[str, str]]:
    if _NLP is None:
        return []

    issues = []
    doc = _NLP(text)
    sentences = list(doc.sents)

    # 1. Sentences not starting with capital letter
    no_cap = [s for s in sentences if s.text.strip() and s.text.strip()[0].islower()]
    if no_cap:
        issues.append({
            "message": f"{len(no_cap)} sentence(s) do not start with a capital letter",
            "context": no_cap[0].text.strip()[:50],
            "suggest": "Capitalise the first word of every sentence"
        })

    # 2. First-person pronoun 'i' not capitalised
    i_tokens = [t for t in doc if t.text == 'i' and t.pos_ == 'PRON']
    if i_tokens:
        issues.append({
            "message": f"First-person pronoun 'i' used {len(i_tokens)} time(s) without capitalisation",
            "context": "Should always be written as 'I'",
            "suggest": "Replace all instances of 'i' with 'I'"
        })

    # 3. Subject-verb agreement
    sv_errors = []
    for token in doc:
        if token.dep_ == "nsubj" and token.head.pos_ == "VERB":
            subj_morph = token.morph.get("Number")
            verb_morph = token.head.morph.get("Number")
            if subj_morph and verb_morph and subj_morph != verb_morph:
                sv_errors.append(f"'{token.text} {token.head.text}'")
    if sv_errors:
        issues.append({
            "message": f"Subject-verb agreement error(s): {', '.join(sv_errors[:4])}",
            "context": "Verb form does not match its subject",
            "suggest": "Match the verb number to its subject"
        })

    # 4. Missing article before singular countable noun (WordNet-based)
    missing_det = []
    for token in doc:
        if (token.pos_ == "NOUN"
                and token.morph.get("Number") == ["Sing"]
                and token.dep_ in ("dobj",)
                and not any(c.dep_ in ("det", "poss", "nummod", "amod") for c in token.children)
                and not token.is_upper
                and len(token.text) > 3
                and not _is_uncountable(token.lemma_)
                and not (
                    token.head.pos_ == "VERB"
                    and not any(c.dep_ in ("det", "amod", "relcl", "prep") for c in token.children)
                    and any(
                        c.dep_ == "prep" and c.lower_ in ("to", "at", "in", "into", "from")
                        for c in token.head.children
                    )
                )):
            missing_det.append(token.text)
    if missing_det:
        issues.append({
            "message": f"Possible missing article before: {', '.join(set(missing_det[:3]))}",
            "context": "Singular countable nouns usually need 'a', 'an', or 'the'",
            "suggest": "Add an appropriate article before the noun"
        })

    # 5. Consecutive duplicate words
    consec = []
    for i in range(len(doc) - 1):
        if doc[i].lower_ == doc[i+1].lower_ and doc[i].is_alpha:
            consec.append(doc[i].text)
    if consec:
        issues.append({
            "message": f"Consecutive duplicate word(s): {', '.join(set(consec[:4]))}",
            "context": "Same word appears back to back",
            "suggest": "Remove the duplicate word"
        })

    # 6. Circular phrasing (3-token window)
    tokens_lower = [t.lower_ for t in doc if t.is_alpha]
    circular = []
    for i in range(len(tokens_lower) - 2):
        if (tokens_lower[i] == tokens_lower[i + 2]
                and len(tokens_lower[i]) > 3
                and not doc[i].is_stop):
            circular.append(tokens_lower[i])
    if circular:
        issues.append({
            "message": f"Circular/tautological phrasing: {', '.join(set(circular[:4]))}",
            "context": "e.g. 'reading is reading' — says nothing meaningful",
            "suggest": "Replace with a real explanation or evidence"
        })

    # 7. Severely overused content words
    content_tokens = [t.lower_ for t in doc if t.is_alpha and not t.is_stop and len(t.text) > 3]
    total = len(content_tokens)
    if total > 0:
        wc = Counter(content_tokens)
        overused = [(w, c) for w, c in wc.items() if c / total > 0.12]
        if overused:
            overused_str = ', '.join(
                f"'{w}'×{c}" for w, c in sorted(overused, key=lambda x: -x[1])[:4]
            )
            issues.append({
                "message": f"Severely overused word(s): {overused_str}",
                "context": "One word dominates the essay",
                "suggest": "Use synonyms and vary your vocabulary"
            })

    # 8. Wrong verb form after modal
    modal_errors = []
    for token in doc:
        if token.dep_ == "aux" and token.tag_ == "MD":
            head = token.head
            if head.pos_ == "VERB" and head.tag_ not in ("VB", "VBP"):
                has_be = any(c.lemma_ == "be" and c.dep_ == "auxpass" for c in head.children)
                if not has_be:
                    modal_errors.append(f"'{token.text} {head.text}'")
    if modal_errors:
        issues.append({
            "message": f"Wrong verb form after modal: {', '.join(modal_errors[:3])}",
            "context": "Modals must be followed by base verb form",
            "suggest": "Use base form: 'can go', not 'can goes'"
        })

    return issues


def grammar_suggestions(text: str, max_issues: int = 20) -> Dict[str, object]:
    issues: List[Dict[str, str]] = []
    corrected = text

    if _LT:
        try:
            matches = _LT.check(text)
            for m in matches[:max_issues]:
                rep = ", ".join(m.replacements[:3]) if m.replacements else ""
                issues.append({
                    "message": m.message,
                    "context": text[max(0, m.offset-20): m.offset + m.errorLength + 20],
                    "suggest": rep
                })
            corrected = language_tool_python.utils.correct(text, matches)
        except Exception:
            pass

    spacy_issues = _spacy_grammar_issues(text)
    seen = {i["message"][:40] for i in issues}
    for si in spacy_issues:
        if si["message"][:40] not in seen:
            issues.append(si)
            seen.add(si["message"][:40])

    issues = issues[:max_issues]
    score_penalty = min(70, len(issues) * 8)
    grammar_score = max(0, 100 - score_penalty)
    return {"issues": issues, "corrected_text": corrected, "grammar_score": grammar_score}


def topic_relevance(text: str, topic: Optional[str] = None, keywords: Optional[List[str]] = None) -> float:
    """
    Semantic topic relevance using sentence-transformers.
    Compares full essay against title using real semantic embeddings —
    understands that 'vacation' = 'trip', 'persistence' = 'never giving up'.
    Falls back to TF-IDF if sentence-transformers not available.
    """
    if not topic and not keywords:
        return 0.0

    # Build query string from title + keywords
    query = (topic or "")
    if keywords:
        query += " " + " ".join(keywords)
    query = query.strip()
    if not query:
        return 0.0

    if _ST_AVAILABLE and _ST_MODEL is not None:
        try:
            # Encode title and full essay text
            title_emb = _ST_MODEL.encode(query, convert_to_tensor=True)
            essay_emb = _ST_MODEL.encode(text, convert_to_tensor=True)
            raw_sim = float(st_util.cos_sim(title_emb, essay_emb)[0][0])

            # Scale: empirically, on-topic essays score 0.3-0.8, off-topic 0.1-0.3
            # Map 0.2 -> 0, 0.4 -> 50, 0.6 -> 85, 0.8 -> 100
            scaled = (raw_sim - 0.2) / 0.6 * 100.0
            return round(max(0.0, min(100.0, scaled)), 2)
        except Exception:
            pass

    # Fallback: TF-IDF cosine similarity
    try:
        docs = [text, query * 5]
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
        X = vec.fit_transform(docs)
        sim = cosine_similarity(X[0], X[1])[0][0]
        return round(min(100.0, sim * 250.0), 2)
    except Exception:
        return 0.0


def _extract_features(text: str) -> Dict[str, float]:
    words = text.split()
    sentences = [s for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()]
    uniq = len({w.lower().strip(".,;:!?\"'()[]{}") for w in words}) if words else 0
    avg_sent_len = (len(words) / len(sentences)) if sentences else 0
    type_token_ratio = (uniq / len(words) * 100) if words else 0
    read = readability_metrics(text)
    sent = sentiment_score(text)
    gram = grammar_suggestions(text)
    return {
        "word_count": len(words),
        "avg_sentence_len": avg_sent_len,
        "type_token_ratio": type_token_ratio,
        "readability": read["readability_score"],
        "sentiment": sent["positivity"],
        "grammar": gram["grammar_score"],
        "issue_count": len(gram["issues"]),
    }


def _features_to_vector(feat: Dict[str, float]) -> List[float]:
    return [
        feat["word_count"],
        feat["avg_sentence_len"],
        feat["type_token_ratio"],
        feat["readability"],
        feat["sentiment"],
        feat["grammar"],
        feat["issue_count"],
    ]


def ml_score(text: str) -> Tuple[float, Dict[str, float]]:
    feat = _extract_features(text)
    richness = min(100.0, feat["type_token_ratio"])
    length_score = min(100.0, feat["word_count"] / 400.0 * 100.0)
    structure = min(100.0, max(0.0, 1 - abs(feat["avg_sentence_len"] - 15) / 15.0) * 100.0)
    length_penalty = max(0.0, (150 - feat["word_count"]) / 150.0 * 20.0)
    depth_bonus = min(10.0, max(0.0, (feat["word_count"] - 200) / 200.0 * 10.0))
    ttr_factor = min(1.0, richness / 70.0)
    adj_readability = feat["readability"] * ttr_factor
    score = (
        0.40 * feat["grammar"] +
        0.25 * adj_readability +
        0.20 * richness +
        0.10 * length_score +
        0.05 * structure
        - length_penalty
        + depth_bonus
    )
    return round(max(0.0, min(100.0, score)), 2), feat