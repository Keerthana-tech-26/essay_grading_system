import re
import math
from collections import Counter
from typing import Dict, Any, Optional, List
from .ai import readability_metrics, sentiment_score, grammar_suggestions, topic_relevance, ml_score

SENTENCE_SPLIT = re.compile(r'[.!?]+(?=\s|$)')
WORD_RE = re.compile(r"[A-Za-z']+")

COMMON_MISSPELLINGS = {
    'teh': 'the',
    'recieve': 'receive',
    'definately': 'definitely',
    'occured': 'occurred',
    'seperate': 'separate',
    'wich': 'which',
    'adress': 'address',
    'becuase': 'because',
    'enviroment': 'environment',
    'goverment': 'government',
}

HEDGING_WORDS = {
    'maybe', 'perhaps', 'somewhat', 'kinda', 'sort of', 'sorta',
    'i think', 'i believe', 'i guess'
}

def split_sentences(text: str):
    text = text.strip()
    if not text:
        return []
    return [p.strip() for p in SENTENCE_SPLIT.split(text) if p.strip()]

def words(text: str):
    return WORD_RE.findall(text.lower())

def flesch_kincaid_proxy(total_words, total_sentences, syllables_estimate):
    if total_sentences == 0 or total_words == 0:
        return 0.0
    ASL = total_words / total_sentences
    ASW = syllables_estimate / total_words
    # Use grade-level logic: sweet spot is grade 6-12
    # FK grade = 0.39*ASL + 11.8*ASW - 15.59
    fk_grade = 0.39 * ASL + 11.8 * ASW - 15.59
    if fk_grade <= 4:
        grade_score = max(10.0, fk_grade / 4.0 * 50.0)
    elif fk_grade <= 12:
        grade_score = 50.0 + (fk_grade - 4) / 8.0 * 45.0
    else:
        grade_score = max(60.0, 95.0 - (fk_grade - 12) * 5.0)
    return round(max(0.0, min(100.0, grade_score)), 2)

def estimate_syllables(w):
    vowels = "aeiouy"
    w = w.lower()
    count, prev_is_vowel = 0, False
    for ch in w:
        is_vowel = ch in vowels
        if is_vowel and not prev_is_vowel:
            count += 1
        prev_is_vowel = is_vowel
    if w.endswith("e") and count > 1:
        count -= 1
    return max(1, count)

