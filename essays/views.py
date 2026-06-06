from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import EssayForm
from .models import Essay
from .utils import grade_text
from .ai import readability_metrics, sentiment_score, grammar_suggestions, topic_relevance, ml_score
from django.utils import timezone
from django.db.models.functions import TruncDate
import json

def index(request):
    essays = Essay.objects.order_by('-created_at')[:10]
    form = EssayForm()
    return render(request, 'essays/index.html', {'form': form, 'essays': essays})

def submit_essay(request):
    if request.method == 'POST':
        form = EssayForm(request.POST)
        if form.is_valid():
            essay = form.save(commit=False)
            result = grade_text(essay.content, title=essay.title)
            ai = result.get('ai', {})
            ml = ai.get('ml_overall')
            essay.score_length = result['length_score']
            essay.score_clarity = result['clarity_score']
            essay.score_vocabulary = result['vocab_score']
            essay.score_readability = result['readability_score']
            essay.score_overall = ml if ml is not None else result['overall']
            essay.feedback = result['feedback']
            essay.analysis = ai
            essay.save()
            messages.success(request, 'Essay graded successfully!')
            return redirect('essays:detail', pk=essay.pk)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = EssayForm()
    return render(request, 'essays/index.html', {'form': form})

def essay_detail(request, pk):
    essay = get_object_or_404(Essay, pk=pk)
    ai_analysis = {}
    text = essay.content
    
    try:
        ai_analysis['readability'] = readability_metrics(text).get("readability_score", 0)
    except Exception as e:
        print(f"Readability error: {e}")
        ai_analysis['readability'] = 0
        
    try:
        ai_analysis['sentiment'] = sentiment_score(text).get("positivity", 0)
    except Exception as e:
        print(f"Sentiment error: {e}")
        ai_analysis['sentiment'] = 0
        
    try:
        grammar_result = grammar_suggestions(text)
        ai_analysis['grammar'] = {
            "score": grammar_result.get("grammar_score", 0),
            "issues": [i['message'] for i in grammar_result.get("issues", [])]
        }
    except Exception as e:
        print(f"Grammar error: {e}")
        ai_analysis['grammar'] = {"score": 0, "issues": []}

    try:
        ai_analysis['topic_relevance'] = topic_relevance(text, essay.title)
    except Exception as e:
        print(f"Topic relevance error: {e}")
        ai_analysis['topic_relevance'] = 0

    try:
        ml_overall, _ = ml_score(text)
        ai_analysis['ml_overall'] = ml_overall
    except Exception as e:
        print(f"ML score error: {e}")
        ai_analysis['ml_overall'] = essay.score_overall
        
    essay.analysis = ai_analysis
    return render(request, 'essays/detail.html', {'essay': essay})

def delete_essay(request, pk):
    essay = get_object_or_404(Essay, pk=pk)
    if request.method == 'POST':
        title = essay.title
        essay.delete()
        messages.success(request, f'Essay "{title}" deleted successfully.')
        next_url = request.POST.get('next', 'essays:index')
        return redirect(next_url)
    return render(request, 'essays/confirm_delete.html', {'essay': essay})

