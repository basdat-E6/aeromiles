from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def landing(request):
    return render(request, "landing.html")


def dashboard(request):
    user_email = request.session.get('user_email')
    role = request.session.get('role')

    if not user_email:
        return redirect('login_view')

    context = {}

    try:
        pengguna_res = settings.SUPABASE_CLIENT.table('pengguna').select('*').eq('email', user_email).execute()
        
        if pengguna_res.data:
            context['pengguna'] = pengguna_res.data[0]

        if role == 'member':
            member_res = settings.SUPABASE_CLIENT.table('member').select('*').eq('email', user_email).execute()
            
            if member_res.data:
                member_data = member_res.data[0]

                total_mentah = member_data.get('total_miles') or 0
                award_mentah = member_data.get('award_miles') or 0

                member_data['total_miles'] = f"{int(total_mentah):,}"
                member_data['award_miles'] = f"{int(award_mentah):,}"

                context['member'] = member_data

                tier_res = settings.SUPABASE_CLIENT.table('tier').select('nama').eq('id_tier', member_data['id_tier']).execute()
                if tier_res.data:
                    context['tier_nama'] = tier_res.data[0]['nama']
            
            transaksi_gabungan = []
            try:
                pkg_res = settings.SUPABASE_CLIENT.table('member_award_miles_package') \
                    .select('timestamp, award_miles_package(jumlah_award_miles)') \
                    .eq('email_member', user_email).execute()
                
                for p in pkg_res.data:
                    miles = p.get('award_miles_package', {}).get('jumlah_award_miles', 0) if p.get('award_miles_package') else 0
                    transaksi_gabungan.append({
                        'jenis': 'Package',
                        'raw_time': p['timestamp'], 
                        'tanggal': p['timestamp'][:16].replace('T', ' '), 
                        'miles': f"{miles:,}", 
                        'is_negative': False
                    })
            except Exception as e:
                print(f"Error Package: {e}")

            try:
                tf_out_res = settings.SUPABASE_CLIENT.table('transfer').select('*').eq('email_member_1', user_email).execute()
                for t in tf_out_res.data:
                    transaksi_gabungan.append({
                        'jenis': 'Transfer',
                        'raw_time': t['timestamp'],
                        'tanggal': t['timestamp'][:16].replace('T', ' '),
                        'miles': f"{t['jumlah']:,}",
                        'is_negative': True
                    })

                tf_in_res = settings.SUPABASE_CLIENT.table('transfer').select('*').eq('email_member_2', user_email).execute()
                for t in tf_in_res.data:
                    transaksi_gabungan.append({
                        'jenis': 'Transfer',
                        'raw_time': t['timestamp'],
                        'tanggal': t['timestamp'][:16].replace('T', ' '),
                        'miles': f"{t['jumlah']:,}",
                        'is_negative': False
                    })
            except Exception as e:
                print(f"Error Transfer: {e}")

            try:
                rdm_res = settings.SUPABASE_CLIENT.table('redeem') \
                    .select('timestamp, hadiah(miles)') \
                    .eq('email_member', user_email).execute()
                
                for r in rdm_res.data:
                    miles = r.get('hadiah', {}).get('miles', 0) if r.get('hadiah') else 0
                    transaksi_gabungan.append({
                        'jenis': 'Redeem',
                        'raw_time': r['timestamp'],
                        'tanggal': r['timestamp'][:16].replace('T', ' '),
                        'miles': f"{miles:,}",
                        'is_negative': True
                    })
            except Exception as e:
                print(f"Error Redeem: {e}")

            transaksi_gabungan.sort(key=lambda x: x['raw_time'], reverse=True)
            
            context['transaksi_list'] = transaksi_gabungan[:5]

        elif role == 'staf':
            staf_res = settings.SUPABASE_CLIENT.table('staf').select('*').eq('email', user_email).execute()
            
            if staf_res.data:
                staf_data = staf_res.data[0]
                context['staf'] = staf_data

                maskapai_res = settings.SUPABASE_CLIENT.table('maskapai').select('nama_maskapai').eq('kode_maskapai', staf_data['kode_maskapai']).execute()
                if maskapai_res.data:
                    context['maskapai_nama'] = maskapai_res.data[0]['nama_maskapai']

                klaim_menunggu_res = settings.SUPABASE_CLIENT.table('claim_missing_miles').select('id').eq('status_penerimaan', 'Menunggu').execute()
                context['klaim_menunggu'] = len(klaim_menunggu_res.data)

                klaim_disetujui_res = settings.SUPABASE_CLIENT.table('claim_missing_miles').select('id').eq('status_penerimaan', 'Disetujui').eq('email_staf', user_email).execute()
                context['klaim_disetujui'] = len(klaim_disetujui_res.data)

                klaim_ditolak_res = settings.SUPABASE_CLIENT.table('claim_missing_miles').select('id').eq('status_penerimaan', 'Ditolak').eq('email_staf', user_email).execute()
                context['klaim_ditolak'] = len(klaim_ditolak_res.data)

    except Exception as e:
        print(f"Error fetching dashboard data: {e}")

    return render(request, 'dashboard.html', context)


