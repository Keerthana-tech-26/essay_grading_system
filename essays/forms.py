from django import forms
from .models import Essay

class EssayForm(forms.ModelForm):
    class Meta:
        model = Essay
        fields = ['title', 'student_name', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Essay title'}),
            'student_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name (optional)'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 12, 'placeholder': 'Paste or type your essay here...'}),
        }
