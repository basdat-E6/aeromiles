from django.shortcuts import render, redirect, get_object_or_404
from .models import Hadiah, Penyedia, Mitra, Penyedia
from .forms import HadiahForm
from datetime import date
from django.http import JsonResponse

# READ + FILTER
def hadiah_list(request):
    penyedia_id = request.GET.get('penyedia')
    status = request.GET.get('status')

    hadiah = Hadiah.objects.all()

    if penyedia_id:
        hadiah = hadiah.filter(penyedia_id=penyedia_id)

    if status == 'aktif':
        hadiah = hadiah.filter(valid_end__gte=date.today())
    elif status == 'expired':
        hadiah = hadiah.filter(valid_end__lt=date.today())

    penyedia_list = Penyedia.objects.all()

    return render(request, 'hadiah/list.html', {
        'hadiah': hadiah,
        'penyedia_list': penyedia_list
    })


# CREATE
def hadiah_create(request):
    form = HadiahForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('hadiah_list')
    return render(request, 'hadiah/form.html', {'form': form, 'title': 'Tambah Hadiah'})

# UPDATE
def hadiah_update(request, pk):
    hadiah = get_object_or_404(Hadiah, pk=pk)
    form = HadiahForm(request.POST or None, instance=hadiah)

    if form.is_valid():
        form.save()
        return redirect('hadiah_list')

    return render(request, 'hadiah/form.html', {
        'form': form,
        'title': 'Edit Hadiah',
        'hadiah': hadiah
    })


# DELETE (hanya jika expired)
def hadiah_delete(request, pk):
    hadiah = get_object_or_404(Hadiah, pk=pk)

    if not hadiah.is_expired():
        return redirect('hadiah_list')  # tidak boleh delete

    if request.method == 'POST':
        hadiah.delete()
        return redirect('hadiah_list')

    return render(request, 'hadiah/delete.html', {'hadiah': hadiah})

# 🔍 READ
def mitra_list(request):
    mitras = Mitra.objects.all()
    return render(request, 'mitra/list.html', {'mitras': mitras})


# ➕ CREATE (langsung buat penyedia juga)
def mitra_create(request):
    if request.method == 'POST':
        form = MitraForm(request.POST)
        if form.is_valid():
            mitra = form.save()

            # otomatis buat penyedia
            Penyedia.objects.create(
                mitra=mitra,
                nama_penyedia=mitra.nama
            )

            return redirect('mitra_list')
    else:
        form = MitraForm()

    return render(request, 'mitra/create.html', {'form': form})


# ✏️ UPDATE (email tidak boleh diubah)
def mitra_update(request, email):
    mitra = get_object_or_404(Mitra, email=email)

    if request.method == 'POST':
        form = MitraForm(request.POST, instance=mitra)
        if form.is_valid():
            form.save()
            return redirect('mitra_list')
    else:
        form = MitraForm(instance=mitra)
        form.fields['email'].disabled = True  # sesuai PDF

    return render(request, 'mitra/update.html', {'form': form})


# DELETE
def mitra_delete(request, email):
    mitra = get_object_or_404(Mitra, email=email)

    if request.method == 'POST':
        mitra.delete()  # cascade ke hadiah
        return redirect('mitra_list')

    return render(request, 'mitra/delete.html', {'mitra': mitra})