def profil_view(request):
    user_email = request.session.get('user_email')
    role = request.session.get('role')

    if not user_email:
        return redirect('authentication:login')

    # --- LOGIKA POST (UPDATE KE SUPABASE) ---
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Skenario 1: Update Profil Dasar
        if action == 'update_profile':
            try:
                first_name = request.POST.get('first_name', '').strip()
                mid_name   = request.POST.get('mid_name', '').strip()
                # Gabungkan kembali jadi first_mid_name untuk disimpan ke DB
                first_mid_name = f"{first_name} {mid_name}".strip() if mid_name else first_name

                settings.SUPABASE_CLIENT.table('pengguna').update({
                    'salutation':     request.POST.get('salutation'),
                    'first_mid_name': first_mid_name,
                    'last_name':      request.POST.get('last_name'),
                    'kewarganegaraan': request.POST.get('citizenship'),
                    'country_code':   request.POST.get('country_code'),
                    'mobile_number':  request.POST.get('phone'),
                    'tanggal_lahir':  request.POST.get('dob'),
                }).eq('email', user_email).execute()
            except Exception as e:
                messages.error(request, {e})
        # Skenario 2: Update Password
        elif action == 'update_password':
            old_pass = request.POST.get('old_pass')
            new_pass = request.POST.get('new_pass')
            confirm_pass = request.POST.get('confirm_pass')

            if new_pass != confirm_pass:
                messages.error(request, "Konfirmasi password baru tidak cocok!")
            else:
                res = settings.SUPABASE_CLIENT.table('pengguna').select('password').eq('email', user_email).execute()
                if res.data and res.data[0]['password'] == old_pass:
                    settings.SUPABASE_CLIENT.table('pengguna').update({'password': new_pass}).eq('email', user_email).execute()
        return redirect('main:profil')

    # --- LOGIKA GET (AMBIL DATA UNTUK TAMPILAN) ---
    context = {'role': role}
    try:
        res_p = settings.SUPABASE_CLIENT.table('pengguna').select('*').eq('email', user_email).execute()
        if res_p.data:
            profile = res_p.data[0]

            # Split first_mid_name → nama_depan + nama_tengah
            first_mid = profile.get('first_mid_name', '') or ''
            parts = first_mid.strip().split(' ', 1)
            profile['nama_depan']  = parts[0] if len(parts) >= 1 else ''
            profile['nama_tengah'] = parts[1] if len(parts) >= 2 else ''
            profile['nama_belakang'] = profile.get('last_name', '') or ''

            context['profile'] = profile
        if role == 'member':
            res_m = settings.SUPABASE_CLIENT.table('member').select('*').eq('email', user_email).execute()
            if res_m.data: context['member'] = res_m.data[0]
        elif role == 'staf':
            res_s = settings.SUPABASE_CLIENT.table('staf').select('*').eq('email', user_email).execute()
            if res_s.data: context['staf'] = res_s.data[0]
            maskapai = settings.SUPABASE_CLIENT.table('maskapai').select('*').execute()
            context['list_maskapai'] = maskapai.data
    except Exception as e:
        print(f"Error: {e}")

    return render(request, 'profil.html', context)