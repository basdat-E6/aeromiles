import datetime
from django.contrib import messages  
import re
import psycopg2
import psycopg2.extras
from django.shortcuts import render, redirect
from django.conf import settings

def get_db_connection():
    """Membuka koneksi langsung ke PostgreSQL menggunakan DATABASE_URL dari settings.py"""
    return psycopg2.connect(settings.DATABASE_URL)


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
        waktu_sekarang = datetime.datetime.now()

        conn = None
        cur = None
        try:
            conn = get_db_connection()
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
            return redirect("miles:claim_miles")

        except Exception as e:
            if conn:
                conn.rollback()
            error_str = str(e)
            if "sudah pernah diajukan sebelumnya" in error_str or "unique_claim_penerbangan" in error_str:
                context["error_message"] = "Klaim untuk penerbangan ini sudah pernah diajukan sebelumnya."
            else:
                context["error_message"] = "Gagal menyimpan klaim."
                print(f"Error insert claim: {e}")
        finally:
            if cur: cur.close()
            if conn: conn.close()

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Ambil daftar maskapai
        cur.execute("SELECT * FROM maskapai")
        context["daftar_maskapai"] = cur.fetchall()

        # Ambil daftar bandara
        cur.execute("SELECT * FROM bandara")
        context["daftar_bandara"] = cur.fetchall()

        # Ambil data claim
        query = "SELECT * FROM claim_missing_miles"
        params = []
        conditions = []

        if not is_staff:
            conditions.append("email_member = %s")
            params.append(user_email)
        
        if status_filter != "semua":
            conditions.append("status_penerimaan = %s")
            params.append(status_filter.capitalize())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp DESC"
        
        cur.execute(query, params)
        klaim_data = cur.fetchall()

        for claim in klaim_data:
            claim["no_klaim"] = f"CLM-{str(claim['id']).zfill(3)}"
            claim["rute_gabungan"] = f"{claim['bandara_asal']} → {claim['bandara_tujuan']}"
            
            # Format datetime
            ts = claim.get("timestamp")
            claim["tanggal_pengajuan_fmt"] = ts.strftime('%Y-%m-%d') if ts else "-"
            claim["member_name"] = claim["email_member"].split("@")[0]
            
        context["claims"] = klaim_data

    except Exception as e:
        print(f"Error fetching claim miles data: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()

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

        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE claim_missing_miles
                SET maskapai=%s, kelas_kabin=%s, bandara_asal=%s, bandara_tujuan=%s,
                    tanggal_penerbangan=%s, flight_number=%s, pnr=%s, nomor_tiket=%s
                WHERE id=%s
            """, (maskapai, kelas, asal, tujuan, tanggal, flight_no, pnr, nomor_tiket_baru, claim_id))
            conn.commit()
        except Exception as e:
            print(f"Gagal update: {e}")
            if conn: conn.rollback()
        finally:
            if cur: cur.close()
            if conn: conn.close()

    return redirect("miles:claim_miles")


def delete_claim(request):
    if request.method == "POST":
        claim_id = request.POST.get("claim_id")
        
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM claim_missing_miles WHERE id=%s", (claim_id,))
            conn.commit()
        except Exception as e:
            print(f"Gagal hapus: {e}")
            if conn: conn.rollback()
        finally:
            if cur: cur.close()
            if conn: conn.close()

    return redirect("miles:claim_miles")


def approve_claim(request, claim_id):
    if request.session.get("role") != "staf":
        return redirect("miles:claim_miles")

    if request.method == "POST":
        conn = None
        cur = None
        try:
            conn = get_db_connection()
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

            # Update status
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
            if cur: cur.close()
            if conn: conn.close()

    return redirect("miles:claim_miles")


def reject_claim(request, claim_id):
    if request.session.get("role") != "staf":
        return redirect("miles:claim_miles")

    if request.method == "POST":
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE claim_missing_miles SET status_penerimaan = 'Ditolak' WHERE id = %s",
                (claim_id,)
            )
            conn.commit()
        except Exception as e:
            print(f"Gagal tolak klaim: {e}")
            if conn: conn.rollback()
        finally:
            if cur: cur.close()
            if conn: conn.close()

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

        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Cek email penerima
            cur.execute("SELECT email FROM member WHERE email = %s", (email_penerima,))
            if not cur.fetchone():
                messages.error(request, "Email penerima tidak ditemukan di sistem.")
                return redirect("miles:transfer_miles")

            # Eksekusi fungsi transfer miles
            cur.execute(
                "SELECT fungsi_proses_transfer_miles(%s, %s, %s, %s)",
                (user_email, email_penerima, jumlah, catatan)
            )
            res = cur.fetchone()
            conn.commit()
            
            if res:
                messages.success(request, res[0])

        except Exception as e:
            if conn: conn.rollback()
            error_message = str(e)
            if "Saldo award miles tidak mencukupi" in error_message:
                match = re.search(r'(ERROR:\s*Saldo award miles tidak mencukupi.*)', error_message)
                messages.error(request, match.group(1) if match else "ERROR: Saldo award miles tidak mencukupi untuk melakukan transfer ini.")
            else:
                print(f"Gagal transfer miles: {e}")
                messages.error(request, "Terjadi kesalahan sistem saat memproses transfer.")
        finally:
            if cur: cur.close()
            if conn: conn.close()

        return redirect("miles:transfer_miles")
    
    context = {"transfers": [], "award_miles": 0}

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Ambil saldo saat ini
        cur.execute("SELECT award_miles FROM member WHERE email = %s", (user_email,))
        member_row = cur.fetchone()
        if member_row:
            context["award_miles"] = member_row.get("award_miles", 0)

        # Ambil riwayat transfer (kirim dan terima)
        cur.execute("""
            SELECT * FROM transfer 
            WHERE email_member_1 = %s OR email_member_2 = %s
            ORDER BY timestamp DESC
        """, (user_email, user_email))
        
        transfer_rows = cur.fetchall()
        transfers = []
        
        for t in transfer_rows:
            ts = t.get("timestamp")
            is_sender = (t["email_member_1"] == user_email)
            
            transfers.append({
                "email_member": t["email_member_2"] if is_sender else t["email_member_1"],
                "nama_member": (t["email_member_2"] if is_sender else t["email_member_1"]).split("@")[0],
                "jumlah_miles": t["jumlah"],
                "catatan": t.get("catatan"),
                "tipe": "Kirim" if is_sender else "Terima",
                "waktu_fmt": ts.strftime('%Y-%m-%d %H:%M') if ts else "-",
                "timestamp": ts
            })

        context["transfers"] = transfers

    except Exception as e:
        print(f"Gagal ambil data transfer miles: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()

    return render(request, "miles/transfer_miles.html", context)