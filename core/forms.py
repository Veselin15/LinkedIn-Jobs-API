from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    # We enforce email as required
    email = forms.EmailField(required=True, help_text="Required. We will send your API key here.")

    class Meta:
        model = User
        # We use 'username' and 'email'. Password is handled by UserCreationForm automatically.
        fields = ('username', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user