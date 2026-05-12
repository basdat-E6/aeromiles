from django.db import models
from django.contrib.auth.models import User

class MemberProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nomor_member = models.CharField(max_length=20, unique=True, editable=False)
    tanggal_bergabung = models.DateField(auto_now_add=True)
    salutation = models.CharField(max_length=10, choices=[('Mr.', 'Mr.'), ('Mrs.', 'Mrs.'), ('Ms.', 'Ms.')])
    nama_tengah = models.CharField(max_length=100, blank=True, null=True)
    kewarganegaraan = models.CharField(max_length=100, default='Indonesia')
    country_code = models.CharField(max_length=5, default='+62')
    nomor_hp = models.CharField(max_length=20)
    tanggal_lahir = models.DateField()

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"