def grade_text(text: str, title: str = ""):
    sents = split_sentences(text)
    tokens = words(text)
    total_words = len(tokens)
    total_sents = len(sents)
    length_score = min(100.0, (total_words / 150.0) * 100.0)
    avg_sent_len = (total_words / total_sents) if total_sents else 0
    # Ideal sentence length: 12-20 words. Too short (choppy) or too long (confusing) both penalised.
    if 12 <= avg_sent_len <= 20:
        clarity_score = 100.0
    elif avg_sent_len < 12:
        # Very short sentences = choppy, underdeveloped
        clarity_score = max(50.0, 50.0 + (avg_sent_len / 12.0) * 50.0)
    else:
        clarity_score = max(0.0, 100.0 - (avg_sent_len - 20) * 3.0)
    unique = len(set(tokens))
    ttr = (unique / total_words) if total_words else 0
    # Average word length as a proxy for vocabulary sophistication
    avg_word_len = (sum(len(w) for w in tokens) / total_words) if total_words else 0
    word_sophistication = min(100.0, max(0.0, (avg_word_len - 3.0) / 3.5 * 100.0))
    # TTR scaled: 0.2=0pts, 0.8+=100pts; mediocre essays score ~40-50
    ttr_score = min(100.0, max(0.0, (ttr - 0.2) / 0.6 * 100.0))
    vocab_score = round(0.6 * ttr_score + 0.4 * word_sophistication, 2)
    syllables = sum(estimate_syllables(w) for w in tokens)
    readability_score = flesch_kincaid_proxy(total_words, total_sents, syllables)
    passive_hits = len(re.findall(r'\b(am|is|are|was|were|be|been|being)\b\s+\b\w+ed\b\s*(?:by\b)?', text, flags=re.I))
    hedges = [h for h in HEDGING_WORDS if h in text.lower()]
    counts = Counter(tokens)
    repeated = [w for w, c in counts.items() if c >= 5 and len(w) > 3]
    miss = [(w, COMMON_MISSPELLINGS[w]) for w in tokens if w in COMMON_MISSPELLINGS]
    # Get grammar score so it feeds into overall
    try:
        _gram_res = grammar_suggestions(text)
        grammar_score_val = _gram_res.get("grammar_score", 100)
    except Exception:
        grammar_score_val = 100

    # Overall: grammar now counts 20% so poor grammar directly hurts the score
    raw_overall = round(
        0.20 * length_score +
        0.20 * clarity_score +
        0.20 * vocab_score +
        0.20 * readability_score +
        0.20 * grammar_score_val, 2
    )
    # Hard caps: very short essays cannot score high
    if total_words < 80:
        overall = min(raw_overall, 55.0)
    elif total_words < 150:
        overall = min(raw_overall, 75.0)
    else:
        overall = raw_overall
    feedback_lines = []
    feedback_lines.append(f"Words: {total_words}, Sentences: {total_sents}, Avg sentence length: {avg_sent_len:.1f}")
    if total_words < 150:
        feedback_lines.append("• Expand your essay to at least ~150 words to cover the topic more fully.")
    if avg_sent_len > 24:
        feedback_lines.append("• Consider splitting long sentences for clarity.")
    if ttr < 0.4:
        feedback_lines.append("• Try to vary your vocabulary to avoid repetition.")
    if readability_score < 60:
        feedback_lines.append("• Simplify sentence structure and prefer familiar words to improve readability.")
    if passive_hits > 0:
        feedback_lines.append(f"• Detected {passive_hits} possible passive constructions; prefer active voice when appropriate.")
    if hedges:
        feedback_lines.append(f"• Hedging language found ({', '.join(hedges)}); be more confident and precise.")
    if repeated:
        feedback_lines.append(f"• Repeated words appear often: {', '.join(sorted(repeated)[:8])}. Consider synonyms.")
    if miss:
        corrections = ', '.join(f"{a}→{b}" for a, b in miss[:10])
        feedback_lines.append(f"• Possible misspellings: {corrections}.")
    if not feedback_lines[1:]:
        feedback_lines.append("Great job! Clear, varied, and readable.")
    ai_analysis = {}

    try:
        ai_analysis['readability'] = readability_metrics(text).get("readability_score", 0)
    except:
        ai_analysis['readability'] = readability_score

    try:
        ai_analysis['sentiment'] = sentiment_score(text).get("positivity", 0)
    except:
        ai_analysis['sentiment'] = 0

    # Reuse already-computed grammar result
    try:
        grammar_res = _gram_res
        ai_analysis['grammar'] = {
            "issues": grammar_res.get("issues", []),
            "grammar_score": grammar_res.get("grammar_score", 0)
        }
    except:
        ai_analysis['grammar'] = {"issues": [], "grammar_score": 0}

    try:
        ai_analysis['topic_relevance'] = topic_relevance(text, title if title else None)
    except:
        ai_analysis['topic_relevance'] = 0

    try:
        ml_overall, feat = ml_score(text)
        ai_analysis['ml_overall'] = ml_overall
        ai_analysis['ml_features'] = feat
    except:
        ai_analysis['ml_overall'] = overall
        ai_analysis['ml_features'] = {}

    return {
        'length_score': round(length_score, 2),
        'clarity_score': round(clarity_score, 2),
        'vocab_score': round(vocab_score, 2),
        'readability_score': round(readability_score, 2),
        'overall': overall,
        'feedback': "\n".join(feedback_lines),
        'stats': {
            'total_words': total_words,
            'total_sentences': total_sents,
            'avg_sentence_len': avg_sent_len,
        },
        'meta': {
            'passive_hits': passive_hits,
            'hedges': hedges,
            'repeated': repeated,
            'misspellings': miss, 
            'ttr': round(ttr, 3),
        },
        'ai': ai_analysis
    }