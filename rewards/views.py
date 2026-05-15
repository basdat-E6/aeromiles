from django.contrib import messages  
from django.shortcuts import render, redirect, get_object_or_404

from aeromiles import settings
from .models import Hadiah, Penyedia, Mitra
import datetime
from datetime import date

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
    print("=== KATALOG DIPANGGIL ===") 
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
                .select("miles, nama, valid_start_date, program_end") \
                .eq("kode_hadiah", kode_hadiah) \
                .single().execute()
            
            if not hadiah_res.data:
                messages.error(request, "Hadiah tidak ditemukan.")
                return redirect("rewards:katalog")

            # Cek periode aktif
            hari_ini = date.today()
            valid_start = date.fromisoformat(hadiah_res.data["valid_start_date"])
            program_end = date.fromisoformat(hadiah_res.data["program_end"])
            if not (valid_start <= hari_ini <= program_end):
                messages.error(request, f"Hadiah \"{hadiah_res.data['nama']}\" tidak tersedia pada periode ini.")
                return redirect("rewards:katalog")
                
            harga_miles = hadiah_res.data["miles"]
            member_res = settings.SUPABASE_CLIENT.table("member") \
                .select("award_miles") \
                .eq("email", user_email) \
                .single().execute()
                
            saldo_sekarang = member_res.data.get("award_miles", 0)

            if saldo_sekarang < harga_miles:
                messages.error(request, f"Saldo award miles tidak mencukupi. Dibutuhkan {harga_miles} miles, saldo Anda: {saldo_sekarang} miles.")
                return redirect("rewards:katalog")

            waktu_sekarang = datetime.datetime.now().isoformat()
            settings.SUPABASE_CLIENT.table("redeem").insert({
                "email_member": user_email,
                "kode_hadiah": kode_hadiah,
                "timestamp": waktu_sekarang
            }).execute()

            # Kurangi award_miles
            settings.SUPABASE_CLIENT.table("member").update({
                "award_miles": saldo_sekarang - harga_miles
            }).eq("email", user_email).execute()

            messages.success(request, f"SUKSES: Redeem hadiah \"{hadiah_res.data['nama']}\" berhasil. Award miles Anda berkurang {harga_miles} miles.")
            return redirect("rewards:katalog")

        except Exception as e:
            print(f"Error saat redeem: {e}")
            messages.error(request, "Terjadi kesalahan saat memproses penukaran.")
            return redirect("rewards:katalog")

    context = {"award_miles": 0, "hadiah_list": [], "riwayat_redeem": []}

    try:
            if role == "member":
                member_res = settings.SUPABASE_CLIENT.table("member") \
                    .select("award_miles") \
                    .eq("email", user_email) \
                    .single().execute()
                if member_res.data:
                    context["award_miles"] = member_res.data.get("award_miles", 0)

            hari_ini = date.today().isoformat()
            print("DEBUG hari_ini:", hari_ini)
            
            hadiah_res = settings.SUPABASE_CLIENT.table("hadiah") \
                .select("kode_hadiah, nama, miles, deskripsi, valid_start_date, program_end, id_penyedia") \
                .gte("program_end", hari_ini) \
                .execute()

            print("DEBUG hadiah_res:", hadiah_res.data)

            if hadiah_res.data:
                daftar_hadiah = hadiah_res.data
                for h in daftar_hadiah:
                    try:
                        mitra_res = settings.SUPABASE_CLIENT.table("mitra") \
                            .select("nama_mitra") \
                            .eq("id_penyedia", h["id_penyedia"]) \
                            .single().execute()
                        h['nama_mitra'] = mitra_res.data.get("nama_mitra", "-") if mitra_res.data else "-"
                    except:
                        h['nama_mitra'] = "-"
                context["hadiah_list"] = daftar_hadiah

            riwayat_res = settings.SUPABASE_CLIENT.table("redeem") \
                .select("timestamp, kode_hadiah, hadiah(miles, nama)") \
                .eq("email_member", user_email) \
                .order("timestamp", desc=True) \
                .execute()

            riwayat_list = []
            for r in riwayat_res.data or []:
                riwayat_list.append({
                    "nama_hadiah": r.get("hadiah", {}).get("nama", r["kode_hadiah"]) if r.get("hadiah") else r["kode_hadiah"],
                    "miles": r.get("hadiah", {}).get("miles", 0) if r.get("hadiah") else 0,
                    "tanggal": r["timestamp"][:16].replace("T", " "),
                })
            context["riwayat_redeem"] = riwayat_list

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

        id_package = request.POST.get("id_package")
        waktu_sekarang = datetime.datetime.now().isoformat()
        
        try:
            # Ambil data package
            pkg_res = settings.SUPABASE_CLIENT.table("award_miles_package") \
                .select("jumlah_award_miles") \
                .eq("id", id_package) \
                .single().execute()

            if not pkg_res.data:
                messages.error(request, "Paket tidak ditemukan.")
                return redirect("rewards:beli_package")

            jumlah_miles = pkg_res.data["jumlah_award_miles"]

            # Insert ke member_award_miles_package
            settings.SUPABASE_CLIENT.table("member_award_miles_package").insert({
                "id_award_miles_package": id_package,
                "email_member": user_email,
                "timestamp": waktu_sekarang
            }).execute()

            # Update award_miles dan total_miles member
            member_res = settings.SUPABASE_CLIENT.table("member") \
                .select("award_miles, total_miles") \
                .eq("email", user_email) \
                .single().execute()

            award_miles_baru = (member_res.data.get("award_miles") or 0) + jumlah_miles
            total_miles_baru = (member_res.data.get("total_miles") or 0) + jumlah_miles

            settings.SUPABASE_CLIENT.table("member").update({
                "award_miles": award_miles_baru,
                "total_miles": total_miles_baru
            }).eq("email", user_email).execute()

            messages.success(request, f"SUKSES: Pembelian package berhasil. Award miles dan total miles Anda bertambah {jumlah_miles:,} miles.")
            
        except Exception as e:
            print(f"Error Beli Package: {e}")
            messages.error(request, "Gagal memproses pembelian paket.")
            
        return redirect("rewards:beli_package")

    context = {"packages": [], "award_miles": 0}
    try:
        pkg_res = settings.SUPABASE_CLIENT.table("award_miles_package").select("*").execute()
        if pkg_res.data:
            context["packages"] = pkg_res.data

        member_res = settings.SUPABASE_CLIENT.table("member") \
            .select("award_miles") \
            .eq("email", user_email) \
            .single().execute()
        if member_res.data:
            context["award_miles"] = member_res.data.get("award_miles", 0)

    except Exception as e:
        print(f"Error fetch packages: {e}")

    return render(request, 'rewards/beli_package.html', context)

