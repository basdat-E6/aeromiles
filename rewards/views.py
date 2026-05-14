from pyexpat.errors import messages

from django.shortcuts import render, redirect, get_object_or_404

from aeromiles import settings
from .models import Hadiah, Penyedia, Mitra
from datetime import date, datetime


def _sync_penyedia():
    """Pastikan semua maskapai dan mitra punya entri Penyedia di DB."""
    # 3 maskapai tetap
    for nama in ["Garuda Indonesia", "Batik Air", "Sriwijaya Air"]:
        Penyedia.objects.get_or_create(
            nama_penyedia=nama,
            tipe='airline',
            defaults={'mitra': None},
        )

    PARTNER_NAMES = [
        "TravelokaPartner",
        "Plaza Premium",
        "ShopIndo Partner",
        "Resto Partner Group",
        "Hotel Bintang Indonesia",
    ]
    for nama in PARTNER_NAMES:
        Penyedia.objects.get_or_create(
            nama_penyedia=nama,
            tipe='partner',
            defaults={'mitra': None},
        )

    # Sync mitra yang ditambahkan manual lewat form Tambah Mitra
    for mitra in Mitra.objects.all():
        Penyedia.objects.update_or_create(
            mitra=mitra,
            defaults={'nama_penyedia': mitra.nama, 'tipe': 'partner'},
        )


def hadiah_list(request):
    """READ: tampilkan semua hadiah."""
    _sync_penyedia()

    hadiah = Hadiah.objects.select_related('penyedia').all()
    penyedia_list = Penyedia.objects.all().order_by('tipe', 'id')

    return render(request, 'hadiah/list.html', {
        'hadiah':        hadiah,
        'penyedia_list': penyedia_list,
    })


def hadiah_create(request):
    """CREATE: form di-POST dari modal Tambah di list_hadiah.html."""
    if request.method == 'POST':
        nama        = request.POST.get('nama', '').strip()
        penyedia_id = request.POST.get('penyedia')
        miles       = request.POST.get('miles')
        deskripsi   = request.POST.get('deskripsi', '').strip()
        valid_start = request.POST.get('valid_start')
        valid_end   = request.POST.get('valid_end')

        if nama and penyedia_id and miles and deskripsi and valid_start and valid_end:
            penyedia = get_object_or_404(Penyedia, pk=penyedia_id)
            Hadiah.objects.create(
                nama        = nama,
                penyedia    = penyedia,
                miles       = int(miles),
                deskripsi   = deskripsi,
                valid_start = valid_start,
                valid_end   = valid_end,
            )

    return redirect('rewards:hadiah_list')


def hadiah_update(request, pk):
    """UPDATE: form di-POST dari modal Edit di list_hadiah.html."""
    hadiah = get_object_or_404(Hadiah, pk=pk)

    if request.method == 'POST':
        nama        = request.POST.get('nama', '').strip()
        penyedia_id = request.POST.get('penyedia')
        miles       = request.POST.get('miles')
        deskripsi   = request.POST.get('deskripsi', '').strip()
        valid_start = request.POST.get('valid_start')
        valid_end   = request.POST.get('valid_end')

        if nama and penyedia_id and miles and deskripsi and valid_start and valid_end:
            penyedia = get_object_or_404(Penyedia, pk=penyedia_id)
            hadiah.nama        = nama
            hadiah.penyedia    = penyedia
            hadiah.miles       = int(miles)
            hadiah.deskripsi   = deskripsi
            hadiah.valid_start = valid_start
            hadiah.valid_end   = valid_end
            hadiah.save()

    return redirect('rewards:hadiah_list')


def hadiah_delete(request, pk):
    """DELETE: hapus hadiah."""
    hadiah = get_object_or_404(Hadiah, pk=pk)

    if request.method == 'POST':
        hadiah.delete()

    return redirect('rewards:hadiah_list')


def mitra_list(request):
    """READ: tampilkan semua mitra."""
    _sync_penyedia()
    mitras = Mitra.objects.all()
    return render(request, 'mitra/list.html', {'mitras': mitras})


def mitra_create(request):
    """CREATE: form di-POST dari modal Tambah di list_mitra.html.
    Otomatis membuat entri Penyedia terkait."""
    if request.method == 'POST':
        email              = request.POST.get('email', '').strip()
        nama               = request.POST.get('nama', '').strip()
        tanggal_kerja_sama = request.POST.get('tanggal_kerja_sama')

        if email and nama and tanggal_kerja_sama:
            # Cek email belum terdaftar
            if not Mitra.objects.filter(email=email).exists():
                mitra = Mitra.objects.create(
                    email              = email,
                    nama               = nama,
                    tanggal_kerja_sama = tanggal_kerja_sama,
                )
                # Otomatis buat entri Penyedia
                Penyedia.objects.create(
                    mitra         = mitra,
                    nama_penyedia = mitra.nama,
                    tipe          = 'partner',   # default; bisa diubah kemudian
                )

    return redirect('rewards:mitra_list')


