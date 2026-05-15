from django.shortcuts import render, redirect, get_object_or_404
from datetime import date
from django.conf import settings

sb = settings.SUPABASE_CLIENT


def _get_penyedia_list():
    """Gabungkan penyedia dari maskapai + mitra berdasarkan id_penyedia."""
    penyedia = []
    try:
        # Maskapai: id_penyedia 1,2,3,4,5
        maskapai_res = (
            sb.table("maskapai").select("id_penyedia, nama_maskapai").execute()
        )
        for m in maskapai_res.data or []:
            penyedia.append(
                {
                    "id_penyedia": m["id_penyedia"],
                    "nama_penyedia": m["nama_maskapai"],
                    "tipe": "airline",
                }
            )
        # Mitra: id_penyedia 3,4,6,7,8
        mitra_res = sb.table("mitra").select("id_penyedia, nama_mitra").execute()
        for m in mitra_res.data or []:
            penyedia.append(
                {
                    "id_penyedia": m["id_penyedia"],
                    "nama_penyedia": m["nama_mitra"],
                    "tipe": "partner",
                }
            )
        penyedia.sort(key=lambda x: (x["tipe"], x["id_penyedia"]))
    except Exception as e:
        print(f"Error fetch penyedia: {e}")
    return penyedia


def _get_nama_penyedia(id_penyedia):
    """Cari nama penyedia dari maskapai atau mitra berdasarkan id_penyedia."""
    try:
        m = (
            sb.table("maskapai")
            .select("nama_maskapai")
            .eq("id_penyedia", id_penyedia)
            .execute()
        )
        if m.data:
            return m.data[0]["nama_maskapai"], "airline"
        mt = (
            sb.table("mitra")
            .select("nama_mitra")
            .eq("id_penyedia", id_penyedia)
            .execute()
        )
        if mt.data:
            return mt.data[0]["nama_mitra"], "partner"
    except Exception as e:
        print(f"Error get nama penyedia: {e}")
    return "-", "-"


def hadiah_list(request):
    """READ: ambil hadiah dari Supabase, resolve nama penyedia dari maskapai/mitra."""
    hadiah = []
    penyedia_list = _get_penyedia_list()

    # Buat lookup dict id_penyedia → {nama, tipe}
    penyedia_map = {p["id_penyedia"]: p for p in penyedia_list}

    try:
        h_res = sb.table("hadiah").select("*").order("kode_hadiah").execute()
        for h in h_res.data or []:
            p = penyedia_map.get(h.get("id_penyedia"), {})
            h["nama_penyedia"] = p.get("nama_penyedia", "-")
            h["tipe_penyedia"] = p.get("tipe", "-")
            hadiah.append(h)
    except Exception as e:
        print(f"Error fetch hadiah: {e}")

    return render(
        request,
        "hadiah/list.html",
        {
            "hadiah": hadiah,
            "penyedia_list": penyedia_list,
        },
    )


def hadiah_create(request):
    """CREATE: simpan hadiah baru ke Supabase."""
    if request.method == "POST":
        nama = request.POST.get("nama", "").strip()
        penyedia_id = request.POST.get("penyedia")
        miles = request.POST.get("miles")
        deskripsi = request.POST.get("deskripsi", "").strip()
        valid_start = request.POST.get("valid_start")
        valid_end = request.POST.get("valid_end")

        if valid_start and valid_end and valid_start > valid_end:
            from django.contrib import messages

            messages.error(
                request, "Tanggal mulai tidak boleh lebih dari tanggal selesai."
            )
            return redirect("rewards:hadiah_list")

        if nama and penyedia_id and miles and deskripsi and valid_start and valid_end:
            try:
                # Generate kode otomatis
                last = (
                    sb.table("hadiah")
                    .select("kode_hadiah")
                    .order("kode_hadiah", desc=True)
                    .limit(1)
                    .execute()
                )
                if last.data:
                    num = int(last.data[0]["kode_hadiah"].split("-")[1]) + 1
                else:
                    num = 1
                kode = f"RWD-{num:03d}"

                sb.table("hadiah").insert(
                    {
                        "kode_hadiah": kode,
                        "nama": nama,
                        "id_penyedia": int(penyedia_id),
                        "miles": int(miles),
                        "deskripsi": deskripsi,
                        "valid_start_date": valid_start,
                        "program_end": valid_end,
                    }
                ).execute()
            except Exception as e:
                print(f"Error create hadiah: {e}")

    return redirect("rewards:hadiah_list")


