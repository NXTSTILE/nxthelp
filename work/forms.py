from django import forms
from .models import HelpRequest, Application


class HelpRequestForm(forms.ModelForm):
    """Form to create a help request with pricing and deadline."""
    class Meta:
        model = HelpRequest
        fields = ['title', 'description', 'category', 'urgency', 'request_type', 'target_year', 'budget', 'deadline']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'What do you need help with?',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input form-textarea',
                'rows': 6,
                'placeholder': 'Describe your problem in detail. The more context you provide, the better help you will get.',
            }),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'urgency': forms.Select(attrs={'class': 'form-input'}),
            'request_type': forms.Select(attrs={'class': 'form-input'}),
            'target_year': forms.Select(attrs={'class': 'form-input'}),
            'budget': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. ₹500, Negotiable, Free...',
            }),
            'deadline': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'placeholder': 'Select a deadline...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['deadline'].required = False
        self.fields['deadline'].label = 'Deadline (optional)'
        self.fields['budget'].required = False
        self.fields['budget'].label = 'Budget / Pricing'


class ApplicationForm(forms.ModelForm):
    """Form for any user to apply to help with a request."""
    class Meta:
        model = Application
        fields = ['message', 'proposed_budget']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-input form-textarea',
                'rows': 4,
                'placeholder': 'Explain how you can help with this. Share your relevant experience...',
            }),
            'proposed_budget': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your proposed price (optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proposed_budget'].required = False
        self.fields['proposed_budget'].label = 'Your Proposed Price (optional)'
