import datetime
from django.shortcuts import render, redirect
from django.conf import settings


def claim_miles(request):
    user_email = request.session.get("user_email")
    if not user_email:
        return redirect("login_view")

    # Cek apakah user adalah staf berdasarkan session role
    is_staff = request.session.get("role") == "staf"

    status_filter = request.GET.get("status", "semua")
    context = {
        "current_status": status_filter,
        "claims": [],
        "is_staff": is_staff,  # Kirim variabel ini ke template HTML
    }

    # LOGIKA POST: Hanya Member yang boleh bikin klaim baru
    if request.method == "POST" and not is_staff:
        maskapai_form = request.POST.get("maskapai")
        kelas_form = request.POST.get("kelas")
        asal_form = request.POST.get("asal")
        tujuan_form = request.POST.get("tujuan")
        tanggal_form = request.POST.get("tanggal")
        flight_no_form = request.POST.get("flight_no")
        pnr_form = request.POST.get("pnr")
        nomor_tiket_baru = request.POST.get("nomor_tiket")
        waktu_sekarang = datetime.datetime.now().isoformat()

        data_klaim_baru = {
            "email_member": user_email,
            "nomor_tiket": nomor_tiket_baru,
            "maskapai": maskapai_form,
            "kelas_kabin": kelas_form,
            "bandara_asal": asal_form,
            "bandara_tujuan": tujuan_form,
            "tanggal_penerbangan": tanggal_form,
            "flight_number": flight_no_form,
            "pnr": pnr_form,
            "timestamp": waktu_sekarang,
            "status_penerimaan": "Menunggu",
        }

        try:
            settings.SUPABASE_CLIENT.table("claim_missing_miles").insert(
                data_klaim_baru
            ).execute()
            return redirect("miles:claim_miles")
        except Exception as e:
            print(f"Gagal menyimpan klaim: {e}")

    # LOGIKA GET: Fetch data untuk render halaman
    try:
        maskapai_res = settings.SUPABASE_CLIENT.table("maskapai").select("*").execute()
        if maskapai_res.data:
            context["daftar_maskapai"] = maskapai_res.data

        bandara_res = settings.SUPABASE_CLIENT.table("bandara").select("*").execute()
        if bandara_res.data:
            context["daftar_bandara"] = bandara_res.data

        # Beda query untuk Staf dan Member
        query = settings.SUPABASE_CLIENT.table("claim_missing_miles").select("*")

        # Jika bukan staf, filter HANYA data miliknya
        if not is_staff:
            query = query.eq("email_member", user_email)

        # Filter berdasarkan status
        if status_filter != "semua":
            query = query.eq("status_penerimaan", status_filter.capitalize())

        klaim_res = query.execute()
        if klaim_res.data:
            klaim_data = klaim_res.data
            klaim_data.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            for claim in klaim_data:
                claim["no_klaim"] = f"CLM-{str(claim['id']).zfill(3)}"
                claim["rute_gabungan"] = (
                    f"{claim['bandara_asal']} → {claim['bandara_tujuan']}"
                )
                claim["tanggal_pengajuan_fmt"] = (
                    claim["timestamp"][:10] if claim.get("timestamp") else "-"
                )

                # Ambil nama depan dari email untuk ditampilkan ke staf
                claim["member_name"] = claim["email_member"].split("@")[0]

            context["claims"] = klaim_data

    except Exception as e:
        print(f"Error fetching claim miles data: {e}")

    return render(request, "miles/claim_miles.html", context)


# --- FUNGSI EXISTING UNTUK MEMBER (Edit & Delete) ---


def edit_claim(request):
    if request.method == "POST":
        claim_id = request.POST.get("claim_id")
        maskapai = request.POST.get("maskapai")
        kelas = request.POST.get("kelas")
        asal = request.POST.get("asal")
        tujuan = request.POST.get("tujuan")
        tanggal = request.POST.get("tanggal")
        flight_no = request.POST.get("flight_no")
        pnr = request.POST.get("pnr")
        nomor_tiket_baru = request.POST.get("nomor_tiket")

        if pnr:
            pnr = pnr.upper()

        updated_data = {
            "maskapai": maskapai,
            "kelas_kabin": kelas,
            "bandara_asal": asal,
            "bandara_tujuan": tujuan,
            "tanggal_penerbangan": tanggal,
            "flight_number": flight_no,
            "pnr": pnr,
            "nomor_tiket": nomor_tiket_baru,
        }

        try:
            settings.SUPABASE_CLIENT.table("claim_missing_miles").update(
                updated_data
            ).eq("id", claim_id).execute()
        except Exception as e:
            print(f"Gagal update: {e}")

    return redirect("miles:claim_miles")


def delete_claim(request):
    if request.method == "POST":
        claim_id = request.POST.get("claim_id")
        try:
            settings.SUPABASE_CLIENT.table("claim_missing_miles").delete().eq(
                "id", claim_id
            ).execute()
        except Exception as e:
            print(f"Gagal hapus: {e}")

    return redirect("miles:claim_miles")


# --- FUNGSI BARU KHUSUS STAF (Approve & Reject) ---


def approve_claim(request, claim_id):
    # Proteksi: Pastikan hanya staf yang bisa akses url ini
    if request.session.get("role") != "staf":
        return redirect("miles:claim_miles")

    if request.method == "POST":
        try:
            settings.SUPABASE_CLIENT.table("claim_missing_miles").update(
                {"status_penerimaan": "Disetujui"}
            ).eq("id", claim_id).execute()
        except Exception as e:
            print(f"Gagal setujui klaim: {e}")

    return redirect("miles:claim_miles")


