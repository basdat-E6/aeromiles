from django.contrib import messages  
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from .models import Hadiah, Penyedia, Mitra
import datetime
from datetime import date


def _get_penyedia_list():
    penyedia = []
    try:
        maskapai_res = settings.SUPABASE_CLIENT.table("maskapai").select("id_penyedia, nama_maskapai").execute()
        for m in maskapai_res.data or []:
            penyedia.append({"id_penyedia": m["id_penyedia"], "nama_penyedia": m["nama_maskapai"], "tipe": "airline"})
        mitra_res = settings.SUPABASE_CLIENT.table("mitra").select("id_penyedia, nama_mitra").execute()
        for m in mitra_res.data or []:
            penyedia.append({"id_penyedia": m["id_penyedia"], "nama_penyedia": m["nama_mitra"], "tipe": "partner"})
        penyedia.sort(key=lambda x: (x["tipe"], x["id_penyedia"]))
    except Exception as e:
        print(f"Error fetch penyedia: {e}")
    return penyedia


def hadiah_list(request):
    hadiah = []
    penyedia_list = _get_penyedia_list()
    penyedia_map = {p["id_penyedia"]: p for p in penyedia_list}
    try:
        h_res = settings.SUPABASE_CLIENT.table("hadiah").select("*").order("kode_hadiah").execute()
        for h in h_res.data or []:
            p = penyedia_map.get(h.get("id_penyedia"), {})
            h["nama_penyedia"] = p.get("nama_penyedia", "-")
            h["tipe_penyedia"] = p.get("tipe", "-")
            hadiah.append(h)
    except Exception as e:
        print(f"Error fetch hadiah: {e}")
    return render(request, "hadiah/list.html", {"hadiah": hadiah, "penyedia_list": penyedia_list})


def hadiah_create(request):
    if request.method == "POST":
        nama = request.POST.get("nama", "").strip()
        penyedia_id = request.POST.get("penyedia")
        miles = request.POST.get("miles")
        deskripsi = request.POST.get("deskripsi", "").strip()
        valid_start = request.POST.get("valid_start")
        valid_end = request.POST.get("valid_end")
        if nama and penyedia_id and miles and deskripsi and valid_start and valid_end:
            try:
                last = settings.SUPABASE_CLIENT.table("hadiah").select("kode_hadiah").order("kode_hadiah", desc=True).limit(1).execute()
                num = int(last.data[0]["kode_hadiah"].split("-")[1]) + 1 if last.data else 1
                kode = f"RWD-{num:03d}"
                settings.SUPABASE_CLIENT.table("hadiah").insert({
                    "kode_hadiah": kode, "nama": nama, "id_penyedia": int(penyedia_id),
                    "miles": int(miles), "deskripsi": deskripsi,
                    "valid_start_date": valid_start, "program_end": valid_end,
                }).execute()
            except Exception as e:
                print(f"Error create hadiah: {e}")
    return redirect("rewards:hadiah_list")


def hadiah_update(request, pk):
    if request.method == "POST":
        nama = request.POST.get("nama", "").strip()
        penyedia_id = request.POST.get("penyedia")
        miles = request.POST.get("miles")
        deskripsi = request.POST.get("deskripsi", "").strip()
        valid_start = request.POST.get("valid_start")
        valid_end = request.POST.get("valid_end")
        if nama and penyedia_id and miles and deskripsi and valid_start and valid_end:
            try:
                settings.SUPABASE_CLIENT.table("hadiah").update({
                    "nama": nama, "id_penyedia": int(penyedia_id), "miles": int(miles),
                    "deskripsi": deskripsi, "valid_start_date": valid_start, "program_end": valid_end,
                }).eq("kode_hadiah", pk).execute()
            except Exception as e:
                print(f"Error update hadiah: {e}")
    return redirect("rewards:hadiah_list")