def dashboard(request):
    essays = Essay.objects.order_by('-created_at')[:50]
    labels = []
    overall_scores = []
    sentiments = []
    grammar_counts = []
    avg_len = avg_clarity = avg_vocab = avg_read = 0.0
    issue_counts = {
        'Short (<150 words)': 0,
        'Low readability (<60)': 0,
        'Passive voice': 0,
        'Hedging': 0,
        'Repeated words': 0,
        'Misspellings': 0,
    }
    topic_relevance_counts = {"High": 0, "Medium": 0, "Low": 0}
    n = max(1, len(essays))
    for i, essay in enumerate(reversed(essays)):
        try:
            labels.append(essay.created_at.strftime("%b %d"))
            overall_scores.append(float(essay.score_overall or 0))
            if hasattr(essay, 'cached_result') and essay.cached_result:
                result = essay.cached_result
            else:
                try:
                    result = grade_text(essay.content)
                except Exception as e:
                    print(f"Grading error for essay {essay.pk}: {e}")
                    result = {
                        'stats': {'total_words': len(essay.content.split())},
                        'readability_score': 50,
                        'meta': {
                            'passive_hits': 0,
                            'hedges': [],
                            'repeated': [],
                            'misspellings': []
                        },
                        'ai': {}
                    }
            avg_len += float(essay.score_length or 0)
            avg_clarity += float(essay.score_clarity or 0)
            avg_vocab += float(essay.score_vocabulary or 0)
            avg_read += float(essay.score_readability or 0)
            stats = result.get('stats', {})
            meta = result.get('meta', {})
            
            if stats.get('total_words', 0) < 150:
                issue_counts['Short (<150 words)'] += 1
            if result.get('readability_score', 0) < 60:
                issue_counts['Low readability (<60)'] += 1
            if meta.get('passive_hits', 0) > 0:
                issue_counts['Passive voice'] += 1
            if len(meta.get('hedges', [])) > 0:
                issue_counts['Hedging'] += 1
            if len(meta.get('repeated', [])) > 0:
                issue_counts['Repeated words'] += 1
            if len(meta.get('misspellings', [])) > 0:
                issue_counts['Misspellings'] += 1          
            ai_data = result.get('ai', {})
            if ai_data:
                sentiment_val = ai_data.get('sentiment', 0)
                if isinstance(sentiment_val, dict):
                    sentiment_val = sentiment_val.get('positivity', 0)
                sentiments.append(float(sentiment_val))
                
                grammar_data = ai_data.get('grammar', {})
                if isinstance(grammar_data, dict):
                    grammar_issues = grammar_data.get('issues', [])
                    grammar_counts.append(len(grammar_issues))
                else:
                    grammar_counts.append(0)
                
                topic_rel = ai_data.get('topic_relevance', 0)
                if isinstance(topic_rel, dict):
                    topic_rel = topic_rel.get('score', 0)
                topic_rel = float(topic_rel)
                
                if topic_rel >= 70:
                    topic_relevance_counts["High"] += 1
                elif topic_rel >= 40:
                    topic_relevance_counts["Medium"] += 1
                else:
                    topic_relevance_counts["Low"] += 1
            else:
                sentiments.append(50.0)  
                grammar_counts.append(0)
                topic_relevance_counts["Low"] += 1
                
        except Exception as e:
            print(f"Error processing essay {essay.pk}: {e}")
            if len(labels) == i: 
                labels.append(f"Essay {i+1}")
            if len(overall_scores) == i:
                overall_scores.append(0.0)
            if len(sentiments) == i:
                sentiments.append(50.0)
            if len(grammar_counts) == i:
                grammar_counts.append(0)
            topic_relevance_counts["Low"] += 1
    avg_scores = {
        'Length': round(avg_len / n, 1),
        'Clarity': round(avg_clarity / n, 1),
        'Vocabulary': round(avg_vocab / n, 1),
        'Readability': round(avg_read / n, 1),
    }
    filtered_issue_labels = []
    filtered_issue_values = []
    for label, value in issue_counts.items():
        if value > 0:
            filtered_issue_labels.append(label)
            filtered_issue_values.append(value)
    context = {
        'labels': labels,
        'overall_scores': overall_scores,
        'avg_scores': avg_scores,
        'avg_overall': round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else 0,
        'total_issues': sum(issue_counts.values()),
        'issue_labels': filtered_issue_labels,
        'issue_values': filtered_issue_values,
        'sentiments': sentiments,
        'grammar_counts': grammar_counts,
        'topic_relevance': topic_relevance_counts,
        'recent_essays': Essay.objects.order_by('-created_at')[:10],
        'total_essays': Essay.objects.count(),
    }
    print(f"Dashboard context: {n} essays processed")
    print(f"Labels: {len(labels)}, Scores: {len(overall_scores)}")
    print(f"Sentiments: {len(sentiments)}, Grammar: {len(grammar_counts)}")
    
    return render(request, 'essays/dashboard.html', context)