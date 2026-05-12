from django import forms
from .models import Hadiah, Mitra

class HadiahForm(forms.ModelForm):
    class Meta:
        model = Hadiah
        fields = ['nama', 'penyedia', 'miles', 'deskripsi', 'valid_start', 'valid_end']
        widgets = {
            'valid_start': forms.DateInput(attrs={'type': 'date'}),
            'valid_end': forms.DateInput(attrs={'type': 'date'}),
        }

class MitraForm(forms.ModelForm):
    class Meta:
        model = Mitra
        fields = ['email', 'nama', 'tanggal_kerja_sama']
        widgets = {
            'tanggal_kerja_sama': forms.DateInput(attrs={'type': 'date'}),
        }