def mitra_update(request, email):
    """UPDATE: email tidak boleh berubah (PK).
    Form di-POST dari modal Edit di list_mitra.html."""
    mitra = get_object_or_404(Mitra, email=email)

    if request.method == 'POST':
        nama               = request.POST.get('nama', '').strip()
        tanggal_kerja_sama = request.POST.get('tanggal_kerja_sama')

        if nama and tanggal_kerja_sama:
            mitra.nama               = nama
            mitra.tanggal_kerja_sama = tanggal_kerja_sama
            mitra.save()

            try:
                mitra.penyedia.nama_penyedia = nama
                mitra.penyedia.save()
            except Penyedia.DoesNotExist:
                pass

    return redirect('rewards:mitra_list')


def mitra_delete(request, email):
    """DELETE: hapus mitra — cascade ke Penyedia dan Hadiah terkait."""
    mitra = get_object_or_404(Mitra, email=email)

    if request.method == 'POST':
        mitra.delete()   # CASCADE ke Penyedia (dan Hadiah via FK)

    return redirect('rewards:mitra_list')

def katalog(request):
    user_email = request.session.get("user_email")
    role = request.session.get("role")

    if not user_email:
        return redirect("login_view")

    if request.method == "POST":
        if role != "member":
            messages.error(request, "Hanya member yang dapat menukarkan hadiah.")
            return redirect("rewards:katalog")

        kode_hadiah = request.POST.get("kode_hadiah")
        
        try:
            hadiah_res = settings.SUPABASE_CLIENT.table("hadiah") \
                .select("miles") \
                .eq("kode_hadiah", kode_hadiah) \
                .single().execute()
            
            if not hadiah_res.data:
                messages.error(request, "Hadiah tidak ditemukan.")
                return redirect("rewards:katalog")
                
            harga_miles = hadiah_res.data["miles"]
            member_res = settings.SUPABASE_CLIENT.table("member") \
                .select("award_miles") \
                .eq("email", user_email) \
                .single().execute()
                
            saldo_sekarang = member_res.data.get("award_miles", 0)

            if saldo_sekarang < harga_miles:
                messages.error(request, "Award miles Anda tidak mencukupi untuk hadiah ini!")
                return redirect("rewards:katalog")

            waktu_sekarang = datetime.datetime.now().isoformat()
            settings.SUPABASE_CLIENT.table("redeem").insert({
                "email_member": user_email,
                "kode_hadiah": kode_hadiah,
                "timestamp": waktu_sekarang
            }).execute()

            messages.success(request, "Berhasil menukarkan hadiah!")
            return redirect("rewards:katalog")

        except Exception as e:
            print(f"Error saat redeem: {e}")
            messages.error(request, "Terjadi kesalahan saat memproses penukaran.")
            return redirect("rewards:katalog")


    context = {
        "award_miles": 0,
        "hadiah_list": []
    }

    try:
        if role == "member":
            member_res = settings.SUPABASE_CLIENT.table("member") \
                .select("award_miles") \
                .eq("email", user_email) \
                .single().execute()
            if member_res.data:
                context["award_miles"] = member_res.data.get("award_miles", 0)

        hari_ini = datetime.date.today().isoformat()
        
        hadiah_res = settings.SUPABASE_CLIENT.table("hadiah") \
            .select("*, penyedia(nama_penyedia)") \
            .gte("program_end", hari_ini) \
            .execute()
            
        if hadiah_res.data:
            daftar_hadiah = hadiah_res.data
            for h in daftar_hadiah:
                h['nama_mitra'] = h.get('penyedia', {}).get('nama_penyedia', '-')
            context["hadiah_list"] = daftar_hadiah

    except Exception as e:
        print(f"Error fetch katalog: {e}")

    return render(request, 'rewards/katalog.html', context)

def beli_package(request):
    user_email = request.session.get("user_email")
    role = request.session.get("role")

    if not user_email:
        return redirect("authentication:login")

    if request.method == "POST":
        if role != "member":
            messages.error(request, "Hanya member yang dapat membeli package.")
            return redirect("rewards:beli_package")

        nama_paket = request.POST.get("nama_paket")
        waktu_sekarang = datetime.datetime.now().isoformat()
        
        try:
            settings.SUPABASE_CLIENT.table("member_award_miles_package").insert({
                "email_member": user_email,
                "nama_paket": nama_paket,
                "timestamp": waktu_sekarang
            }).execute()
            
            messages.success(request, f"Berhasil membeli paket {nama_paket}!")
        except Exception as e:
            print(f"Error Beli Package: {e}")
            messages.error(request, "Gagal memproses pembelian paket.")
            
        return redirect("rewards:beli_package")

    context = {"packages": []}
    try:
        pkg_res = settings.SUPABASE_CLIENT.table("award_miles_package").select("*").execute()
        if pkg_res.data:
            context["packages"] = pkg_res.data
    except Exception as e:
        print(f"Error fetch packages: {e}")

    return render(request, 'rewards/beli_package.html', context)

