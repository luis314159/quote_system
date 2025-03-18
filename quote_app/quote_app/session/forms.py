from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from quote.models import User, Company


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm',
        'placeholder': 'user'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm',
        'placeholder': 'password'
    }))

class CompanyUserRegistrationForm(UserCreationForm):
    registration_code = forms.UUIDField(
        label='Registration Code',
        help_text='Enter the code provided by the administrator',
        widget=forms.TextInput(attrs={
            'class': 'form-control border-2 border-indigo-500 focus:ring-indigo-500 focus:border-indigo-600 rounded-md p-2 w-full',
            'placeholder': 'Registration Code',
            'autofocus': 'autofocus'  # Esto hace que el campo sea seleccionado automáticamente
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'registration_code':  # Ya personalizamos este campo arriba
                self.fields[field].widget.attrs.update({
                    'class': 'form-control border border-gray-300 focus:ring-indigo-500 focus:border-indigo-500 rounded-md p-2 w-full',
                    'placeholder': self.fields[field].label
                })

class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff', 'is_superuser')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control border border-gray-300 focus:ring-indigo-500 focus:border-indigo-500 rounded-md p-2 w-full',
                'placeholder': self.fields[field].label
            })