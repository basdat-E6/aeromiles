import psycopg2
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from datetime import date
from django.db import connection

def dictfetchall(cursor):
    if cursor.description is None:
        return []
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def kelola_member(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            nama_depan = request.POST.get('nama_depan', '')
            nama_tengah = request.POST.get('nama_tengah', '')
            first_mid_name = f"{nama_depan} {nama_tengah}".strip()
            hashed_pw = make_password(password)
            tgl_hari_ini = date.today().isoformat()

            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO pengguna 
                        (email, password, salutation, first_mid_name, last_name, country_code, mobile_number, tanggal_lahir, kewarganegaraan) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        email, hashed_pw, request.POST.get('salutation'), 
                        first_mid_name, request.POST.get('nama_belakang'), 
                        request.POST.get('country_code'), request.POST.get('nomor_hp'), 
                        request.POST.get('tanggal_lahir'), request.POST.get('kewarganegaraan')
                    ])
                    # Insert ke tabel Member
                    cursor.execute("""
                        INSERT INTO member (email, tanggal_gabung, id_tier, award_miles, total_miles) 
                        VALUES (%s, %s, %s, 0, 0)
                    """, [email, tgl_hari_ini, "T1"])

                messages.success(request, "Member baru berhasil ditambahkan!")
            except psycopg2.Error as e:
                print(f"Error Add Member: {e}")
                messages.error(request, "Gagal menambahkan member. Email mungkin sudah terdaftar.")

        elif action == 'edit':
            email = request.POST.get('email_edit') 
            nama_depan = request.POST.get('nama_depan_edit', '')
            nama_tengah = request.POST.get('nama_tengah_edit', '')
            first_mid_name = f"{nama_depan} {nama_tengah}".strip()

            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE pengguna 
                        SET salutation=%s, first_mid_name=%s, last_name=%s, country_code=%s, 
                            mobile_number=%s, tanggal_lahir=%s, kewarganegaraan=%s 
                        WHERE email=%s
                    """, [
                        request.POST.get('salutation_edit'), first_mid_name, 
                        request.POST.get('nama_belakang_edit'), request.POST.get('country_code_edit'), 
                        request.POST.get('nomor_hp_edit'), request.POST.get('tanggal_lahir_edit'), 
                        request.POST.get('kewarganegaraan_edit'), email
                    ])

                    cursor.execute("""
                        UPDATE member SET id_tier=%s WHERE email=%s
                    """, [request.POST.get('tier_edit'), email])

                messages.success(request, "Data member berhasil diperbarui!")
            except Exception as e:
                print(f"Error Edit Member: {e}")
                messages.error(request, "Gagal memperbarui data member.")

        elif action == 'delete':
            email = request.POST.get('email_delete')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM pengguna WHERE email=%s", [email])
                messages.success(request, "Member berhasil dihapus!")
            except Exception as e:
                print(f"Error Delete Member: {e}")
                messages.error(request, "Gagal menghapus member.")

        return redirect('main:kelola_member')

    context = {}
    search_query = request.GET.get('search', '').lower()
    tier_filter = request.GET.get('tier', '')

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM tier")
            context['tier_list'] = dictfetchall(cursor)

            cursor.execute("""
                SELECT 
                    m.nomor_member, m.email, m.id_tier, m.total_miles, m.award_miles, m.tanggal_gabung,
                    p.salutation, p.first_mid_name, p.last_name, p.country_code, p.mobile_number, 
                    p.tanggal_lahir, p.kewarganegaraan,
                    t.nama AS tier_nama
                FROM member m
                JOIN pengguna p ON m.email = p.email
                LEFT JOIN tier t ON m.id_tier = t.id_tier
            """)
            raw_members = dictfetchall(cursor)

        processed_members = []
        for m in raw_members:
            if tier_filter and m['id_tier'] != tier_filter:
                continue

            full_name = f"{m.get('salutation', '')} {m.get('first_mid_name', '')} {m.get('last_name', '')}".strip()
            
            if search_query:
                if not (search_query in full_name.lower() or 
                        search_query in m['email'].lower() or 
                        search_query in str(m.get('nomor_member', '')).lower()):
                    continue

            processed_members.append({
                'nomor_member': m.get('nomor_member', '-'),
                'email': m['email'],
                'nama_lengkap': full_name,
                'tier_nama': m.get('tier_nama', '-'),
                'id_tier': m['id_tier'],
                'total_miles': f"{m.get('total_miles', 0):,}",
                'award_miles': f"{m.get('award_miles', 0):,}",
                'tanggal_gabung': str(m.get('tanggal_gabung', '-')),
                'raw_salutation': m.get('salutation', ''),
                'raw_fmn': m.get('first_mid_name', ''),
                'raw_last': m.get('last_name', ''),
                'raw_country': m.get('country_code', ''),
                'raw_phone': m.get('mobile_number', ''),
                'raw_dob': str(m.get('tanggal_lahir', '')),
                'raw_kwn': m.get('kewarganegaraan', ''),
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
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO identitas (nomor, jenis, negara_penerbit, tanggal_terbit, tanggal_habis, email_member) 
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, [
                        request.POST.get('nomor'), request.POST.get('jenis'), 
                        request.POST.get('negara_penerbit'), request.POST.get('tanggal_terbit'), 
                        request.POST.get('tanggal_habis'), user_email
                    ])
                messages.success(request, "Dokumen identitas berhasil ditambahkan!")
            except psycopg2.Error as e:
                print(f"Error Add Identitas: {e}")
                messages.error(request, "Gagal! Nomor dokumen mungkin sudah terdaftar di sistem.")

        elif action == 'edit':
            nomor = request.POST.get('nomor_edit')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE identitas 
                        SET jenis=%s, negara_penerbit=%s, tanggal_terbit=%s, tanggal_habis=%s 
                        WHERE nomor=%s AND email_member=%s
                    """, [
                        request.POST.get('jenis_edit'), request.POST.get('negara_penerbit_edit'),
                        request.POST.get('tanggal_terbit_edit'), request.POST.get('tanggal_habis_edit'),
                        nomor, user_email
                    ])
                messages.success(request, "Data identitas berhasil diperbarui!")
            except Exception as e:
                print(f"Error Edit Identitas: {e}")
                messages.error(request, "Gagal memperbarui identitas.")

        elif action == 'delete':
            nomor = request.POST.get('nomor_delete')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM identitas WHERE nomor=%s AND email_member=%s", [nomor, user_email])
                messages.success(request, "Identitas berhasil dihapus!")
            except Exception as e:
                print(f"Error Delete Identitas: {e}")
                messages.error(request, "Gagal menghapus identitas.")

        return redirect('membership:identitas')

    context = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM identitas WHERE email_member=%s", [user_email])
            identitas_list = dictfetchall(cursor)
        
        hari_ini = date.today()

        for doc in identitas_list:
            if type(doc['tanggal_habis']) is str:
                tgl_habis_obj = date.fromisoformat(doc['tanggal_habis'])
            else:
                tgl_habis_obj = doc['tanggal_habis']
                doc['tanggal_habis'] = doc['tanggal_habis'].isoformat()
                
            if tgl_habis_obj < hari_ini:
                doc['status'] = 'Kedaluwarsa'
            else:
                doc['status'] = 'Aktif'

        context['identitas_list'] = identitas_list

    except Exception as e:
        print(f"Error load identitas: {e}")

    return render(request, 'identitas.html', context)