def info_tier(request):
    context = {"tiers": []}
    try:
        tier_res = settings.SUPABASE_CLIENT.table("tier").select("*").execute()
        
        if tier_res.data:
            tiers = tier_res.data
            tiers.sort(key=lambda x: x.get('id_tier', ''))
            context["tiers"] = tiers
            
    except Exception as e:
        print(f"Error fetch info tier: {e}")

    return render(request, 'rewards/info_tier.html', context)

def laporan_transaksi(request):
    user_email = request.session.get("user_email")
    role = request.session.get("role")

    if not user_email:
        return redirect("authentication:login")

    transaksi_gabungan = []

    try:
        pkg_query = settings.SUPABASE_CLIENT.table('member_award_miles_package') \
            .select('timestamp, email_member, nama_paket, award_miles_package(jumlah_award_miles)')
        
        if role == 'member':
            pkg_query = pkg_query.eq('email_member', user_email)
            
        pkg_res = pkg_query.execute()
        for p in pkg_res.data:
            miles = p.get('award_miles_package', {}).get('jumlah_award_miles', 0) if p.get('award_miles_package') else 0
            transaksi_gabungan.append({
                'jenis': 'Beli Package',
                'aktor': p['email_member'],
                'detail': f"Beli {p['nama_paket']}",
                'miles': f"+{miles:,}",
                'is_negative': False,
                'raw_time': p['timestamp'],
                'tanggal': p['timestamp'][:16].replace('T', ' ')
            })

        rdm_query = settings.SUPABASE_CLIENT.table('redeem') \
            .select('timestamp, email_member, kode_hadiah, hadiah(miles, nama)')
        
        if role == 'member':
            rdm_query = rdm_query.eq('email_member', user_email)
            
        rdm_res = rdm_query.execute()
        for r in rdm_res.data:
            miles = r.get('hadiah', {}).get('miles', 0) if r.get('hadiah') else 0
            nama_hadiah = r.get('hadiah', {}).get('nama', r['kode_hadiah'])
            transaksi_gabungan.append({
                'jenis': 'Redeem Hadiah',
                'aktor': r['email_member'],
                'detail': f"Tukar {nama_hadiah}",
                'miles': f"-{miles:,}",
                'is_negative': True,
                'raw_time': r['timestamp'],
                'tanggal': r['timestamp'][:16].replace('T', ' ')
            })

        if role == 'member':
            tf_out = settings.SUPABASE_CLIENT.table('transfer').select('*').eq('email_member_1', user_email).execute()
            for t in tf_out.data:
                transaksi_gabungan.append({
                    'jenis': 'Transfer Keluar',
                    'aktor': t['email_member_2'], 
                    'detail': t.get('catatan', '-'),
                    'miles': f"-{t['jumlah']:,}",
                    'is_negative': True,
                    'raw_time': t['timestamp'],
                    'tanggal': t['timestamp'][:16].replace('T', ' ')
                })

            tf_in = settings.SUPABASE_CLIENT.table('transfer').select('*').eq('email_member_2', user_email).execute()
            for t in tf_in.data:
                transaksi_gabungan.append({
                    'jenis': 'Transfer Masuk',
                    'aktor': t['email_member_1'], 
                    'detail': t.get('catatan', '-'),
                    'miles': f"+{t['jumlah']:,}",
                    'is_negative': False,
                    'raw_time': t['timestamp'],
                    'tanggal': t['timestamp'][:16].replace('T', ' ')
                })
        else:
            tf_res = settings.SUPABASE_CLIENT.table('transfer').select('*').execute()
            for t in tf_res.data:
                transaksi_gabungan.append({
                    'jenis': 'Transfer Miles',
                    'aktor': f"{t['email_member_1']} ➔ {t['email_member_2']}",
                    'detail': t.get('catatan', '-'),
                    'miles': f"{t['jumlah']:,}",
                    'is_negative': False, # Staf cukup lihat nominal mentah
                    'raw_time': t['timestamp'],
                    'tanggal': t['timestamp'][:16].replace('T', ' ')
                })

        transaksi_gabungan.sort(key=lambda x: x['raw_time'], reverse=True)

    except Exception as e:
        print(f"Error fetching laporan transaksi: {e}")

    return render(request, 'rewards/laporan_transaksi.html', {
        'transaksi_list': transaksi_gabungan,
        'role': role
    })