def reject_claim(request, claim_id):
    # Proteksi: Pastikan hanya staf yang bisa akses url ini
    if request.session.get("role") != "staf":
        return redirect("miles:claim_miles")

    if request.method == "POST":
        try:
            settings.SUPABASE_CLIENT.table("claim_missing_miles").update(
                {"status_penerimaan": "Ditolak"}
            ).eq("id", claim_id).execute()
        except Exception as e:
            print(f"Gagal tolak klaim: {e}")

    return redirect("miles:claim_miles")


def transfer_miles(request):
    user_email = request.session.get("user_email")
    if not user_email:
        return redirect("login_view")

    # LOGIKA POST: Buat transfer baru
    if request.method == "POST":
        email_penerima = request.POST.get("email_penerima", "").strip().lower()
        jumlah = request.POST.get("jumlah_miles")
        catatan = request.POST.get("catatan", "").strip() or None

        # Validasi: tidak boleh transfer ke diri sendiri
        if email_penerima == user_email:
            return redirect("miles:transfer_miles")

        try:
            jumlah = int(jumlah)
        except (ValueError, TypeError):
            return redirect("miles:transfer_miles")

        # Validasi: penerima harus terdaftar sebagai member
        try:
            penerima_res = (
                settings.SUPABASE_CLIENT.table("member")
                .select("email")
                .eq("email", email_penerima)
                .execute()
            )
            if not penerima_res.data:
                # Penerima tidak ditemukan, redirect dengan error
                return redirect("miles:transfer_miles")
        except Exception as e:
            print(f"Gagal validasi penerima: {e}")
            return redirect("miles:transfer_miles")

        # Validasi: cek award miles pengirim mencukupi
        try:
            pengirim_res = (
                settings.SUPABASE_CLIENT.table("member")
                .select("award_miles")
                .eq("email", user_email)
                .single()
                .execute()
            )
            award_miles_pengirim = pengirim_res.data.get("award_miles", 0)
            if award_miles_pengirim < jumlah:
                return redirect("miles:transfer_miles")
        except Exception as e:
            print(f"Gagal cek miles pengirim: {e}")
            return redirect("miles:transfer_miles")

        # Simpan transaksi transfer
        try:
            waktu_sekarang = datetime.datetime.now().isoformat()
            settings.SUPABASE_CLIENT.table("transfer").insert(
                {
                    "email_member_1": user_email,
                    "email_member_2": email_penerima,
                    "jumlah": jumlah,
                    "catatan": catatan,
                    "timestamp": waktu_sekarang,
                }
            ).execute()

            # Kurangi miles pengirim
            settings.SUPABASE_CLIENT.table("member").update(
                {"award_miles": award_miles_pengirim - jumlah}
            ).eq("email", user_email).execute()

            # Tambah miles penerima
            penerima_miles_res = (
                settings.SUPABASE_CLIENT.table("member")
                .select("award_miles")
                .eq("email", email_penerima)
                .single()
                .execute()
            )
            award_miles_penerima = penerima_miles_res.data.get("award_miles", 0)
            settings.SUPABASE_CLIENT.table("member").update(
                {"award_miles": award_miles_penerima + jumlah}
            ).eq("email", email_penerima).execute()

        except Exception as e:
            print(f"Gagal transfer miles: {e}")

        return redirect("miles:transfer_miles")

    # LOGIKA GET: Fetch data untuk render halaman
    context = {"transfers": [], "award_miles": 0}

    try:
        # Ambil award miles milik user
        member_res = (
            settings.SUPABASE_CLIENT.table("member")
            .select("award_miles")
            .eq("email", user_email)
            .single()
            .execute()
        )
        if member_res.data:
            context["award_miles"] = member_res.data.get("award_miles", 0)
    except Exception as e:
        print(f"Gagal ambil award miles: {e}")

    try:
        # Ambil semua transfer yang melibatkan user (sebagai pengirim atau penerima)
        kirim_res = (
            settings.SUPABASE_CLIENT.table("transfer")
            .select("*")
            .eq("email_member_1", user_email)
            .execute()
        )
        terima_res = (
            settings.SUPABASE_CLIENT.table("transfer")
            .select("*")
            .eq("email_member_2", user_email)
            .execute()
        )

        transfers = []

        for t in kirim_res.data or []:
            transfers.append(
                {
                    "email_member": t["email_member_2"],
                    "nama_member": t["email_member_2"].split("@")[0],
                    "jumlah_miles": t["jumlah"],
                    "catatan": t.get("catatan"),
                    "tipe": "Kirim",
                    "waktu_fmt": (
                        t["timestamp"][:16].replace("T", " ")
                        if t.get("timestamp")
                        else "-"
                    ),
                    "timestamp": t.get("timestamp", ""),
                }
            )

        for t in terima_res.data or []:
            transfers.append(
                {
                    "email_member": t["email_member_1"],
                    "nama_member": t["email_member_1"].split("@")[0],
                    "jumlah_miles": t["jumlah"],
                    "catatan": t.get("catatan"),
                    "tipe": "Terima",
                    "waktu_fmt": (
                        t["timestamp"][:16].replace("T", " ")
                        if t.get("timestamp")
                        else "-"
                    ),
                    "timestamp": t.get("timestamp", ""),
                }
            )

        # Urutkan dari terbaru
        transfers.sort(key=lambda x: x["timestamp"], reverse=True)
        context["transfers"] = transfers

    except Exception as e:
        print(f"Gagal ambil riwayat transfer: {e}")

    return render(request, "miles/transfer_miles.html", context)