def hadiah_delete(request, pk):
    if request.method == "POST":
        try:
            settings.SUPABASE_CLIENT.table("hadiah").delete().eq("kode_hadiah", pk).execute()
        except Exception as e:
            print(f"Error delete hadiah: {e}")
    return redirect("rewards:hadiah_list")


def mitra_list(request):
    mitras = []
    try:
        res = settings.SUPABASE_CLIENT.table("mitra").select("*").order("nama_mitra").execute()
        mitras = res.data or []
    except Exception as e:
        print(f"Error fetch mitra: {e}")
    return render(request, "mitra/list.html", {"mitras": mitras})


def mitra_create(request):
    if request.method == "POST":
        email_mitra = request.POST.get("email", "").strip()
        nama = request.POST.get("nama", "").strip()
        tanggal_kerja_sama = request.POST.get("tanggal_kerja_sama")
        if email_mitra and nama and tanggal_kerja_sama:
            try:
                cek = settings.SUPABASE_CLIENT.table("mitra").select("email_mitra").eq("email_mitra", email_mitra).execute()
                if cek.data:
                    return redirect("rewards:mitra_list")
                max_res = settings.SUPABASE_CLIENT.table("penyedia").select("id").order("id", desc=True).limit(1).execute()
                next_id = (max_res.data[0]["id"] + 1) if max_res.data else 1
                settings.SUPABASE_CLIENT.table("penyedia").insert({"id": next_id}).execute()
                settings.SUPABASE_CLIENT.table("mitra").insert({
                    "email_mitra": email_mitra, "id_penyedia": next_id,
                    "nama_mitra": nama, "tanggal_kerja_sama": tanggal_kerja_sama,
                }).execute()
            except Exception as e:
                print(f"Error create mitra: {e}")
    return redirect("rewards:mitra_list")


def mitra_update(request, email):
    if request.method == "POST":
        nama = request.POST.get("nama", "").strip()
        tanggal_kerja_sama = request.POST.get("tanggal_kerja_sama")
        if nama and tanggal_kerja_sama:
            try:
                settings.SUPABASE_CLIENT.table("mitra").update({
                    "nama_mitra": nama, "tanggal_kerja_sama": tanggal_kerja_sama,
                }).eq("email_mitra", email).execute()
            except Exception as e:
                print(f"Error update mitra: {e}")
    return redirect("rewards:mitra_list")


