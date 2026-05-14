from django.db import models
from datetime import date

class Mitra(models.Model):
    email = models.EmailField(primary_key=True)
    nama = models.CharField(max_length=100)
    tanggal_kerja_sama = models.DateField()

    def __str__(self):
        return self.nama

class Penyedia(models.Model):
    mitra = models.OneToOneField(Mitra, on_delete=models.CASCADE, null=True, blank=True) 
    nama_penyedia = models.CharField(max_length=255)
    tipe = models.CharField(max_length=50)
    TIPE_CHOICES = [
        ('airline', 'Airline'),
        ('partner', 'Partner'),
    ]
    mitra = models.OneToOneField(
        Mitra, on_delete=models.CASCADE,
        null=True, blank=True, related_name='penyedia'
    )
    nama_penyedia = models.CharField(max_length=100)
    tipe = models.CharField(max_length=20, choices=TIPE_CHOICES, default='partner')

    def __str__(self):
        return f"{self.nama_penyedia} ({self.tipe})"

class Hadiah(models.Model):
    kode = models.CharField(max_length=10, unique=True, editable=False)
    nama = models.CharField(max_length=255)
    deskripsi = models.TextField()
    penyedia = models.ForeignKey(Penyedia, on_delete=models.CASCADE)
    miles = models.IntegerField()
    valid_start = models.DateField()
    valid_end = models.DateField()

    def save(self, *args, **kwargs):
        if not self.kode:
            last = Hadiah.objects.all().order_by('id').last()
            if last:
                num = int(last.kode.split('-')[1]) + 1
            else:
                num = 1
            self.kode = f"RWD-{num:03d}"
        super().save(*args, **kwargs)

    def is_expired(self):
        return self.valid_end < date.today()

    def __str__(self):
        return f"{self.kode} - {self.nama}"
    