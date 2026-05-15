import psycopg2
from psycopg2 import errors
from psycopg2.extras import RealDictCursor
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from datetime import date
from django.conf import settings

def get_db_connection():
    """Membuka koneksi langsung ke PostgreSQL menggunakan kredensial dari settings.py"""
    return psycopg2.connect(settings.DATABASE_URL)

def register(request):
    if request.method == "POST":
        role = request.POST.get('role')
        email = request.POST.get('email').strip().lower()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Password dan konfirmasi password tidak sama.")
            return redirect('authentication:register')

        conn = None 
        try:
            conn = get_db_connection()
            conn.autocommit = False 
            cursor = conn.cursor()

            hashed_pw = make_password(password)

            cursor.execute("""
                INSERT INTO pengguna (email, password, salutation, first_mid_name, last_name, country_code, mobile_number, tanggal_lahir, kewarganegaraan)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                email, hashed_pw, request.POST.get('salutation'), 
                request.POST.get('first_name'), request.POST.get('last_name'), 
                request.POST.get('country_code'), request.POST.get('phone'), 
                request.POST.get('dob'), request.POST.get('nationality')
            ])

            if role == 'member':
                cursor.execute("""
                    INSERT INTO member (email, tanggal_gabung, id_tier, award_miles, total_miles)
                    VALUES (%s, %s, %s, %s, %s)
                """, [email, date.today().isoformat(), "T01", 0, 0])

            elif role == 'staf':
                cursor.execute("""
                    INSERT INTO staf (email, kode_maskapai)
                    VALUES (%s, %s)
                """, [email, request.POST.get('airline_code')])

            conn.commit() 
            messages.success(request, "Registrasi berhasil, silakan login.")
            return redirect('authentication:login')

        except errors.RaiseException as e:
            if conn: conn.rollback() 
            pesan_bersih = str(e.diag.message_primary) if e.diag else str(e).split('\n')[0]
            messages.error(request, pesan_bersih)
            return redirect('authentication:register')

        except psycopg2.Error as e:
            if conn: conn.rollback()
            print(f"Database Error: {e}")
            messages.error(request, "Gagal mendaftar: Terjadi kesalahan pada database.")
            return redirect('authentication:register')

        except Exception as e:
            if conn: conn.rollback()
            print(f"Gagal mendaftar: {e}")
            messages.error(request, "Gagal mendaftar: Pastikan data valid.")
            return redirect('authentication:register')

        finally:
            if conn:
                cursor.close()
                conn.close()

    daftar_maskapai = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM maskapai")
        daftar_maskapai = cursor.fetchall()
    except Exception as e:
        print(f"Gagal load maskapai: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()

    return render(request, 'authentication/register.html', {'maskapai_list': daftar_maskapai})


def login(request):
    if request.session.get('user_email'):
        return redirect('main:dashboard')

    if request.method == 'POST':
        email = request.POST.get('email').strip().lower()
        password = request.POST.get('password')

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 1. Cek User
            cursor.execute("SELECT * FROM pengguna WHERE email = %s", [email])
            user_data = cursor.fetchone()

            if not user_data:
                messages.error(request, "Email atau password salah, silakan coba lagi.")
                return redirect('authentication:login')

            db_password = user_data['password']

            if db_password.startswith('$2b$12$'):
                is_password_correct = (db_password == f"$2b$12${password}")
            else:
                is_password_correct = check_password(password, db_password)

            if is_password_correct:
                salutation = user_data['salutation']
                last_name = user_data['last_name']
                first_mid_name = user_data['first_mid_name']
                first_name = first_mid_name.split()[0] if first_mid_name else ""
                full_name = f"{salutation} {first_name} {last_name}"

                request.session['user_email'] = email
                request.session['user_full_name'] = full_name

                cursor.execute("SELECT * FROM staf WHERE email = %s", [email])
                staf_data = cursor.fetchone()

                if staf_data:
                    request.session['role'] = 'staf'
                else:
                    request.session['role'] = 'member'

                return redirect('main:dashboard')
            else:
                messages.error(request, "Email atau password salah, silakan coba lagi.")
                return redirect('authentication:login')

        except Exception as e:
            print(f"ERROR LOGIN: {e}")
            messages.error(request, "Terjadi kesalahan pada sistem database.")
            return redirect('authentication:login')
        finally:
            if conn:
                cursor.close()
                conn.close()

    return render(request, 'authentication/login.html')

def logout(request):
    request.session.flush()
    return redirect('/')