import datetime
from django.contrib import messages  
import re
import psycopg2
import psycopg2.extras
from django.shortcuts import render, redirect
from django.contrib import messages   
from django.conf import settings
import psycopg2
import os

# Helper koneksi psycopg2
def get_db_connection():
    db = settings.DATABASES['default']
    return psycopg2.connect(
        host=db['HOST'],
        port=db.get('PORT', 5432),
        dbname=db['NAME'],
        user=db['USER'],
        password=db['PASSWORD'],
    )

def claim_miles(request):
    user_email = request.session.get("user_email")
    if not user_email:
        return redirect("login_view")

    is_staff = request.session.get("role") == "staf"
    status_filter = request.GET.get("status", "semua")
    context = {
        "current_status": status_filter,
        "claims": [],
        "is_staff": is_staff,
    }

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

        conn = None
        cur = None
        try:
            conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO claim_missing_miles 
                (email_member, nomor_tiket, maskapai, kelas_kabin, bandara_asal, 
                bandara_tujuan, tanggal_penerbangan, flight_number, pnr, timestamp, status_penerimaan)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_email, nomor_tiket_baru, maskapai_form, kelas_form,
                asal_form, tujuan_form, tanggal_form, flight_no_form,
                pnr_form, waktu_sekarang, "Menunggu"
            ))
            conn.commit()
            cur.close()
            conn.close()
            return redirect("miles:claim_miles")

        except Exception as e:
            if conn:
                conn.rollback()
            if cur:
                cur.close()
            if conn:
                conn.close()
            error_str = str(e)
            if "sudah pernah diajukan sebelumnya" in error_str:
                match = re.search(r'ERROR: Klaim untuk penerbangan.*?sebelumnya\.', error_str)
                context["error_message"] = match.group(0) if match else "Klaim ini sudah pernah diajukan sebelumnya."
            else:
                context["error_message"] = "Gagal menyimpan klaim."
                print(f"Error: {e}")

    try:
        maskapai_res = settings.SUPABASE_CLIENT.table("maskapai").select("*").execute()
        if maskapai_res.data:
            context["daftar_maskapai"] = maskapai_res.data

        bandara_res = settings.SUPABASE_CLIENT.table("bandara").select("*").execute()
        if bandara_res.data:
            context["daftar_bandara"] = bandara_res.data

        query = settings.SUPABASE_CLIENT.table("claim_missing_miles").select("*")
        if not is_staff:
            query = query.eq("email_member", user_email)
        if status_filter != "semua":
            query = query.eq("status_penerimaan", status_filter.capitalize())

        klaim_res = query.execute()
        if klaim_res.data:
            klaim_data = klaim_res.data
            klaim_data.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            for claim in klaim_data:
                claim["no_klaim"] = f"CLM-{str(claim['id']).zfill(3)}"
                claim["rute_gabungan"] = f"{claim['bandara_asal']} → {claim['bandara_tujuan']}"
                claim["tanggal_pengajuan_fmt"] = claim["timestamp"][:10] if claim.get("timestamp") else "-"
                claim["member_name"] = claim["email_member"].split("@")[0]
            context["claims"] = klaim_data

    except Exception as e:
        print(f"Error fetching claim miles data: {e}")

    return render(request, "miles/claim_miles.html", context)


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
            "maskapai": maskapai, "kelas_kabin": kelas,
            "bandara_asal": asal, "bandara_tujuan": tujuan,
            "tanggal_penerbangan": tanggal, "flight_number": flight_no,
            "pnr": pnr, "nomor_tiket": nomor_tiket_baru,
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


def approve_claim(request, claim_id):
    if request.session.get("role") != "staf":
        return redirect("miles:claim_miles")

    if request.method == "POST":
        conn = None
        cur = None
        try:
            conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
            cur = conn.cursor()

            # Ambil data klaim untuk keperluan pesan sukses
            cur.execute(
                "SELECT email_member, flight_number FROM claim_missing_miles WHERE id = %s",
                (claim_id,)
            )
            row = cur.fetchone()
            if not row:
                return redirect("miles:claim_miles")

            email_member, flight_number = row

            # Update status → trigger akan otomatis tambah 1000 miles ke member
            cur.execute(
                """
                UPDATE claim_missing_miles
                SET status_penerimaan = 'Disetujui'
                WHERE id = %s
                """,
                (claim_id,)
            )

            conn.commit()
            messages.success(
                request,
                f'SUKSES: Total miles Member "{email_member}" telah diperbarui. '
                f'Miles ditambahkan: 1000 miles dari klaim penerbangan "{flight_number}".'
            )

        except Exception as e:
            if conn:
                conn.rollback()
            messages.error(request, "Gagal menyetujui klaim.")
            print(f"Gagal setujui klaim: {e}")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return redirect("miles:claim_miles")


