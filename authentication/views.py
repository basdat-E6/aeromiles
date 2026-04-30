from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from datetime import date

from django.conf import settings

def register(request):
    if request.method == "POST":
        role = request.POST.get('role')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Password dan konfirmasi password tidak sama.")
            return redirect('authentication:register')

        try:
            settings.SUPABASE_CLIENT.auth.sign_up({
                "email": email,
                "password": password
            })

            hashed_pw = make_password(password)

            settings.SUPABASE_CLIENT.table('pengguna').insert({
                "email": email,
                "password": hashed_pw,
                "salutation": request.POST.get('salutation'),
                "first_mid_name": request.POST.get('first_name'),
                "last_name": request.POST.get('last_name'),
                "country_code": request.POST.get('country_code'),
                "mobile_number": request.POST.get('phone'),
                "tanggal_lahir": request.POST.get('dob'),
                "kewarganegaraan": request.POST.get('nationality')
            }).execute()

            if role == 'member':
                settings.SUPABASE_CLIENT.table('member').insert({
                    "email": email,
                    "tanggal_gabung": date.today().isoformat(),
                    "id_tier": "T1",
                    "award_miles": 0,
                    "total_miles": 0
                }).execute()

            elif role == 'staf':
                settings.SUPABASE_CLIENT.table('staf').insert({
                    "email": email,
                    "kode_maskapai": request.POST.get('airline_code')
                }).execute()

            return redirect('authentication:login')

        except Exception as e:
            messages.error(request, f"Gagal mendaftar: {str(e)}")
            return redirect('authentication:register')

    try:
        maskapai_res = settings.SUPABASE_CLIENT.table('maskapai').select('*').execute()
        daftar_maskapai = maskapai_res.data
    except Exception:
        daftar_maskapai = []

    return render(request, 'authentication/register.html', {'maskapai_list': daftar_maskapai})


def login(request):
    if request.session.get('user_email'):
        return redirect('main:dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user_check = settings.SUPABASE_CLIENT.table('pengguna').select('*').eq('email', email).execute()

            if len(user_check.data) == 0:
                messages.error(request, "Email tidak terdaftar.")
                return redirect('authentication:login')

            user_data = user_check.data[0]
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
                staf_check = settings.SUPABASE_CLIENT.table('staf').select('*').eq('email', email).execute()
                
                
                if len(staf_check.data) > 0:
                    request.session['role'] = 'staf'
                else:
                    request.session['role'] = 'member'

                return redirect('main:dashboard')
            else:
                messages.error(request, "Password salah.")
                return redirect('authentication:login')

        except Exception as e:
            print(f"ERROR LOGIN SUPABASE: {e}")
            messages.error(request, "Terjadi kesalahan pada sistem database.")
            return redirect('authentication:login')

    return render(request, 'authentication/login.html')


def logout(request):
    try:
        settings.SUPABASE_CLIENT.auth.sign_out()
    except Exception:
        pass
    
    request.session.flush()
    return redirect('/')
