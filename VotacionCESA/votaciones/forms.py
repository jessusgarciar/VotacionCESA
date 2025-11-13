from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Voter, Candidate, Election
from .models import CandidateMember
from django.forms import ModelForm, HiddenInput

User = get_user_model()


def _is_valid_algorand_address(addr: str) -> bool:
    """Try to validate an Algorand address.

    Prefer `algosdk`'s validator when available; otherwise perform a lightweight
    format check (base32 chars, length 58).
    """
    if not addr:
        return False
    try:
        from algosdk.encoding import is_valid_address
        return is_valid_address(addr)
    except Exception:
        # fallback simple check: base32 (A-Z2-7) length 58
        import re
        return bool(re.fullmatch(r"[A-Z2-7]{58}", addr))


class FrontendUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=False)
    create_voter = forms.BooleanField(required=False, initial=False, label='Crear perfil de votante')
    control_number = forms.CharField(required=False, max_length=50, label='Número de control')

    class Meta:
        model = User
        fields = ('username', 'email')

    def clean(self):
        data = super().clean()
        create_voter = data.get('create_voter')
        control = data.get('control_number')
        if create_voter and control:
            # ensure control_number unique
            if Voter.objects.filter(control_number=control).exists():
                raise ValidationError({'control_number': 'El número de control ya está en uso por otro votante.'})
        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add bootstrap classes to common fields
        widgets_map = {
            'username': {'class': 'form-control'},
            'email': {'class': 'form-control'},
            'password1': {'class': 'form-control'},
            'password2': {'class': 'form-control'},
        }
        for name, attrs in widgets_map.items():
            if name in self.fields:
                existing = self.fields[name].widget.attrs
                existing.update(attrs)

        # control_number and create_voter
        if 'control_number' in self.fields:
            self.fields['control_number'].widget.attrs.update({'class': 'form-control'})
        if 'create_voter' in self.fields:
            self.fields['create_voter'].widget.attrs.update({'class': 'form-check-input'})


class VoterForm(forms.ModelForm):
    class Meta:
        model = Voter
        fields = ('user', 'control_number', 'is_eligible', 'blockchain_address')
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'control_number': forms.TextInput(attrs={'class': 'form-control'}),
            'is_eligible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'blockchain_address': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_control_number(self):
        cn = self.cleaned_data.get('control_number')
        if not cn:
            raise ValidationError('El número de control es obligatorio.')
        qs = Voter.objects.filter(control_number=cn)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Este número de control ya está registrado para otro votante.')
        return cn

    def clean_user(self):
        user = self.cleaned_data.get('user')
        if not user:
            raise ValidationError('Selecciona un usuario.')
        qs = Voter.objects.filter(user=user)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Este usuario ya tiene un perfil de votante.')
        return user

    def clean_blockchain_address(self):
        addr = (self.cleaned_data.get('blockchain_address') or '').strip()
        if addr:
            if not _is_valid_algorand_address(addr):
                raise ValidationError('Dirección Algorand inválida (formato incorrecto).')
        return addr or None


class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ('name', 'list_name', 'image_url', 'manifesto', 'election')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'list_name': forms.TextInput(attrs={'class': 'form-control'}),
            # Model now uses ImageField; present a file input so staff can see/remove
            # or replace an existing uploaded image. The form also exposes an
            # auxiliary `image` upload field which the view handles.
            'image_url': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'manifesto': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'election': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise ValidationError('El nombre de la planilla es obligatorio.')
        return name

    # allow uploading an image from the admin frontend; this field is not stored
    # directly on the model (the model stores an image_url string). The view will
    # handle file saving when request.FILES contains 'image'.
    image = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))


class CandidateMemberForm(ModelForm):
    class Meta:
        model = CandidateMember
        fields = ('full_name', 'role', 'order')
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Juan Pérez'}),
            'role': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Presidente'}),
            'order': HiddenInput(),
        }
