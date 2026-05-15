from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from datetime import date
from django.db import connection, transaction

# --- HELPER FUNCTIONS ---
def dictfetchall(cursor):
    """Mengembalikan semua baris dari cursor sebagai list of dicts"""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def dictfetchone(cursor):
    """Mengembalikan satu baris dari cursor sebagai dict"""
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))

# --- VIEWS ---

def register(request):
    if request.method == "POST":
        role = request.POST.get('role')
        email = request.POST.get('email').strip().lower()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Password dan konfirmasi password tidak sama.")
            return redirect('authentication:register')

        try:
            # transaction.atomic memastikan kalau ada query yang gagal di blok ini, 
            # semuanya otomatis di-rollback. Jika sukses, otomatis di-commit.
            with transaction.atomic():
                with connection.cursor() as cursor:
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

                    # Insert sesuai ROLE
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

            messages.success(request, "Registrasi berhasil, silakan login.")
            return redirect('authentication:login')

        except Exception as e:
            # Psycopg2 errors biasanya bisa langsung di-print sebagai string
            print(f"Gagal mendaftar: {e}")
            messages.error(request, f"Gagal mendaftar: Pastikan email belum terpakai atau data valid.")
            return redirect('authentication:register')

    # Bagian GET request (Fetch Maskapai)
    daftar_maskapai = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM maskapai")
            daftar_maskapai = dictfetchall(cursor)
    except Exception as e:
        print(f"Gagal load maskapai: {e}")

    return render(request, 'authentication/register.html', {'maskapai_list': daftar_maskapai})


def login(request):
    if request.session.get('user_email'):
        return redirect('main:dashboard')

    if request.method == 'POST':
        email = request.POST.get('email').strip().lower()
        password = request.POST.get('password')

        try:
            with connection.cursor() as cursor:
                # 1. Cek User
                cursor.execute("SELECT * FROM pengguna WHERE email = %s", [email])
                user_data = dictfetchone(cursor)

                if not user_data:
                    messages.error(request, "Email atau password salah, silakan coba lagi.")
                    return redirect('authentication:login')

                db_password = user_data['password']

                # Cek password Supabase lawas vs Django hash baru
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

                    # 2. Cek Role (Apakah Staf?)
                    cursor.execute("SELECT * FROM staf WHERE email = %s", [email])
                    staf_data = dictfetchone(cursor)

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

    return render(request, 'authentication/login.html')


def logout(request):
    request.session.flush()
    return redirect('/')