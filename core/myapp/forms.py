from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Property, Slot, Message

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + ('email', 'role',)

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['title', 'description', 'price', 'location', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class SlotForm(forms.ModelForm):
    class Meta:
        model = Slot
        fields = ['date', 'time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
        }

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Ask AssistMe about PC builds, availability, bookings...'}),
        }
