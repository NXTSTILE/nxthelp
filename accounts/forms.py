from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Profile


class EmailOrUsernameAuthForm(AuthenticationForm):
    """Custom auth form that does NOT reject inactive users.

    This prevents timing-based user enumeration: valid credentials for
    inactive accounts will pass ``is_valid()`` so the view can redirect
    to OTP verification without needing a secondary DB lookup.
    """

    def confirm_login_allowed(self, user):
        # Allow inactive users so the view can handle them uniformly.
        pass


class UserRegisterForm(UserCreationForm):
    """Registration form — no role selection, just personal info."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'university@email.com',
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'First name',
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Last name',
        })
    )
    profession = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. 3rd Year CSE Student, Assistant Professor...',
        }),
        help_text='What is your role at the university?'
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Choose a username',
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Create a password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Confirm password',
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            user.profile.profession = self.cleaned_data.get('profession', '')
            user.profile.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """Form to update profile details."""
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input'}))

    class Meta:
        model = Profile
        fields = ['profession', 'bio', 'skills', 'year', 'department', 'phone_number', 'upi_id']
        widgets = {
            'profession': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. 3rd Year CSE Student, Assistant Professor...',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-input form-textarea', 'rows': 4,
                'placeholder': 'Tell us about yourself...',
            }),
            'skills': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Python, Mathematics, Data Science...',
            }),
            'year': forms.Select(attrs={'class': 'form-input'}),
            'department': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Computer Science',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. 9876543210',
            }),
            'upi_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. yourname@upi, yourname@paytm',
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        query = User.objects.filter(email=email)
        if self.user and self.user.pk:
            query = query.exclude(pk=self.user.pk)
        if query.exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            if commit:
                self.user.save()
        if commit:
            profile.save()
        return profile
