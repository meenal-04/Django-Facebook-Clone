from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import Profile, Post, Comment

class ProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, label="First name", widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=False, label="Last name", widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, label="Email", widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Profile
        fields = ["avatar", "cover_photo", "bio", "location", "relationship_status"]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4, "class": "form-control", "placeholder": "Tell people about yourself..."}),
            "location": forms.TextInput(attrs={"class": "form-control", "placeholder": "City, Country"}),
            "avatar": forms.FileInput(attrs={"class": "form-control"}),
            "cover_photo": forms.FileInput(attrs={"class": "form-control"}),
            "relationship_status": forms.TextInput(attrs={"class": "form-control", "placeholder": "Single, Married, ..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            profile.save()
        return profile

class ConnectlyPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["content", "image", "privacy", "music", "music_preview"] # ADDED MUSIC FIELDS
        widgets = {
            "content": forms.Textarea(attrs={"rows": 3, "class": "form-control", "placeholder": "What's on your mind?"}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "privacy": forms.Select(attrs={"class": "form-select"}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Write a comment..."}),
        }

class SettingsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["is_private"]
        widgets = {
            "is_private": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }