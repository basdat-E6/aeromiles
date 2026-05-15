from django.contrib import messages
from django.shortcuts import render, redirect
from django.conf import settings
import datetime
from datetime import date
import psycopg2
import psycopg2.extras


def _get_conn():
    """Buat koneksi psycopg2 dari settings Django."""
    return psycopg2.connect(settings.DATABASES["default"]["OPTIONS"].get(
        "dsn", settings.DATABASE_URL
    ))


def _get_penyedia_list():
    penyedia = []
    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT id_penyedia, nama_maskapai FROM maskapai")
                for m in cur.fetchall():
                    penyedia.append({
                        "id_penyedia": m["id_penyedia"],
                        "nama_penyedia": m["nama_maskapai"],
                        "tipe": "airline",
                    })
                cur.execute("SELECT id_penyedia, nama_mitra FROM mitra")
                for m in cur.fetchall():
                    penyedia.append({
                        "id_penyedia": m["id_penyedia"],
                        "nama_penyedia": m["nama_mitra"],
                        "tipe": "partner",
                    })
        penyedia.sort(key=lambda x: (x["tipe"], x["id_penyedia"]))
    except Exception as e:
        print(f"Error fetch penyedia: {e}")
    return penyedia


def hadiah_list(request):
    hadiah = []
    penyedia_list = _get_penyedia_list()
    penyedia_map = {p["id_penyedia"]: p for p in penyedia_list}
    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM hadiah ORDER BY kode_hadiah")
                for h in cur.fetchall():
                    h = dict(h)
                    p = penyedia_map.get(h.get("id_penyedia"), {})
                    h["nama_penyedia"] = p.get("nama_penyedia", "-")
                    h["tipe_penyedia"] = p.get("tipe", "-")
                    hadiah.append(h)
    except Exception as e:
        print(f"Error fetch hadiah: {e}")
    return render(request, "hadiah/list.html", {"hadiah": hadiah, "penyedia_list": penyedia_list})


def hadiah_create(request):
    if request.method == "POST":
        nama = request.POST.get("nama", "").strip()
        penyedia_id = request.POST.get("penyedia")
        miles = request.POST.get("miles")
        deskripsi = request.POST.get("deskripsi", "").strip()
        valid_start = request.POST.get("valid_start")
        valid_end = request.POST.get("valid_end")
        if nama and penyedia_id and miles and deskripsi and valid_start and valid_end:
            try:
                with _get_conn() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute("SELECT kode_hadiah FROM hadiah ORDER BY kode_hadiah DESC LIMIT 1")
                        last = cur.fetchone()
                        num = int(last["kode_hadiah"].split("-")[1]) + 1 if last else 1
                        kode = f"RWD-{num:03d}"
                        cur.execute(
                            """
                            INSERT INTO hadiah (kode_hadiah, nama, id_penyedia, miles, deskripsi, valid_start_date, program_end)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (kode, nama, int(penyedia_id), int(miles), deskripsi, valid_start, valid_end),
                        )
            except Exception as e:
                print(f"Error create hadiah: {e}")
    return redirect("rewards:hadiah_list")


def hadiah_update(request, pk):
    if request.method == "POST":
        nama = request.POST.get("nama", "").strip()
        penyedia_id = request.POST.get("penyedia")
        miles = request.POST.get("miles")
        deskripsi = request.POST.get("deskripsi", "").strip()
        valid_start = request.POST.get("valid_start")
        valid_end = request.POST.get("valid_end")
        if nama and penyedia_id and miles and deskripsi and valid_start and valid_end:
            try:
                with _get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE hadiah
                            SET nama=%s, id_penyedia=%s, miles=%s, deskripsi=%s,
                                valid_start_date=%s, program_end=%s
                            WHERE kode_hadiah=%s
                            """,
                            (nama, int(penyedia_id), int(miles), deskripsi, valid_start, valid_end, pk),
                        )
            except Exception as e:
                print(f"Error update hadiah: {e}")
    return redirect("rewards:hadiah_list")


def hadiah_delete(request, pk):
    if request.method == "POST":
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM hadiah WHERE kode_hadiah=%s", (pk,))
        except Exception as e:
            print(f"Error delete hadiah: {e}")
    return redirect("rewards:hadiah_list")


