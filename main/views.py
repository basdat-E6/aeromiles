import psycopg2
from psycopg2.extras import RealDictCursor
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password

def get_db_connection():
    """Membuka koneksi langsung ke PostgreSQL menggunakan DATABASE_URL dari settings.py"""
    return psycopg2.connect(settings.DATABASE_URL)

def landing(request):
    return render(request, "landing.html")

def dashboard(request):
    user_email = request.session.get('user_email')
    role = request.session.get('role')

    if not user_email:
        return redirect('authentication:login')

    context = {}
    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 1. Ambil Data Pengguna
        cursor.execute("SELECT * FROM pengguna WHERE email = %s", [user_email])
        pengguna_data = cursor.fetchone()
        if pengguna_data:
            context['pengguna'] = pengguna_data

        if role == 'member':
            cursor.execute("SELECT * FROM member WHERE email = %s", [user_email])
            member_data = cursor.fetchone()
            
            if member_data:
                total_mentah = member_data.get('total_miles') or 0
                award_mentah = member_data.get('award_miles') or 0

                member_data['total_miles'] = f"{int(total_mentah):,}"
                member_data['award_miles'] = f"{int(award_mentah):,}"
                context['member'] = member_data

                cursor.execute("SELECT nama FROM tier WHERE id_tier = %s", [member_data['id_tier']])
                tier_data = cursor.fetchone()
                if tier_data:
                    context['tier_nama'] = tier_data['nama']
            
            transaksi_gabungan = []
            
            cursor.execute("""
                SELECT mp.timestamp, amp.jumlah_award_miles
                FROM member_award_miles_package mp
                JOIN award_miles_package amp ON mp.id = amp.id
                WHERE mp.email_member = %s
            """, [user_email])
            for p in cursor.fetchall():
                transaksi_gabungan.append({
                    'jenis': 'Package',
                    'raw_time': p['timestamp'], 
                    'tanggal': str(p['timestamp'])[:16].replace('T', ' '), 
                    'miles': f"{p['jumlah_award_miles']:,}", 
                    'is_negative': False
                })

            cursor.execute("SELECT * FROM transfer WHERE email_member_1 = %s", [user_email])
            for t in cursor.fetchall():
                transaksi_gabungan.append({
                    'jenis': 'Transfer',
                    'raw_time': t['timestamp'],
                    'tanggal': str(t['timestamp'])[:16].replace('T', ' '),
                    'miles': f"{t['jumlah']:,}",
                    'is_negative': True
                })

            cursor.execute("SELECT * FROM transfer WHERE email_member_2 = %s", [user_email])
            for t in cursor.fetchall():
                transaksi_gabungan.append({
                    'jenis': 'Transfer',
                    'raw_time': t['timestamp'],
                    'tanggal': str(t['timestamp'])[:16].replace('T', ' '),
                    'miles': f"{t['jumlah']:,}",
                    'is_negative': False
                })

            cursor.execute("""
                SELECT r.timestamp, h.miles
                FROM redeem r
                JOIN hadiah h ON r.kode_hadiah = h.kode_hadiah
                WHERE r.email_member = %s
            """, [user_email])
            for r in cursor.fetchall():
                transaksi_gabungan.append({
                    'jenis': 'Redeem',
                    'raw_time': r['timestamp'],
                    'tanggal': str(r['timestamp'])[:16].replace('T', ' '),
                    'miles': f"{r['miles']:,}",
                    'is_negative': True
                })

            transaksi_gabungan.sort(key=lambda x: x['raw_time'], reverse=True)
            context['transaksi_list'] = transaksi_gabungan[:5]

        elif role == 'staf':
            cursor.execute("SELECT * FROM staf WHERE email = %s", [user_email])
            staf_data = cursor.fetchone()
            
            if staf_data:
                context['staf'] = staf_data

                cursor.execute("SELECT nama_maskapai FROM maskapai WHERE kode_maskapai = %s", [staf_data['kode_maskapai']])
                maskapai_data = cursor.fetchone()
                if maskapai_data:
                    context['maskapai_nama'] = maskapai_data['nama_maskapai']

                cursor.execute("SELECT COUNT(*) AS total FROM claim_missing_miles WHERE status_penerimaan = 'Menunggu'")
                context['klaim_menunggu'] = cursor.fetchone()['total']

                cursor.execute("SELECT COUNT(*) AS total FROM claim_missing_miles WHERE status_penerimaan = 'Disetujui' AND email_staf = %s", [user_email])
                context['klaim_disetujui'] = cursor.fetchone()['total']

                cursor.execute("SELECT COUNT(*) AS total FROM claim_missing_miles WHERE status_penerimaan = 'Ditolak' AND email_staf = %s", [user_email])
                context['klaim_ditolak'] = cursor.fetchone()['total']

    except Exception as e:
        print(f"Error fetching dashboard data: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()

    return render(request, 'dashboard.html', context)

def profil_view(request):
    user_email = request.session.get('user_email')
    role = request.session.get('role')

    if not user_email:
        return redirect('authentication:login')

    if request.method == 'POST':
        action = request.POST.get('action')
        conn = None
        
        try:
            conn = get_db_connection()
            conn.autocommit = False
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if action == 'update_profile':
                first_name = request.POST.get('first_name', '').strip()
                mid_name   = request.POST.get('mid_name', '').strip()
                first_mid_name = f"{first_name} {mid_name}".strip() if mid_name else first_name

                cursor.execute("""
                    UPDATE pengguna 
                    SET salutation=%s, first_mid_name=%s, last_name=%s, kewarganegaraan=%s,
                        country_code=%s, mobile_number=%s, tanggal_lahir=%s
                    WHERE email=%s
                """, [
                    request.POST.get('salutation'), first_mid_name, request.POST.get('last_name'),
                    request.POST.get('citizenship'), request.POST.get('country_code'),
                    request.POST.get('phone'), request.POST.get('dob'), user_email
                ])
                
                conn.commit()
                messages.success(request, "Profil berhasil diperbarui!")

            elif action == 'update_password':
                old_pass = request.POST.get('old_pass')
                new_pass = request.POST.get('new_pass')
                confirm_pass = request.POST.get('confirm_pass')

                if new_pass != confirm_pass:
                    messages.error(request, "Konfirmasi password baru tidak cocok!")
                else:
                    cursor.execute("SELECT password FROM pengguna WHERE email = %s", [user_email])
                    user_data = cursor.fetchone()
                    db_pass = user_data['password']

                    is_correct = False
                    if db_pass.startswith('$2b$12$'):
                        is_correct = (db_pass == f"$2b$12${old_pass}")
                    else:
                        is_correct = check_password(old_pass, db_pass)

                    if is_correct:
                        hashed_new_pass = make_password(new_pass)
                        cursor.execute("UPDATE pengguna SET password=%s WHERE email=%s", [hashed_new_pass, user_email])
                        conn.commit()
                        messages.success(request, "Password berhasil diperbarui!")
                    else:
                        messages.error(request, "Password lama salah!")

        except psycopg2.Error as e:
            if conn: conn.rollback()
            print(f"Database Error: {e}")
            messages.error(request, "Gagal memperbarui data karena kesalahan database.")
        except Exception as e:
            if conn: conn.rollback()
            print(f"System Error: {e}")
            messages.error(request, "Terjadi kesalahan sistem.")
        finally:
            if conn:
                cursor.close()
                conn.close()
                
        return redirect('main:profil')

    context = {'role': role}
    conn = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT * FROM pengguna WHERE email = %s", [user_email])
        profile = cursor.fetchone()
        
        if profile:
            first_mid = profile.get('first_mid_name', '') or ''
            parts = first_mid.strip().split(' ', 1)
            profile['nama_depan']  = parts[0] if len(parts) >= 1 else ''
            profile['nama_tengah'] = parts[1] if len(parts) >= 2 else ''
            profile['nama_belakang'] = profile.get('last_name', '') or ''
            context['profile'] = profile

        if role == 'member':
            cursor.execute("SELECT * FROM member WHERE email = %s", [user_email])
            member_data = cursor.fetchone()
            if member_data: 
                context['member'] = member_data
                
        elif role == 'staf':
            cursor.execute("SELECT * FROM staf WHERE email = %s", [user_email])
            staf_data = cursor.fetchone()
            if staf_data: 
                context['staf'] = staf_data

            cursor.execute("SELECT * FROM maskapai")
            context['list_maskapai'] = cursor.fetchall()
            
    except Exception as e:
        print(f"Error loading profile data: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()

    return render(request, 'profil.html', context)