from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm

class HRSignupForm(forms.Form):
    first_name   = forms.CharField(max_length=100, label='First Name')
    last_name    = forms.CharField(max_length=100, label='Last Name')
    email        = forms.EmailField(label='Work Email')
    company      = forms.CharField(max_length=200, label='Company Name')
    designation  = forms.CharField(max_length=100, label='Your Designation')
    phone        = forms.CharField(max_length=30, label='Phone Number')
    password1    = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2    = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        if p1 and len(p1) < 8:
            raise forms.ValidationError('Password must be at least 8 characters.')
        return cleaned


class HRLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Work Email', widget=forms.EmailInput(attrs={'autofocus': True}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'your@email.com'})
        self.fields['password'].widget.attrs.update({'placeholder': '••••••••'})
