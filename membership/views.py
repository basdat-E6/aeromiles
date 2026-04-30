from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.hashers import make_password
from datetime import date

def kelola_member(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            nama_depan = request.POST.get('nama_depan', '')
            nama_tengah = request.POST.get('nama_tengah', '')
            first_mid_name = f"{nama_depan} {nama_tengah}".strip()

            try:
                settings.SUPABASE_CLIENT.table('pengguna').insert({
                    "email": email,
                    "password": make_password(password), # Wajib di-hash
                    "salutation": request.POST.get('salutation'),
                    "first_mid_name": first_mid_name,
                    "last_name": request.POST.get('nama_belakang'),
                    "country_code": request.POST.get('country_code'),
                    "mobile_number": request.POST.get('nomor_hp'),
                    "tanggal_lahir": request.POST.get('tanggal_lahir'),
                    "kewarganegaraan": request.POST.get('kewarganegaraan')
                }).execute()

                settings.SUPABASE_CLIENT.table('member').insert({
                    "email": email,
                    "tanggal_gabung": date.today().isoformat(),
                    "id_tier": "T1", # Ganti dengan ID tier terendah di database kamu
                    "award_miles": 0,
                    "total_miles": 0
                }).execute()
                
                messages.success(request, "Member baru berhasil ditambahkan!")
            except Exception as e:
                print(f"Error Add Member: {e}")
                messages.error(request, "Gagal menambahkan member. Email mungkin sudah terdaftar.")

        elif action == 'edit':
            email = request.POST.get('email_edit') 
            nama_depan = request.POST.get('nama_depan_edit', '')
            nama_tengah = request.POST.get('nama_tengah_edit', '')
            first_mid_name = f"{nama_depan} {nama_tengah}".strip()

            try:
                settings.SUPABASE_CLIENT.table('pengguna').update({
                    "salutation": request.POST.get('salutation_edit'),
                    "first_mid_name": first_mid_name,
                    "last_name": request.POST.get('nama_belakang_edit'),
                    "country_code": request.POST.get('country_code_edit'),
                    "mobile_number": request.POST.get('nomor_hp_edit'),
                    "tanggal_lahir": request.POST.get('tanggal_lahir_edit'),
                    "kewarganegaraan": request.POST.get('kewarganegaraan_edit')
                }).eq('email', email).execute()

                settings.SUPABASE_CLIENT.table('member').update({
                    "id_tier": request.POST.get('tier_edit')
                }).eq('email', email).execute()

                messages.success(request, "Data member berhasil diperbarui!")
            except Exception as e:
                print(f"Error Edit Member: {e}")
                messages.error(request, "Gagal memperbarui data member.")

        elif action == 'delete':
            email = request.POST.get('email_delete')
            try:
                settings.SUPABASE_CLIENT.table('pengguna').delete().eq('email', email).execute()
                messages.success(request, "Member berhasil dihapus!")
            except Exception as e:
                print(f"Error Delete Member: {e}")
                messages.error(request, "Gagal menghapus member.")

        return redirect('main:kelola_member')

    context = {}
    search_query = request.GET.get('search', '').lower()
    tier_filter = request.GET.get('tier', '')

    try:
        tier_res = settings.SUPABASE_CLIENT.table('tier').select('*').execute()
        context['tier_list'] = tier_res.data

        members_res = settings.SUPABASE_CLIENT.table('member') \
            .select('*, pengguna(*), tier(nama)') \
            .execute()
        
        raw_members = members_res.data
        processed_members = []

        for m in raw_members:
            pengguna = m.get('pengguna', {})
            tier_nama = m.get('tier', {}).get('nama', '-')
            
            if not pengguna: continue

            if tier_filter and m['id_tier'] != tier_filter:
                continue

            full_name = f"{pengguna.get('salutation', '')} {pengguna.get('first_mid_name', '')} {pengguna.get('last_name', '')}".strip()
            
            if search_query:
                if not (search_query in full_name.lower() or 
                        search_query in m['email'].lower() or 
                        search_query in str(m.get('nomor_member', '')).lower()):
                    continue

            processed_members.append({
                'nomor_member': m.get('nomor_member', '-'),
                'email': m['email'],
                'nama_lengkap': full_name,
                'tier_nama': tier_nama,
                'id_tier': m['id_tier'],
                'total_miles': f"{m.get('total_miles', 0):,}",
                'award_miles': f"{m.get('award_miles', 0):,}",
                'tanggal_gabung': m.get('tanggal_gabung', '-'),
                'raw_salutation': pengguna.get('salutation', ''),
                'raw_fmn': pengguna.get('first_mid_name', ''),
                'raw_last': pengguna.get('last_name', ''),
                'raw_country': pengguna.get('country_code', ''),
                'raw_phone': pengguna.get('mobile_number', ''),
                'raw_dob': pengguna.get('tanggal_lahir', ''),
                'raw_kwn': pengguna.get('kewarganegaraan', ''),
            })

        context['members'] = processed_members
        context['search_query'] = search_query
        context['tier_filter'] = tier_filter

    except Exception as e:
        print(f"Error load kelola member: {e}")

    return render(request, 'kelola_member.html', context)

def identitas(request):
    user_email = request.session.get('user_email')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            nomor = request.POST.get('nomor')
            jenis = request.POST.get('jenis')
            negara = request.POST.get('negara_penerbit')
            tgl_terbit = request.POST.get('tanggal_terbit')
            tgl_habis = request.POST.get('tanggal_habis')

            try:
                settings.SUPABASE_CLIENT.table('identitas').insert({
                    "nomor": nomor,
                    "jenis": jenis,
                    "negara_penerbit": negara,
                    "tanggal_terbit": tgl_terbit,
                    "tanggal_habis": tgl_habis,
                    "email_member": user_email
                }).execute()
                messages.success(request, "Dokumen identitas berhasil ditambahkan!")
            except Exception as e:
                print(f"Error Add Identitas: {e}")
                messages.error(request, "Gagal! Nomor dokumen mungkin sudah terdaftar di sistem.")

        elif action == 'edit':
            nomor = request.POST.get('nomor_edit')
            jenis = request.POST.get('jenis_edit')
            negara = request.POST.get('negara_penerbit_edit')
            tgl_terbit = request.POST.get('tanggal_terbit_edit')
            tgl_habis = request.POST.get('tanggal_habis_edit')

            try:
                settings.SUPABASE_CLIENT.table('identitas').update({
                    "jenis": jenis,
                    "negara_penerbit": negara,
                    "tanggal_terbit": tgl_terbit,
                    "tanggal_habis": tgl_habis
                }).eq('nomor', nomor).eq('email_member', user_email).execute()
                
                messages.success(request, "Data identitas berhasil diperbarui!")
            except Exception as e:
                print(f"Error Edit Identitas: {e}")
                messages.error(request, "Gagal memperbarui identitas.")

        elif action == 'delete':
            nomor = request.POST.get('nomor_delete')
            try:
                settings.SUPABASE_CLIENT.table('identitas').delete() \
                    .eq('nomor', nomor).eq('email_member', user_email).execute()
                messages.success(request, "Identitas berhasil dihapus!")
            except Exception as e:
                print(f"Error Delete Identitas: {e}")
                messages.error(request, "Gagal menghapus identitas.")

        return redirect('membership:identitas')

    context = {}
    try:
        id_res = settings.SUPABASE_CLIENT.table('identitas').select('*').eq('email_member', user_email).execute()
        
        identitas_list = id_res.data
        hari_ini = date.today()

        for doc in identitas_list:
            tgl_habis_obj = date.fromisoformat(doc['tanggal_habis'])
            
            if tgl_habis_obj < hari_ini:
                doc['status'] = 'Kedaluwarsa'
            else:
                doc['status'] = 'Aktif'

        context['identitas_list'] = identitas_list

    except Exception as e:
        print(f"Error load identitas: {e}")

    return render(request, 'identitas.html', context)