def mitra_list(request):
    mitras = []
    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM mitra ORDER BY nama_mitra")
                mitras = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"Error fetch mitra: {e}")
    return render(request, "mitra/list.html", {"mitras": mitras})


def mitra_create(request):
    if request.method == "POST":
        email_mitra = request.POST.get("email", "").strip()
        nama = request.POST.get("nama", "").strip()
        tanggal_kerja_sama = request.POST.get("tanggal_kerja_sama")
        if email_mitra and nama and tanggal_kerja_sama:
            try:
                with _get_conn() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute("SELECT email_mitra FROM mitra WHERE email_mitra=%s", (email_mitra,))
                        if cur.fetchone():
                            return redirect("rewards:mitra_list")

                        cur.execute("SELECT id FROM penyedia ORDER BY id DESC LIMIT 1")
                        max_row = cur.fetchone()
                        next_id = (max_row["id"] + 1) if max_row else 1

                        cur.execute("INSERT INTO penyedia (id) VALUES (%s)", (next_id,))
                        cur.execute(
                            """
                            INSERT INTO mitra (email_mitra, id_penyedia, nama_mitra, tanggal_kerja_sama)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (email_mitra, next_id, nama, tanggal_kerja_sama),
                        )
            except Exception as e:
                print(f"Error create mitra: {e}")
    return redirect("rewards:mitra_list")


def mitra_update(request, email):
    if request.method == "POST":
        nama = request.POST.get("nama", "").strip()
        tanggal_kerja_sama = request.POST.get("tanggal_kerja_sama")
        if nama and tanggal_kerja_sama:
            try:
                with _get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE mitra SET nama_mitra=%s, tanggal_kerja_sama=%s WHERE email_mitra=%s",
                            (nama, tanggal_kerja_sama, email),
                        )
            except Exception as e:
                print(f"Error update mitra: {e}")
    return redirect("rewards:mitra_list")


def mitra_delete(request, email):
    if request.method == "POST":
        try:
            with _get_conn() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT id_penyedia FROM mitra WHERE email_mitra=%s", (email,))
                    mitra_row = cur.fetchone()
                    cur.execute("DELETE FROM mitra WHERE email_mitra=%s", (email,))
                    if mitra_row:
                        cur.execute("DELETE FROM penyedia WHERE id=%s", (mitra_row["id_penyedia"],))
        except Exception as e:
            print(f"Error delete mitra: {e}")
    return redirect("rewards:mitra_list")


def katalog(request):
    user_email = request.session.get("user_email")
    role = request.session.get("role")

    if not user_email:
        return redirect("login_view")

    if request.method == "POST":
        if role != "member":
            messages.error(request, "Hanya member yang dapat menukarkan hadiah.")
            return redirect("rewards:katalog")

        kode_hadiah = request.POST.get("kode_hadiah")
        try:
            with _get_conn() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        "SELECT miles, nama, valid_start_date, program_end FROM hadiah WHERE kode_hadiah=%s",
                        (kode_hadiah,),
                    )
                    hadiah_row = cur.fetchone()

                    if not hadiah_row:
                        messages.error(request, "Hadiah tidak ditemukan.")
                        return redirect("rewards:katalog")

                    hari_ini = date.today()
                    valid_start = date.fromisoformat(str(hadiah_row["valid_start_date"]))
                    program_end = date.fromisoformat(str(hadiah_row["program_end"]))

                    if not (valid_start <= hari_ini <= program_end):
                        messages.error(request, f"Hadiah \"{hadiah_row['nama']}\" tidak tersedia pada periode ini.")
                        return redirect("rewards:katalog")

                    harga_miles = hadiah_row["miles"]

                    cur.execute("SELECT award_miles FROM member WHERE email=%s", (user_email,))
                    member_row = cur.fetchone()
                    saldo_sekarang = member_row.get("award_miles", 0) if member_row else 0

                    if saldo_sekarang < harga_miles:
                        messages.error(request, f"Saldo award miles tidak mencukupi. Dibutuhkan {harga_miles} miles, saldo Anda: {saldo_sekarang} miles.")
                        return redirect("rewards:katalog")

                    waktu_sekarang = datetime.datetime.now().isoformat()
                    cur.execute(
                        "INSERT INTO redeem (email_member, kode_hadiah, timestamp) VALUES (%s, %s, %s)",
                        (user_email, kode_hadiah, waktu_sekarang),
                    )
                    cur.execute(
                        "UPDATE member SET award_miles=%s WHERE email=%s",
                        (saldo_sekarang - harga_miles, user_email),
                    )

            messages.success(request, f"SUKSES: Redeem hadiah \"{hadiah_row['nama']}\" berhasil. Award miles Anda berkurang {harga_miles} miles.")
            return redirect("rewards:katalog")

        except Exception as e:
            print(f"Error saat redeem: {e}")
            messages.error(request, "Terjadi kesalahan saat memproses penukaran.")
            return redirect("rewards:katalog")

    context = {"award_miles": 0, "hadiah_list": [], "riwayat_redeem": []}

    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if role == "member":
                    cur.execute("SELECT award_miles FROM member WHERE email=%s", (user_email,))
                    member_row = cur.fetchone()
                    if member_row:
                        context["award_miles"] = member_row.get("award_miles", 0)

                hari_ini = date.today().isoformat()
                cur.execute(
                    """
                    SELECT kode_hadiah, nama, miles, deskripsi, valid_start_date, program_end, id_penyedia
                    FROM hadiah WHERE program_end >= %s
                    """,
                    (hari_ini,),
                )
                daftar_hadiah = [dict(r) for r in cur.fetchall()]
                for h in daftar_hadiah:
                    try:
                        cur.execute("SELECT nama_mitra FROM mitra WHERE id_penyedia=%s", (h["id_penyedia"],))
                        mitra_row = cur.fetchone()
                        h["nama_mitra"] = mitra_row["nama_mitra"] if mitra_row else "-"
                    except Exception:
                        h["nama_mitra"] = "-"
                context["hadiah_list"] = daftar_hadiah

                cur.execute(
                    """
                    SELECT r.timestamp, r.kode_hadiah, h.miles, h.nama
                    FROM redeem r
                    LEFT JOIN hadiah h ON h.kode_hadiah = r.kode_hadiah
                    WHERE r.email_member=%s
                    ORDER BY r.timestamp DESC
                    """,
                    (user_email,),
                )
                riwayat_list = []
                for r in cur.fetchall():
                    riwayat_list.append({
                        "nama_hadiah": r["nama"] if r["nama"] else r["kode_hadiah"],
                        "miles": r["miles"] if r["miles"] else 0,
                        "tanggal": str(r["timestamp"])[:16].replace("T", " "),
                    })
                context["riwayat_redeem"] = riwayat_list

    except Exception as e:
        print(f"Error fetch katalog: {e}")

    return render(request, 'rewards/katalog.html', context)


def beli_package(request):
    user_email = request.session.get("user_email")
    role = request.session.get("role")

    if not user_email:
        return redirect("authentication:login")

    if request.method == "POST":
        if role != "member":
            messages.error(request, "Hanya member yang dapat membeli package.")
            return redirect("rewards:beli_package")

        id_package = request.POST.get("id_package")
        waktu_sekarang = datetime.datetime.now().isoformat()

        try:
            with _get_conn() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        "SELECT jumlah_award_miles FROM award_miles_package WHERE id=%s",
                        (id_package,),
                    )
                    pkg_row = cur.fetchone()
                    if not pkg_row:
                        messages.error(request, "Paket tidak ditemukan.")
                        return redirect("rewards:beli_package")

                    jumlah_miles = pkg_row["jumlah_award_miles"]
                    cur.execute(
                        """
                        INSERT INTO member_award_miles_package (id_award_miles_package, email_member, timestamp)
                        VALUES (%s, %s, %s)
                        """,
                        (id_package, user_email, waktu_sekarang),
                    )

                    cur.execute(
                        "SELECT award_miles, total_miles FROM member WHERE email=%s",
                        (user_email,),
                    )
                    member_row = cur.fetchone()
                    award_miles_baru = (member_row.get("award_miles") or 0) + jumlah_miles
                    total_miles_baru = (member_row.get("total_miles") or 0) + jumlah_miles
                    cur.execute(
                        "UPDATE member SET award_miles=%s, total_miles=%s WHERE email=%s",
                        (award_miles_baru, total_miles_baru, user_email),
                    )

            messages.success(request, f"SUKSES: Pembelian package berhasil. Award miles dan total miles Anda bertambah {jumlah_miles:,} miles.")

        except Exception as e:
            print(f"Error Beli Package: {e}")
            messages.error(request, "Gagal memproses pembelian paket.")

        return redirect("rewards:beli_package")

    context = {"packages": [], "award_miles": 0}
    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM award_miles_package")
                context["packages"] = [dict(r) for r in cur.fetchall()]

                cur.execute("SELECT award_miles FROM member WHERE email=%s", (user_email,))
                member_row = cur.fetchone()
                if member_row:
                    context["award_miles"] = member_row.get("award_miles", 0)
    except Exception as e:
        print(f"Error fetch packages: {e}")

    return render(request, 'rewards/beli_package.html', context)


def info_tier(request):
    user_email = request.session.get("user_email")
    context = {"tiers": [], "id_tier_saya": None, "total_miles": 0}

    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM tier")
                tiers = [dict(r) for r in cur.fetchall()]
                tiers.sort(key=lambda x: x.get("id_tier", ""))
                context["tiers"] = tiers

                if user_email:
                    cur.execute(
                        "SELECT id_tier, total_miles FROM member WHERE email=%s",
                        (user_email,),
                    )
                    member_row = cur.fetchone()
                    if member_row:
                        context["id_tier_saya"] = member_row.get("id_tier")
                        context["total_miles"] = member_row.get("total_miles", 0)
    except Exception as e:
        print(f"Error fetch info tier: {e}")

    tier_berikutnya = None
    progress_persen = 0
    id_tier_saya = context.get("id_tier_saya")
    if id_tier_saya and context["tiers"]:
        tiers = context["tiers"]
        for i, t in enumerate(tiers):
            if t["id_tier"] == id_tier_saya:
                if i + 1 < len(tiers):
                    tier_berikutnya = tiers[i + 1]
                    total = context.get("total_miles", 0) or 0
                    target = tier_berikutnya["minimal_tier_miles"]
                    progress_persen = min(int((total / target) * 100), 100) if target > 0 else 100
                break

    context["tier_berikutnya"] = tier_berikutnya
    context["progress_persen"] = progress_persen
    return render(request, 'rewards/info_tier.html', context)


def laporan_transaksi(request):
    user_email = request.session.get("user_email")
    role = request.session.get("role")

    if not user_email:
        return redirect("authentication:login")

    transaksi_gabungan = []

    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

                # Beli Package
                if role == "member":
                    cur.execute(
                        """
                        SELECT p.timestamp, p.email_member, p.id_award_miles_package,
                               a.jumlah_award_miles
                        FROM member_award_miles_package p
                        LEFT JOIN award_miles_package a ON a.id = p.id_award_miles_package
                        WHERE p.email_member = %s
                        """,
                        (user_email,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT p.timestamp, p.email_member, p.id_award_miles_package,
                               a.jumlah_award_miles
                        FROM member_award_miles_package p
                        LEFT JOIN award_miles_package a ON a.id = p.id_award_miles_package
                        """
                    )
                for p in cur.fetchall():
                    miles = p["jumlah_award_miles"] or 0
                    transaksi_gabungan.append({
                        "jenis": "Beli Package", "aktor": p["email_member"],
                        "detail": f"Beli {p['id_award_miles_package']}", "miles": f"+{miles:,}",
                        "is_negative": False, "raw_time": str(p["timestamp"]),
                        "tanggal": str(p["timestamp"])[:16].replace("T", " "), "dapat_hapus": True,
                    })

                # Redeem
                if role == "member":
                    cur.execute(
                        """
                        SELECT r.timestamp, r.email_member, r.kode_hadiah, h.miles, h.nama
                        FROM redeem r
                        LEFT JOIN hadiah h ON h.kode_hadiah = r.kode_hadiah
                        WHERE r.email_member = %s
                        """,
                        (user_email,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT r.timestamp, r.email_member, r.kode_hadiah, h.miles, h.nama
                        FROM redeem r
                        LEFT JOIN hadiah h ON h.kode_hadiah = r.kode_hadiah
                        """
                    )
                for r in cur.fetchall():
                    miles = r["miles"] or 0
                    nama_hadiah = r["nama"] if r["nama"] else r["kode_hadiah"]
                    transaksi_gabungan.append({
                        "jenis": "Redeem Hadiah", "aktor": r["email_member"],
                        "detail": f"Tukar {nama_hadiah}", "miles": f"-{miles:,}",
                        "is_negative": True, "raw_time": str(r["timestamp"]),
                        "tanggal": str(r["timestamp"])[:16].replace("T", " "), "dapat_hapus": True,
                    })

                # Transfer
                if role == "member":
                    cur.execute(
                        "SELECT * FROM transfer WHERE email_member_1=%s",
                        (user_email,),
                    )
                    for t in cur.fetchall():
                        transaksi_gabungan.append({
                            "jenis": "Transfer Keluar", "aktor": t["email_member_2"],
                            "detail": t.get("catatan", "-"), "miles": f"-{t['jumlah']:,}",
                            "is_negative": True, "raw_time": str(t["timestamp"]),
                            "tanggal": str(t["timestamp"])[:16].replace("T", " "), "dapat_hapus": True,
                        })
                    cur.execute(
                        "SELECT * FROM transfer WHERE email_member_2=%s",
                        (user_email,),
                    )
                    for t in cur.fetchall():
                        transaksi_gabungan.append({
                            "jenis": "Transfer Masuk", "aktor": t["email_member_1"],
                            "detail": t.get("catatan", "-"), "miles": f"+{t['jumlah']:,}",
                            "is_negative": False, "raw_time": str(t["timestamp"]),
                            "tanggal": str(t["timestamp"])[:16].replace("T", " "), "dapat_hapus": True,
                        })
                else:
                    cur.execute("SELECT * FROM transfer")
                    for t in cur.fetchall():
                        transaksi_gabungan.append({
                            "jenis": "Transfer Miles",
                            "aktor": f"{t['email_member_1']} → {t['email_member_2']}",
                            "detail": t.get("catatan", "-"), "miles": f"{t['jumlah']:,}",
                            "is_negative": False, "raw_time": str(t["timestamp"]),
                            "tanggal": str(t["timestamp"])[:16].replace("T", " "), "dapat_hapus": True,
                        })

                    cur.execute(
                        "SELECT id, email_member, timestamp FROM claim_missing_miles WHERE status_penerimaan='Disetujui'"
                    )
                    for k in cur.fetchall():
                        transaksi_gabungan.append({
                            "jenis": "Klaim", "aktor": k["email_member"], "detail": "-",
                            "miles": "+1,000", "is_negative": False, "raw_time": str(k["timestamp"]),
                            "tanggal": str(k["timestamp"])[:16].replace("T", " "), "dapat_hapus": False,
                        })

        transaksi_gabungan.sort(key=lambda x: x["raw_time"], reverse=True)

        context_stats = {}
        if role == "staf":
            total_miles_beredar = 0
            try:
                with _get_conn() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute("SELECT total_miles FROM member")
                        total_miles_beredar = sum(m.get("total_miles", 0) or 0 for m in cur.fetchall())
            except Exception:
                pass
            bulan_ini = datetime.datetime.now().strftime("%Y-%m")
            total_redeem_bulan_ini = sum(1 for t in transaksi_gabungan if t["jenis"] == "Redeem Hadiah" and t["tanggal"].startswith(bulan_ini))
            total_klaim_disetujui = sum(1 for t in transaksi_gabungan if t["jenis"] == "Klaim")
            context_stats = {
                "total_miles_beredar": f"{total_miles_beredar:,}",
                "total_redeem_bulan_ini": f"{total_redeem_bulan_ini:,}",
                "total_klaim_disetujui": f"{total_klaim_disetujui:,}",
            }

    except Exception as e:
        print(f"Error fetching laporan transaksi: {e}")
        context_stats = {}

    top_member = []
    if role == "staf":
        try:
            with _get_conn() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM get_top5_member_by_miles()")
                    top_member = [dict(r) for r in cur.fetchall()]
            if top_member:
                peringkat_pertama = top_member[0]
                messages.success(
                    request,
                    f"SUKSES: Daftar Top 5 Member berdasarkan total miles berhasil diperbarui, "
                    f"dengan peringkat pertama \"{peringkat_pertama['email']}\" "
                    f"memiliki {int(peringkat_pertama['total_miles'])} miles."
                )
        except Exception as e:
            print(f"Error fetching top member via stored procedure: {e}")

    return render(request, 'rewards/laporan_transaksi.html', {
        "transaksi_list": transaksi_gabungan,
        "role": role,
        "top_member": top_member,
        **context_stats,
    })