def info_tier(request):
    user_email = request.session.get("user_email")
    context = {"tiers": [], "id_tier_saya": None, "total_miles": 0}

    try:
        tier_res = settings.SUPABASE_CLIENT.table("tier").select("*").execute()
        if tier_res.data:
            tiers = tier_res.data
            tiers.sort(key=lambda x: x.get('id_tier', ''))
            context["tiers"] = tiers

        if user_email:
            member_res = settings.SUPABASE_CLIENT.table("member") \
                .select("id_tier, total_miles") \
                .eq("email", user_email) \
                .single().execute()
            if member_res.data:
                context["id_tier_saya"] = member_res.data.get("id_tier")
                context["total_miles"] = member_res.data.get("total_miles", 0)

    except Exception as e:
        print(f"Error fetch info tier: {e}")
    tier_berikutnya = None
    progress_persen = 0

    id_tier_saya = context.get("id_tier_saya")
    if id_tier_saya and context["tiers"]:
        tiers = context["tiers"]
        for i, t in enumerate(tiers):
            if t["id_tier"] == id_tier_saya:
                if i + 1 < len(tiers):
                    tier_berikutnya = tiers[i + 1]
                    total = context.get("total_miles", 0) or 0
                    target = tier_berikutnya["minimal_tier_miles"]
                    progress_persen = min(int((total / target) * 100), 100) if target > 0 else 100
                break

    context["tier_berikutnya"] = tier_berikutnya
    context["progress_persen"] = progress_persen
    return render(request, 'rewards/info_tier.html', context)