def mitra_delete(request, email):
    if request.method == "POST":
        try:
            mitra_res = settings.SUPABASE_CLIENT.table("mitra").select("id_penyedia").eq("email_mitra", email).execute()
            settings.SUPABASE_CLIENT.table("mitra").delete().eq("email_mitra", email).execute()
            if mitra_res.data:
                settings.SUPABASE_CLIENT.table("penyedia").delete().eq("id", mitra_res.data[0]["id_penyedia"]).execute()
        except Exception as e:
            print(f"Error delete mitra: {e}")
    return redirect("rewards:mitra_list")


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
                .select("miles, nama, valid_start_date, program_end") \
                .eq("kode_hadiah", kode_hadiah).single().execute()

            if not hadiah_res.data:
                messages.error(request, "Hadiah tidak ditemukan.")
                return redirect("rewards:katalog")

            hari_ini = date.today()
            valid_start = date.fromisoformat(hadiah_res.data["valid_start_date"])
            program_end = date.fromisoformat(hadiah_res.data["program_end"])
            if not (valid_start <= hari_ini <= program_end):
                messages.error(request, f"Hadiah \"{hadiah_res.data['nama']}\" tidak tersedia pada periode ini.")
                return redirect("rewards:katalog")

            harga_miles = hadiah_res.data["miles"]
            member_res = settings.SUPABASE_CLIENT.table("member").select("award_miles").eq("email", user_email).single().execute()
            saldo_sekarang = member_res.data.get("award_miles", 0)

            if saldo_sekarang < harga_miles:
                messages.error(request, f"Saldo award miles tidak mencukupi. Dibutuhkan {harga_miles} miles, saldo Anda: {saldo_sekarang} miles.")
                return redirect("rewards:katalog")

            waktu_sekarang = datetime.datetime.now().isoformat()
            settings.SUPABASE_CLIENT.table("redeem").insert({
                "email_member": user_email, "kode_hadiah": kode_hadiah, "timestamp": waktu_sekarang
            }).execute()

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
            member_res = settings.SUPABASE_CLIENT.table("member").select("award_miles").eq("email", user_email).single().execute()
            if member_res.data:
                context["award_miles"] = member_res.data.get("award_miles", 0)

        hari_ini = date.today().isoformat()
        hadiah_res = settings.SUPABASE_CLIENT.table("hadiah") \
            .select("kode_hadiah, nama, miles, deskripsi, valid_start_date, program_end, id_penyedia") \
            .gte("program_end", hari_ini).execute()

        if hadiah_res.data:
            daftar_hadiah = hadiah_res.data
            for h in daftar_hadiah:
                try:
                    mitra_res = settings.SUPABASE_CLIENT.table("mitra").select("nama_mitra").eq("id_penyedia", h["id_penyedia"]).single().execute()
                    h['nama_mitra'] = mitra_res.data.get("nama_mitra", "-") if mitra_res.data else "-"
                except:
                    h['nama_mitra'] = "-"
            context["hadiah_list"] = daftar_hadiah

        riwayat_res = settings.SUPABASE_CLIENT.table("redeem") \
            .select("timestamp, kode_hadiah, hadiah(miles, nama)") \
            .eq("email_member", user_email).order("timestamp", desc=True).execute()

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
            pkg_res = settings.SUPABASE_CLIENT.table("award_miles_package").select("jumlah_award_miles").eq("id", id_package).single().execute()
            if not pkg_res.data:
                messages.error(request, "Paket tidak ditemukan.")
                return redirect("rewards:beli_package")

            jumlah_miles = pkg_res.data["jumlah_award_miles"]
            settings.SUPABASE_CLIENT.table("member_award_miles_package").insert({
                "id_award_miles_package": id_package, "email_member": user_email, "timestamp": waktu_sekarang
            }).execute()

            member_res = settings.SUPABASE_CLIENT.table("member").select("award_miles, total_miles").eq("email", user_email).single().execute()
            award_miles_baru = (member_res.data.get("award_miles") or 0) + jumlah_miles
            total_miles_baru = (member_res.data.get("total_miles") or 0) + jumlah_miles
            settings.SUPABASE_CLIENT.table("member").update({
                "award_miles": award_miles_baru, "total_miles": total_miles_baru
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
        member_res = settings.SUPABASE_CLIENT.table("member").select("award_miles").eq("email", user_email).single().execute()
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
            member_res = settings.SUPABASE_CLIENT.table("member").select("id_tier, total_miles").eq("email", user_email).single().execute()
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
        pkg_query = settings.SUPABASE_CLIENT.table('member_award_miles_package') \
            .select('timestamp, email_member, id_award_miles_package, award_miles_package(jumlah_award_miles)')
        if role == 'member':
            pkg_query = pkg_query.eq('email_member', user_email)
        pkg_res = pkg_query.execute()
        for p in pkg_res.data or []:
            miles = p.get('award_miles_package', {}).get('jumlah_award_miles', 0) if p.get('award_miles_package') else 0
            transaksi_gabungan.append({
                'jenis': 'Beli Package', 'aktor': p['email_member'],
                'detail': f"Beli {p['id_award_miles_package']}", 'miles': f"+{miles:,}",
                'is_negative': False, 'raw_time': p['timestamp'],
                'tanggal': p['timestamp'][:16].replace('T', ' '), 'dapat_hapus': True,
            })

        rdm_query = settings.SUPABASE_CLIENT.table('redeem').select('timestamp, email_member, kode_hadiah, hadiah(miles, nama)')
        if role == 'member':
            rdm_query = rdm_query.eq('email_member', user_email)
        rdm_res = rdm_query.execute()
        for r in rdm_res.data or []:
            miles = r.get('hadiah', {}).get('miles', 0) if r.get('hadiah') else 0
            nama_hadiah = r.get('hadiah', {}).get('nama', r['kode_hadiah']) if r.get('hadiah') else r['kode_hadiah']
            transaksi_gabungan.append({
                'jenis': 'Redeem Hadiah', 'aktor': r['email_member'],
                'detail': f"Tukar {nama_hadiah}", 'miles': f"-{miles:,}",
                'is_negative': True, 'raw_time': r['timestamp'],
                'tanggal': r['timestamp'][:16].replace('T', ' '), 'dapat_hapus': True,
            })

        if role == 'member':
            tf_out = settings.SUPABASE_CLIENT.table('transfer').select('*').eq('email_member_1', user_email).execute()
            for t in tf_out.data or []:
                transaksi_gabungan.append({
                    'jenis': 'Transfer Keluar', 'aktor': t['email_member_2'],
                    'detail': t.get('catatan', '-'), 'miles': f"-{t['jumlah']:,}",
                    'is_negative': True, 'raw_time': t['timestamp'],
                    'tanggal': t['timestamp'][:16].replace('T', ' '), 'dapat_hapus': True,
                })
            tf_in = settings.SUPABASE_CLIENT.table('transfer').select('*').eq('email_member_2', user_email).execute()
            for t in tf_in.data or []:
                transaksi_gabungan.append({
                    'jenis': 'Transfer Masuk', 'aktor': t['email_member_1'],
                    'detail': t.get('catatan', '-'), 'miles': f"+{t['jumlah']:,}",
                    'is_negative': False, 'raw_time': t['timestamp'],
                    'tanggal': t['timestamp'][:16].replace('T', ' '), 'dapat_hapus': True,
                })
        else:
            tf_res = settings.SUPABASE_CLIENT.table('transfer').select('*').execute()
            for t in tf_res.data or []:
                transaksi_gabungan.append({
                    'jenis': 'Transfer Miles', 'aktor': f"{t['email_member_1']} → {t['email_member_2']}",
                    'detail': t.get('catatan', '-'), 'miles': f"{t['jumlah']:,}",
                    'is_negative': False, 'raw_time': t['timestamp'],
                    'tanggal': t['timestamp'][:16].replace('T', ' '), 'dapat_hapus': True,
                })

            klaim_res = settings.SUPABASE_CLIENT.table('claim_missing_miles').select('id, email_member, timestamp').eq('status_penerimaan', 'Disetujui').execute()
            for k in klaim_res.data or []:
                transaksi_gabungan.append({
                    'jenis': 'Klaim', 'aktor': k['email_member'], 'detail': '-',
                    'miles': '+1,000', 'is_negative': False, 'raw_time': k['timestamp'],
                    'tanggal': k['timestamp'][:16].replace('T', ' '), 'dapat_hapus': False,
                })

        transaksi_gabungan.sort(key=lambda x: x['raw_time'], reverse=True)

        context_stats = {}
        if role == 'staf':
            total_miles_beredar = 0
            try:
                member_res = settings.SUPABASE_CLIENT.table('member').select('total_miles').execute()
                total_miles_beredar = sum(m.get('total_miles', 0) or 0 for m in member_res.data or [])
            except:
                pass
            bulan_ini = datetime.datetime.now().strftime('%Y-%m')
            total_redeem_bulan_ini = sum(1 for t in transaksi_gabungan if t['jenis'] == 'Redeem Hadiah' and t['tanggal'].startswith(bulan_ini))
            total_klaim_disetujui = sum(1 for t in transaksi_gabungan if t['jenis'] == 'Klaim')
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
            top_res = settings.SUPABASE_CLIENT.table('member').select('email, total_miles').order('total_miles', desc=True).limit(5).execute()
            top_member = top_res.data or []
        except:
            pass

    return render(request, 'rewards/laporan_transaksi.html', {
        'transaksi_list': transaksi_gabungan,
        'role': role,
        'top_member': top_member,
        **context_stats,
    })