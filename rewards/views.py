import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings

def hadiah_list(request):
    penyedia_id = request.GET.get('penyedia')
    status = request.GET.get('status')
    hari_ini = datetime.date.today().isoformat()

    hadiah_data = []
    penyedia_list = []

    try:
        query = settings.SUPABASE_CLIENT.table('hadiah').select('*, penyedia(nama_penyedia)')

        if penyedia_id:
            query = query.eq('id_penyedia', penyedia_id)

        if status == 'aktif':
            query = query.gte('program_end', hari_ini)
        elif status == 'expired':
            query = query.lt('program_end', hari_ini)

        hadiah_res = query.execute()
        if hadiah_res.data:
            hadiah_data = hadiah_res.data

        penyedia_res = settings.SUPABASE_CLIENT.table('penyedia').select('*').execute()
        if penyedia_res.data:
            penyedia_list = penyedia_res.data

    except Exception as e:
        print(f"Error fetch hadiah: {e}")

    return render(request, 'hadiah/list.html', {
        'hadiah': hadiah_data,
        'penyedia_list': penyedia_list
    })

def hadiah_create(request):
    if request.method == 'POST':
        try:
            settings.SUPABASE_CLIENT.table('hadiah').insert({
                "nama": request.POST.get('nama'),
                "miles": request.POST.get('miles'),
                "deskripsi": request.POST.get('deskripsi'),
                "valid_start_date": request.POST.get('valid_start_date'),
                "program_end": request.POST.get('program_end'),
                "id_penyedia": request.POST.get('id_penyedia')
            }).execute()
            messages.success(request, "Hadiah berhasil ditambahkan!")
            return redirect('rewards:hadiah_list')
        except Exception as e:
            print(f"Gagal tambah hadiah: {e}")
            messages.error(request, "Gagal menambahkan hadiah.")

    penyedia_list = []
    try:
        res = settings.SUPABASE_CLIENT.table('penyedia').select('*').execute()
        penyedia_list = res.data or []
    except Exception as e:
        pass

    return render(request, 'hadiah/form.html', {
        'title': 'Tambah Hadiah',
        'penyedia_list': penyedia_list
    })

def hadiah_update(request, pk):
    if request.method == 'GET':
        try:
            hadiah_res = settings.SUPABASE_CLIENT.table('hadiah').select('*').eq('kode_hadiah', pk).single().execute()
            penyedia_res = settings.SUPABASE_CLIENT.table('penyedia').select('*').execute()
            
            return render(request, 'hadiah/form.html', {
                'title': 'Edit Hadiah',
                'hadiah': hadiah_res.data,
                'penyedia_list': penyedia_res.data or []
            })
        except Exception as e:
            print(f"Error load hadiah edit: {e}")
            return redirect('rewards:hadiah_list')

    elif request.method == 'POST':
        try:
            settings.SUPABASE_CLIENT.table('hadiah').update({
                "nama": request.POST.get('nama'),
                "miles": request.POST.get('miles'),
                "deskripsi": request.POST.get('deskripsi'),
                "valid_start_date": request.POST.get('valid_start_date'),
                "program_end": request.POST.get('program_end'),
                "id_penyedia": request.POST.get('id_penyedia')
            }).eq('kode_hadiah', pk).execute()
            
            messages.success(request, "Hadiah berhasil diperbarui!")
        except Exception as e:
            print(f"Gagal update hadiah: {e}")
            messages.error(request, "Gagal memperbarui hadiah.")
            
        return redirect('rewards:hadiah_list')

def hadiah_delete(request, pk):
    try:
        hari_ini = datetime.date.today().isoformat()
        hadiah_res = settings.SUPABASE_CLIENT.table('hadiah').select('program_end').eq('kode_hadiah', pk).single().execute()
        
        if hadiah_res.data:
            program_end = hadiah_res.data['program_end']
            if program_end < hari_ini:
                settings.SUPABASE_CLIENT.table('hadiah').delete().eq('kode_hadiah', pk).execute()
                messages.success(request, "Hadiah berhasil dihapus!")
            else:
                # Belum expired, tolak
                messages.error(request, "Gagal! Hadiah masih aktif dan belum kedaluwarsa.")
                
    except Exception as e:
        print(f"Error delete hadiah: {e}")

    return redirect('rewards:hadiah_list')

def mitra_list(request):
    mitras = []
    try:
        mitra_res = settings.SUPABASE_CLIENT.table('mitra').select('*').execute()
        mitras = mitra_res.data or []
    except Exception as e:
        print(f"Error load mitra: {e}")
        
    return render(request, 'mitra/list.html', {'mitras': mitras})

def mitra_create(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        nama = request.POST.get('nama')
        deskripsi = request.POST.get('deskripsi', '')
        
        try:
            settings.SUPABASE_CLIENT.table('mitra').insert({
                "email": email,
                "nama": nama,
                "deskripsi": deskripsi
            }).execute()

            settings.SUPABASE_CLIENT.table('penyedia').insert({
                "email_mitra": email,
                "nama_penyedia": nama
            }).execute()

            messages.success(request, "Mitra dan Penyedia berhasil ditambahkan!")
            return redirect('rewards:mitra_list')
        except Exception as e:
            print(f"Error tambah mitra: {e}")
            messages.error(request, "Gagal menambahkan Mitra. Pastikan email belum terdaftar.")

    return render(request, 'mitra/create.html')

def mitra_update(request, email):
    if request.method == 'GET':
        try:
            mitra_res = settings.SUPABASE_CLIENT.table('mitra').select('*').eq('email', email).single().execute()
            return render(request, 'mitra/update.html', {'mitra': mitra_res.data})
        except Exception as e:
            return redirect('rewards:mitra_list')

    elif request.method == 'POST':
        nama = request.POST.get('nama')
        deskripsi = request.POST.get('deskripsi', '')
        
        try:
            settings.SUPABASE_CLIENT.table('mitra').update({
                "nama": nama,
                "deskripsi": deskripsi
            }).eq('email', email).execute()

            settings.SUPABASE_CLIENT.table('penyedia').update({
                "nama_penyedia": nama
            }).eq('email_mitra', email).execute()

            messages.success(request, "Data Mitra berhasil diperbarui!")
        except Exception as e:
            print(f"Error update mitra: {e}")
            messages.error(request, "Gagal memperbarui data Mitra.")
            
        return redirect('rewards:mitra_list')

def mitra_delete(request, email):
    if request.method == 'POST':
        try:
            settings.SUPABASE_CLIENT.table('mitra').delete().eq('email', email).execute()
            messages.success(request, "Mitra berhasil dihapus!")
        except Exception as e:
            print(f"Error delete mitra: {e}")
            messages.error(request, "Gagal menghapus Mitra.")
            
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