def hadiah_update(request, pk):
    """UPDATE: edit hadiah di Supabase."""
    if request.method == "POST":
        nama = request.POST.get("nama", "").strip()
        penyedia_id = request.POST.get("penyedia")
        miles = request.POST.get("miles")
        deskripsi = request.POST.get("deskripsi", "").strip()
        valid_start = request.POST.get("valid_start")
        valid_end = request.POST.get("valid_end")

        if valid_start and valid_end and valid_start > valid_end:
            from django.contrib import messages

            messages.error(
                request, "Tanggal mulai tidak boleh lebih dari tanggal selesai."
            )
            return redirect("rewards:hadiah_list")

        if nama and penyedia_id and miles and deskripsi and valid_start and valid_end:
            try:
                sb.table("hadiah").update(
                    {
                        "nama": nama,
                        "id_penyedia": int(penyedia_id),
                        "miles": int(miles),
                        "deskripsi": deskripsi,
                        "valid_start_date": valid_start,
                        "program_end": valid_end,
                    }
                ).eq("kode_hadiah", pk).execute()
            except Exception as e:
                print(f"Error update hadiah: {e}")

    return redirect("rewards:hadiah_list")


def hadiah_delete(request, pk):
    """DELETE: hapus hadiah dari Supabase."""
    if request.method == "POST":
        try:
            sb.table("hadiah").delete().eq("kode_hadiah", pk).execute()
        except Exception as e:
            print(f"Error delete hadiah: {e}")

    return redirect("rewards:hadiah_list")


def mitra_list(request):
    """READ: ambil mitra dari Supabase."""
    mitras = []
    try:
        res = sb.table("mitra").select("*").order("nama_mitra").execute()
        mitras = res.data or []
    except Exception as e:
        print(f"Error fetch mitra: {e}")
    return render(request, "mitra/list.html", {"mitras": mitras})


def mitra_create(request):
    """CREATE: tambah mitra baru ke Supabase."""
    if request.method == "POST":
        email_mitra = request.POST.get("email", "").strip()
        nama = request.POST.get("nama", "").strip()
        tanggal_kerja_sama = request.POST.get("tanggal_kerja_sama")

        if email_mitra and nama and tanggal_kerja_sama:
            try:
                # Cek email sudah ada
                cek = (
                    sb.table("mitra")
                    .select("email_mitra")
                    .eq("email_mitra", email_mitra)
                    .execute()
                )
                if cek.data:
                    return redirect("rewards:mitra_list")

                # Ambil id terbesar dari penyedia lalu +1
                max_res = (
                    sb.table("penyedia")
                    .select("id")
                    .order("id", desc=True)
                    .limit(1)
                    .execute()
                )
                next_id = (max_res.data[0]["id"] + 1) if max_res.data else 1

                # Insert ke penyedia dengan id yang sudah ditentukan
                sb.table("penyedia").insert({"id": next_id}).execute()

                # Insert mitra
                sb.table("mitra").insert(
                    {
                        "email_mitra": email_mitra,
                        "id_penyedia": next_id,
                        "nama_mitra": nama,
                        "tanggal_kerja_sama": tanggal_kerja_sama,
                    }
                ).execute()

            except Exception as e:
                print(f"Error create mitra: {e}")

    return redirect("rewards:mitra_list")


def mitra_update(request, email):
    """UPDATE: edit mitra di Supabase."""
    if request.method == "POST":
        nama = request.POST.get("nama", "").strip()
        tanggal_kerja_sama = request.POST.get("tanggal_kerja_sama")

        if nama and tanggal_kerja_sama:
            try:
                sb.table("mitra").update(
                    {
                        "nama_mitra": nama,
                        "tanggal_kerja_sama": tanggal_kerja_sama,
                    }
                ).eq("email_mitra", email).execute()
            except Exception as e:
                print(f"Error update mitra: {e}")

    return redirect("rewards:mitra_list")