def laporan_transaksi(request):
    user_email = request.session.get("user_email")
    role = request.session.get("role")

    if not user_email:
        return redirect("authentication:login")

    transaksi_gabungan = []

    try:
        # Package
        pkg_query = settings.SUPABASE_CLIENT.table('member_award_miles_package') \
            .select('timestamp, email_member, id_award_miles_package, award_miles_package(jumlah_award_miles)')
        if role == 'member':
            pkg_query = pkg_query.eq('email_member', user_email)
        pkg_res = pkg_query.execute()
        for p in pkg_res.data or []:
            miles = p.get('award_miles_package', {}).get('jumlah_award_miles', 0) if p.get('award_miles_package') else 0
            transaksi_gabungan.append({
                'jenis': 'Beli Package',
                'aktor': p['email_member'],
                'detail': f"Beli {p['id_award_miles_package']}",
                'miles': f"+{miles:,}",
                'is_negative': False,
                'raw_time': p['timestamp'],
                'tanggal': p['timestamp'][:16].replace('T', ' '),
                'dapat_hapus': True,
            })

        # Redeem
        rdm_query = settings.SUPABASE_CLIENT.table('redeem') \
            .select('timestamp, email_member, kode_hadiah, hadiah(miles, nama)')
        if role == 'member':
            rdm_query = rdm_query.eq('email_member', user_email)
        rdm_res = rdm_query.execute()
        for r in rdm_res.data or []:
            miles = r.get('hadiah', {}).get('miles', 0) if r.get('hadiah') else 0
            nama_hadiah = r.get('hadiah', {}).get('nama', r['kode_hadiah']) if r.get('hadiah') else r['kode_hadiah']
            transaksi_gabungan.append({
                'jenis': 'Redeem Hadiah',
                'aktor': r['email_member'],
                'detail': f"Tukar {nama_hadiah}",
                'miles': f"-{miles:,}",
                'is_negative': True,
                'raw_time': r['timestamp'],
                'tanggal': r['timestamp'][:16].replace('T', ' '),
                'dapat_hapus': True,
            })

        # Transfer
        if role == 'member':
            tf_out = settings.SUPABASE_CLIENT.table('transfer').select('*').eq('email_member_1', user_email).execute()
            for t in tf_out.data or []:
                transaksi_gabungan.append({
                    'jenis': 'Transfer Keluar',
                    'aktor': t['email_member_2'],
                    'detail': t.get('catatan', '-'),
                    'miles': f"-{t['jumlah']:,}",
                    'is_negative': True,
                    'raw_time': t['timestamp'],
                    'tanggal': t['timestamp'][:16].replace('T', ' '),
                    'dapat_hapus': True,
                })
            tf_in = settings.SUPABASE_CLIENT.table('transfer').select('*').eq('email_member_2', user_email).execute()
            for t in tf_in.data or []:
                transaksi_gabungan.append({
                    'jenis': 'Transfer Masuk',
                    'aktor': t['email_member_1'],
                    'detail': t.get('catatan', '-'),
                    'miles': f"+{t['jumlah']:,}",
                    'is_negative': False,
                    'raw_time': t['timestamp'],
                    'tanggal': t['timestamp'][:16].replace('T', ' '),
                    'dapat_hapus': True,
                })
        else:
            tf_res = settings.SUPABASE_CLIENT.table('transfer').select('*').execute()
            for t in tf_res.data or []:
                transaksi_gabungan.append({
                    'jenis': 'Transfer Miles',
                    'aktor': f"{t['email_member_1']} → {t['email_member_2']}",
                    'detail': t.get('catatan', '-'),
                    'miles': f"{t['jumlah']:,}",
                    'is_negative': False,
                    'raw_time': t['timestamp'],
                    'tanggal': t['timestamp'][:16].replace('T', ' '),
                    'dapat_hapus': True,
                })

            # Klaim disetujui - tidak bisa dihapus
            klaim_res = settings.SUPABASE_CLIENT.table('claim_missing_miles') \
                .select('id, email_member, timestamp') \
                .eq('status_penerimaan', 'Disetujui').execute()
            for k in klaim_res.data or []:
                transaksi_gabungan.append({
                    'jenis': 'Klaim',
                    'aktor': k['email_member'],
                    'detail': '-',
                    'miles': '+1,000',
                    'is_negative': False,
                    'raw_time': k['timestamp'],
                    'tanggal': k['timestamp'][:16].replace('T', ' '),
                    'dapat_hapus': False,
                })

        transaksi_gabungan.sort(key=lambda x: x['raw_time'], reverse=True)

        # Stats untuk staf
        context_stats = {}
        if role == 'staf':
            total_miles_beredar = 0
            try:
                member_res = settings.SUPABASE_CLIENT.table('member').select('total_miles').execute()
                total_miles_beredar = sum(m.get('total_miles', 0) or 0 for m in member_res.data or [])
            except:
                pass

            bulan_ini = datetime.datetime.now().strftime('%Y-%m')
            total_redeem_bulan_ini = sum(
                1 for t in transaksi_gabungan
                if t['jenis'] == 'Redeem Hadiah' and t['tanggal'].startswith(bulan_ini)
            )
            total_klaim_disetujui = sum(
                1 for t in transaksi_gabungan if t['jenis'] == 'Klaim'
            )
            context_stats = {
                'total_miles_beredar': f"{total_miles_beredar:,}",
                'total_redeem_bulan_ini': f"{total_redeem_bulan_ini:,}",
                'total_klaim_disetujui': f"{total_klaim_disetujui:,}",
            }

    except Exception as e:
        print(f"Error fetching laporan transaksi: {e}")
        context_stats = {}
    
    top_member = []
    if role == 'staf':
        try:
            top_res = settings.SUPABASE_CLIENT.table('member') \
                .select('email, total_miles') \
                .order('total_miles', desc=True) \
                .limit(5) \
                .execute()
            top_member = top_res.data or []
        except:
            pass
    return render(request, 'rewards/laporan_transaksi.html', {
        'transaksi_list': transaksi_gabungan,
        'role': role,
        'top_member': top_member,
        **context_stats,
    })