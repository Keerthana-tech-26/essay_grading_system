from django.db import models
from django.db.models import JSONField
class Essay(models.Model):
    title = models.CharField(max_length=200)
    student_name = models.CharField(max_length=100, blank=True, null=True)
    content = models.TextField()
    score_length = models.FloatField(default=0)
    score_clarity = models.FloatField(default=0)
    score_vocabulary = models.FloatField(default=0)
    score_readability = models.FloatField(default=0)
    score_overall = models.FloatField(default=0)
    feedback = models.TextField(blank=True, null=True)

    analysis = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title