def mitra_delete(request, email):
    """DELETE: hapus mitra dari Supabase."""
    if request.method == "POST":
        try:
            # Ambil id_penyedia dulu untuk hapus entri penyedia juga
            mitra_res = (
                sb.table("mitra")
                .select("id_penyedia")
                .eq("email_mitra", email)
                .execute()
            )

            sb.table("mitra").delete().eq("email_mitra", email).execute()

            # Hapus dari penyedia pakai kolom 'id' (bukan id_penyedia)
            if mitra_res.data:
                sb.table("penyedia").delete().eq(
                    "id", mitra_res.data[0]["id_penyedia"]
                ).execute()
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
            hadiah_res = (
                settings.SUPABASE_CLIENT.table("hadiah")
                .select("miles")
                .eq("kode_hadiah", kode_hadiah)
                .single()
                .execute()
            )

            if not hadiah_res.data:
                messages.error(request, "Hadiah tidak ditemukan.")
                return redirect("rewards:katalog")

            harga_miles = hadiah_res.data["miles"]
            member_res = (
                settings.SUPABASE_CLIENT.table("member")
                .select("award_miles")
                .eq("email", user_email)
                .single()
                .execute()
            )

            saldo_sekarang = member_res.data.get("award_miles", 0)

            if saldo_sekarang < harga_miles:
                messages.error(
                    request, "Award miles Anda tidak mencukupi untuk hadiah ini!"
                )
                return redirect("rewards:katalog")

            waktu_sekarang = datetime.datetime.now().isoformat()
            settings.SUPABASE_CLIENT.table("redeem").insert(
                {
                    "email_member": user_email,
                    "kode_hadiah": kode_hadiah,
                    "timestamp": waktu_sekarang,
                }
            ).execute()

            messages.success(request, "Berhasil menukarkan hadiah!")
            return redirect("rewards:katalog")

        except Exception as e:
            print(f"Error saat redeem: {e}")
            messages.error(request, "Terjadi kesalahan saat memproses penukaran.")
            return redirect("rewards:katalog")

    context = {"award_miles": 0, "hadiah_list": []}

    try:
        if role == "member":
            member_res = (
                settings.SUPABASE_CLIENT.table("member")
                .select("award_miles")
                .eq("email", user_email)
                .single()
                .execute()
            )
            if member_res.data:
                context["award_miles"] = member_res.data.get("award_miles", 0)

        hari_ini = datetime.date.today().isoformat()

        hadiah_res = (
            settings.SUPABASE_CLIENT.table("hadiah")
            .select("*, penyedia(nama_penyedia)")
            .gte("program_end", hari_ini)
            .execute()
        )

        if hadiah_res.data:
            daftar_hadiah = hadiah_res.data
            for h in daftar_hadiah:
                h["nama_mitra"] = h.get("penyedia", {}).get("nama_penyedia", "-")
            context["hadiah_list"] = daftar_hadiah

    except Exception as e:
        print(f"Error fetch katalog: {e}")

    return render(request, "rewards/katalog.html", context)


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
            settings.SUPABASE_CLIENT.table("member_award_miles_package").insert(
                {
                    "email_member": user_email,
                    "nama_paket": nama_paket,
                    "timestamp": waktu_sekarang,
                }
            ).execute()

            messages.success(request, f"Berhasil membeli paket {nama_paket}!")
        except Exception as e:
            print(f"Error Beli Package: {e}")
            messages.error(request, "Gagal memproses pembelian paket.")

        return redirect("rewards:beli_package")

    context = {"packages": []}
    try:
        pkg_res = (
            settings.SUPABASE_CLIENT.table("award_miles_package").select("*").execute()
        )
        if pkg_res.data:
            context["packages"] = pkg_res.data
    except Exception as e:
        print(f"Error fetch packages: {e}")

    return render(request, "rewards/beli_package.html", context)


def info_tier(request):
    context = {"tiers": []}
    try:
        tier_res = settings.SUPABASE_CLIENT.table("tier").select("*").execute()

        if tier_res.data:
            tiers = tier_res.data
            tiers.sort(key=lambda x: x.get("id_tier", ""))
            context["tiers"] = tiers

    except Exception as e:
        print(f"Error fetch info tier: {e}")

    return render(request, "rewards/info_tier.html", context)


