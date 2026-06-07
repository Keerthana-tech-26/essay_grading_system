# AI Essay Grader (Django)

An intelligent essay grading system built with Django that uses multiple NLP libraries to evaluate essays across grammar, vocabulary, readability, topic relevance, and writing quality — providing detailed, actionable feedback.

## Features

### Grading & Analysis
- **Grammar Checking** — Powered by LanguageTool (Java-based) for real grammar detection: tense errors, subject-verb agreement, missing auxiliaries, capitalisation, and more
- **Vocabulary Scoring** — Type-token ratio combined with average word sophistication (word length as proxy)
- **Readability** — Grade-level aware scoring (sweet spot: grade 6–12); penalises childish or overly complex text
- **Topic Relevance** — Semantic similarity using `sentence-transformers` (`all-MiniLM-L6-v2`); understands synonyms (e.g. "vacation" = "trip")
- **ML Score** — Calibrated scoring formula combining grammar, readability, vocabulary richness, length, and structure
- **Sentiment Analysis** — VADER sentiment scoring
- **Uncountable Noun Detection** — WordNet-based (no hardcoded lists) to reduce false grammar flags
- **spaCy Grammar Rules** — Additional structural checks: circular phrasing, overused words, modal verb errors

### Application
- Submit essays with title and student name
- Instant detailed feedback with grammar suggestions, vocabulary tips, and improvement areas
- Auto-corrected draft (when LanguageTool is available)
- Essay history with scores
- Delete single essays or bulk delete multiple essays via checkboxes
- Analytics dashboard with:
  - Overall score trend chart
  - Average sub-scores breakdown
  - Common issues distribution
  - Sentiment trend over time
  - Grammar issues over time
  - Topic relevance distribution (High / Medium / Low)

## Tech Stack

| Component | Library |
|---|---|
| Web Framework | Django 4.2 |
| Grammar Checking | LanguageTool (via `language-tool-python`) + Java |
| Semantic Similarity | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| NLP / POS Tagging | `spaCy` (`en_core_web_sm`) |
| Uncountable Nouns | `nltk` WordNet |
| Readability | `textstat` |
| Sentiment | `vaderSentiment` |
| ML Scoring | `scikit-learn`, `joblib` |
| Database | SQLite |
| Charts | Chart.js |

## Quickstart

```bash
# 1) Create & activate a virtualenv
python -m venv .venv
# Windows:
.venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Download spaCy model
python -m spacy download en_core_web_sm

# 4) Download NLTK WordNet data
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

# 5) Install Java (required for LanguageTool grammar checker)
# Download from: https://www.oracle.com/java/technologies/downloads/
# Verify: java -version

# 6) Migrate & run
python manage.py migrate
python manage.py runserver
```

## Project Layout

```
Essay_grading-main/
├── essays/
│   ├── ai.py           # Core AI: grammar, sentiment, readability, topic relevance, ML score
│   ├── utils.py        # Rule-based grading: length, clarity, vocabulary, feedback generation
│   ├── views.py        # Django views: submit, detail, delete, bulk delete, dashboard
│   ├── models.py       # Essay model with score fields and JSON analysis field
│   ├── urls.py         # URL routing
│   └── forms.py        # Essay submission form
├── templates/essays/
│   ├── index.html      # Home page with essay submission form
│   ├── detail.html     # Essay result page with full analysis
│   ├── dashboard.html  # Analytics dashboard with charts
│   └── confirm_delete.html  # Delete confirmation page
├── static/js/
│   └── dashboard.js    # Chart.js chart rendering
├── project/            # Django project settings
├── requirements.txt
└── README.md
```

## Scoring System

| Metric | Weight | Method |
|---|---|---|
| Grammar | 40% | LanguageTool + spaCy rules |
| Readability | 25% | textstat grade-level (adjusted by vocabulary richness) |
| Vocabulary | 20% | Type-token ratio + word sophistication |
| Length | 10% | Word count (target: 200+ words) |
| Structure | 5% | Sentence length distribution |

**Bonuses & Penalties:**
- Depth bonus: up to +10 points for essays over 200 words
- Length penalty: up to -20 points for essays under 150 words
- TTR multiplier: poor vocabulary reduces readability credit proportionally

## Notes

- First essay submission after server start may take a few seconds longer — LanguageTool starts its Java server on first use; subsequent requests are fast.
- The `sentence-transformers` model (`~90MB`) downloads automatically on first run.
- LanguageTool grammar data (`~260MB`) downloads automatically on first run.
- This system is designed for demos and educational projects. For production use, consider additional training data and model fine-tuning.