def reject_claim(request, claim_id):
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
        return redirect("authentication:login")

    if request.method == "POST":
        email_penerima = request.POST.get("email_penerima", "").strip().lower()
        jumlah = request.POST.get("jumlah_miles")
        catatan = request.POST.get("catatan", "").strip() or None

        if email_penerima == user_email:
            messages.error(request, "Tidak bisa transfer ke akun sendiri.")
            return redirect("miles:transfer_miles")

        try:
            jumlah = int(jumlah)
        except (ValueError, TypeError):
            messages.error(request, "Jumlah miles tidak valid.")
            return redirect("miles:transfer_miles")

        try:
            penerima_res = settings.SUPABASE_CLIENT.table("member").select("email").eq("email", email_penerima).execute()
            if not penerima_res.data:
                messages.error(request, "Email penerima tidak ditemukan di sistem.")
                return redirect("miles:transfer_miles")
        except Exception as e:
            messages.error(request, "Terjadi kesalahan sistem saat memvalidasi penerima.")
            return redirect("miles:transfer_miles")

        try:
            rpc_res = settings.SUPABASE_CLIENT.rpc("fungsi_proses_transfer_miles", {
                "p_pengirim": user_email,
                "p_penerima": email_penerima,
                "p_jumlah": jumlah,
                "p_catatan": catatan
            }).execute()
            messages.success(request, rpc_res.data)
            
        except Exception as e:
            error_message = str(e)
            if "ERROR: Saldo award miles tidak mencukupi" in error_message:
                match = re.search(r'(ERROR: Saldo award miles tidak mencukupi\..*?miles\.)', error_message)
                if match:
                    messages.error(request, match.group(1))
                else:
                    messages.error(request, "ERROR: Saldo award miles tidak mencukupi untuk melakukan transfer ini.")
            else:
                print(f"Gagal transfer miles: {e}")
                messages.error(request, "Terjadi kesalahan sistem saat memproses transfer.")

        return redirect("miles:transfer_miles")
    
    context = {"transfers": [], "award_miles": 0}

    try:
        member_res = settings.SUPABASE_CLIENT.table("member").select("award_miles").eq("email", user_email).single().execute()
        if member_res.data:
            context["award_miles"] = member_res.data.get("award_miles", 0)
    except Exception as e:
        print(f"Gagal ambil award miles: {e}")

    try:
        kirim_res = settings.SUPABASE_CLIENT.table("transfer").select("*").eq("email_member_1", user_email).execute()
        terima_res = settings.SUPABASE_CLIENT.table("transfer").select("*").eq("email_member_2", user_email).execute()

        transfers = []
        for t in kirim_res.data or []:
            transfers.append({
                "email_member": t["email_member_2"],
                "nama_member": t["email_member_2"].split("@")[0],
                "jumlah_miles": t["jumlah"],
                "catatan": t.get("catatan"),
                "tipe": "Kirim",
                "waktu_fmt": t["timestamp"][:16].replace("T", " ") if t.get("timestamp") else "-",
                "timestamp": t.get("timestamp", ""),
            })
        for t in terima_res.data or []:
            transfers.append({
                "email_member": t["email_member_1"],
                "nama_member": t["email_member_1"].split("@")[0],
                "jumlah_miles": t["jumlah"],
                "catatan": t.get("catatan"),
                "tipe": "Terima",
                "waktu_fmt": t["timestamp"][:16].replace("T", " ") if t.get("timestamp") else "-",
                "timestamp": t.get("timestamp", ""),
            })

        transfers.sort(key=lambda x: x["timestamp"], reverse=True)
        context["transfers"] = transfers

    except Exception as e:
        print(f"Gagal ambil riwayat transfer: {e}")

    return render(request, "miles/transfer_miles.html", context)

def laporan_transaksi(request):
    # Proteksi: hanya staf
    if request.session.get("role") != "staf":
        return redirect("miles:claim_miles")

    context = {"top5_members": [], "pesan_sukses": ""}

    conn   = None
    cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Panggil stored procedure get_top5_member_by_miles()
        cursor.execute("SELECT * FROM get_top5_member_by_miles()")
        rows = cursor.fetchall()
        top5 = [dict(row) for row in rows]

        if top5:
            pertama = top5[0]
            context["pesan_sukses"] = (
                f'SUKSES: Daftar Top 5 Member berdasarkan total miles berhasil diperbarui, '
                f'dengan peringkat pertama "{pertama["email"]}" '
                f'memiliki {pertama["total_miles"]} miles.'
            )

        context["top5_members"] = top5

    except Exception as e:
        print(f"Gagal ambil top 5 member: {e}")
        messages.error(request, "Gagal memuat data laporan.")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render(request, "miles/laporan_transaksi.html", context)