def laporan_transaksi(request):
    user_email = request.session.get("user_email")
    role = request.session.get("role")

    if not user_email:
        return redirect("authentication:login")

    transaksi_gabungan = []

    try:
        pkg_query = settings.SUPABASE_CLIENT.table("member_award_miles_package").select(
            "timestamp, email_member, nama_paket, award_miles_package(jumlah_award_miles)"
        )

        if role == "member":
            pkg_query = pkg_query.eq("email_member", user_email)

        pkg_res = pkg_query.execute()
        for p in pkg_res.data:
            miles = (
                p.get("award_miles_package", {}).get("jumlah_award_miles", 0)
                if p.get("award_miles_package")
                else 0
            )
            transaksi_gabungan.append(
                {
                    "jenis": "Beli Package",
                    "aktor": p["email_member"],
                    "detail": f"Beli {p['nama_paket']}",
                    "miles": f"+{miles:,}",
                    "is_negative": False,
                    "raw_time": p["timestamp"],
                    "tanggal": p["timestamp"][:16].replace("T", " "),
                }
            )

        rdm_query = settings.SUPABASE_CLIENT.table("redeem").select(
            "timestamp, email_member, kode_hadiah, hadiah(miles, nama)"
        )

        if role == "member":
            rdm_query = rdm_query.eq("email_member", user_email)

        rdm_res = rdm_query.execute()
        for r in rdm_res.data:
            miles = r.get("hadiah", {}).get("miles", 0) if r.get("hadiah") else 0
            nama_hadiah = r.get("hadiah", {}).get("nama", r["kode_hadiah"])
            transaksi_gabungan.append(
                {
                    "jenis": "Redeem Hadiah",
                    "aktor": r["email_member"],
                    "detail": f"Tukar {nama_hadiah}",
                    "miles": f"-{miles:,}",
                    "is_negative": True,
                    "raw_time": r["timestamp"],
                    "tanggal": r["timestamp"][:16].replace("T", " "),
                }
            )

        if role == "member":
            tf_out = (
                settings.SUPABASE_CLIENT.table("transfer")
                .select("*")
                .eq("email_member_1", user_email)
                .execute()
            )
            for t in tf_out.data:
                transaksi_gabungan.append(
                    {
                        "jenis": "Transfer Keluar",
                        "aktor": t["email_member_2"],
                        "detail": t.get("catatan", "-"),
                        "miles": f"-{t['jumlah']:,}",
                        "is_negative": True,
                        "raw_time": t["timestamp"],
                        "tanggal": t["timestamp"][:16].replace("T", " "),
                    }
                )

            tf_in = (
                settings.SUPABASE_CLIENT.table("transfer")
                .select("*")
                .eq("email_member_2", user_email)
                .execute()
            )
            for t in tf_in.data:
                transaksi_gabungan.append(
                    {
                        "jenis": "Transfer Masuk",
                        "aktor": t["email_member_1"],
                        "detail": t.get("catatan", "-"),
                        "miles": f"+{t['jumlah']:,}",
                        "is_negative": False,
                        "raw_time": t["timestamp"],
                        "tanggal": t["timestamp"][:16].replace("T", " "),
                    }
                )
        else:
            tf_res = settings.SUPABASE_CLIENT.table("transfer").select("*").execute()
            for t in tf_res.data:
                transaksi_gabungan.append(
                    {
                        "jenis": "Transfer Miles",
                        "aktor": f"{t['email_member_1']} ➔ {t['email_member_2']}",
                        "detail": t.get("catatan", "-"),
                        "miles": f"{t['jumlah']:,}",
                        "is_negative": False,  # Staf cukup lihat nominal mentah
                        "raw_time": t["timestamp"],
                        "tanggal": t["timestamp"][:16].replace("T", " "),
                    }
                )

        transaksi_gabungan.sort(key=lambda x: x["raw_time"], reverse=True)

    except Exception as e:
        print(f"Error fetching laporan transaksi: {e}")

    return render(
        request,
        "rewards/laporan_transaksi.html",
        {"transaksi_list": transaksi_gabungan, "role": role},
    )
