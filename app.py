import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import date, datetime, timedelta
import calendar

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Robot Demo Booking",
    page_icon="🤖",
    layout="wide",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── General ── */
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
h1 { font-size: 1.4rem !important; font-weight: 600 !important; margin-bottom: 0 !important; }

/* ── Robot Cards ── */
.robot-card-free {
    background: #EAF3DE; border: 1px solid #97C459;
    border-radius: 10px; padding: 10px 8px;
    text-align: center; cursor: pointer;
    transition: transform .15s;
}
.robot-card-free:hover { transform: scale(1.04); }
.robot-card-booked {
    background: #FCEBEB; border: 1px solid #F09595;
    border-radius: 10px; padding: 10px 8px;
    text-align: center; opacity: .85;
}
.card-id-free  { font-size: 13px; font-weight: 600; color: #3B6D11; }
.card-id-booked{ font-size: 13px; font-weight: 600; color: #A32D2D; }
.card-status-free  { font-size: 11px; color: #639922; }
.card-status-booked{ font-size: 11px; color: #E24B4A; }
.card-who { font-size: 10px; color: #A32D2D; margin-top: 2px; }

/* ── Status Badges ── */
.badge-confirmed { background:#EAF3DE; color:#3B6D11; padding:2px 8px; border-radius:6px; font-size:12px; }
.badge-pending   { background:#FAEEDA; color:#854F0B; padding:2px 8px; border-radius:6px; font-size:12px; }
.badge-cancelled { background:#FCEBEB; color:#A32D2D; padding:2px 8px; border-radius:6px; font-size:12px; }

/* ── Stat Cards ── */
.stat-box {
    background: #f8f9fa; border-radius: 10px;
    padding: 14px 16px; text-align: center;
}
.stat-num  { font-size: 28px; font-weight: 700; color: #1D9E75; }
.stat-label{ font-size: 13px; color: #666; margin-top: 2px; }

/* ── Heatmap ── */
.hm-cell-0 { background:#f0f0f0; border-radius:6px; padding:6px; text-align:center; font-size:12px; color:#999; }
.hm-cell-1 { background:#C0DD97; border-radius:6px; padding:6px; text-align:center; font-size:12px; color:#27500A; font-weight:600; }
.hm-cell-2 { background:#639922; border-radius:6px; padding:6px; text-align:center; font-size:12px; color:#EAF3DE; font-weight:600; }
.hm-cell-3 { background:#F09595; border-radius:6px; padding:6px; text-align:center; font-size:12px; color:#501313; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ROBOT DATA
# ─────────────────────────────────────────────
ROBOTS = {
    "Flash Bot": [f"FLASH-{str(i).zfill(2)}" for i in range(1, 7)],
    "Ketty":     [f"KETTY-{str(i).zfill(2)}" for i in range(1, 5)],
    "T300":      ["T300-01"],
}
ALL_ROBOTS = [r for group in ROBOTS.values() for r in group]

THAI_MONTHS = ["","มกราคม","กุมภาพันธ์","มีนาคม","เมษายน","พฤษภาคม",
               "มิถุนายน","กรกฎาคม","สิงหาคม","กันยายน","ตุลาคม","พฤศจิกายน","ธันวาคม"]

SHEET_NAME  = "RobotDemoBookings"   # ชื่อ Google Sheet ของคุณ
WORKSHEET   = "Bookings"            # ชื่อ tab ใน Sheet

# ─────────────────────────────────────────────
# GOOGLE SHEETS CONNECTION
# ─────────────────────────────────────────────
@st.cache_resource
def get_gsheet():
    """เชื่อมต่อ Google Sheets ผ่าน Service Account"""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )
    client = gspread.authorize(creds)
    sheet  = client.open(SHEET_NAME).worksheet(WORKSHEET)
    return sheet


def load_bookings() -> pd.DataFrame:
    """โหลดข้อมูลการจองทั้งหมดจาก Google Sheets"""
    try:
        sheet = get_gsheet()
        data  = sheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=[
                "ID","dates","robot","name","phone",
                "start_time","end_time","note","status","created_at"
            ])
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"❌ ไม่สามารถโหลดข้อมูลได้: {e}")
        return pd.DataFrame()


def save_booking(dates_list: list, robot: str, name: str,
                 phone: str, start_time: str, end_time: str,
                 note: str) -> bool:
    """บันทึกการจองใหม่ลง Google Sheets (1 row ต่อ 1 วัน)"""
    try:
        sheet = get_gsheet()
        existing = sheet.get_all_records()
        next_id  = (max([int(r["ID"]) for r in existing], default=0) + 1) if existing else 1

        rows_to_add = []
        for d in dates_list:
            rows_to_add.append([
                next_id,
                str(d),          # วันที่ในรูปแบบ YYYY-MM-DD
                robot, name, phone,
                start_time, end_time,
                note, "confirmed",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ])
            next_id += 1

        sheet.append_rows(rows_to_add)
        # ล้าง cache เพื่อโหลดข้อมูลใหม่
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่สำเร็จ: {e}")
        return False


def update_status(row_index: int, new_status: str):
    """อัปเดตสถานะการจอง (row_index = ลำดับใน sheet เริ่มจาก 2)"""
    try:
        sheet = get_gsheet()
        # คอลัมน์ status = คอลัมน์ที่ 9 (I)
        sheet.update_cell(row_index + 2, 9, new_status)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ อัปเดตไม่สำเร็จ: {e}")
        return False


def delete_booking(row_index: int):
    """ลบแถวการจอง"""
    try:
        sheet = get_gsheet()
        sheet.delete_rows(row_index + 2)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ ลบไม่สำเร็จ: {e}")
        return False


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def get_booked_robots_on_date(df: pd.DataFrame, target_date: date) -> dict:
    """คืน dict {robot_id: name} สำหรับวันที่ที่เลือก"""
    if df.empty:
        return {}
    date_str = target_date.strftime("%Y-%m-%d")
    booked = df[
        (df["dates"] == date_str) &
        (df["status"] != "cancelled")
    ]
    return dict(zip(booked["robot"], booked["name"]))


def fmt_thai_date(d: date) -> str:
    return f"{d.day} {THAI_MONTHS[d.month]} {d.year + 543}"  # แปลงเป็น พ.ศ.


# ─────────────────────────────────────────────
# ── SESSION STATE ──
# ─────────────────────────────────────────────
if "view_date"       not in st.session_state: st.session_state.view_date = date.today()
if "selected_dates"  not in st.session_state: st.session_state.selected_dates = []
if "booking_robot"   not in st.session_state: st.session_state.booking_robot = None
if "show_form"       not in st.session_state: st.session_state.show_form = False
if "active_tab"      not in st.session_state: st.session_state.active_tab = "booking"


# ─────────────────────────────────────────────
# ── HEADER ──
# ─────────────────────────────────────────────
col_logo, col_nav = st.columns([3, 2])
with col_logo:
    st.markdown("## 🤖 Robot Demo Booking")
with col_nav:
    tab = st.radio(
        "หน้า", ["📅 จองหุ่นยนต์", "🗂 Admin Dashboard"],
        horizontal=True, label_visibility="collapsed",
        key="tab_radio",
    )
    st.session_state.active_tab = "booking" if "จอง" in tab else "admin"

st.divider()

# โหลดข้อมูล (cache 60 วินาที)
@st.cache_data(ttl=60)
def cached_load():
    return load_bookings()

df = cached_load()

# ══════════════════════════════════════════════
# ── PAGE: จองหุ่นยนต์ ──
# ══════════════════════════════════════════════
if st.session_state.active_tab == "booking":

    # ── Date Navigation ──
    col_lbl, col_date, col_prev, col_next, col_today = st.columns([1.2, 2.5, 1, 1, 1])
    with col_lbl:
        st.markdown("<div style='padding-top:6px;font-size:14px;color:#666'>ดูสถานะวันที่</div>",
                    unsafe_allow_html=True)
    with col_date:
        st.markdown(
            f"<div style='background:#f0f0f0;border-radius:8px;padding:6px 14px;"
            f"font-size:14px;font-weight:600;margin-top:2px'>"
            f"📅 {fmt_thai_date(st.session_state.view_date)}</div>",
            unsafe_allow_html=True,
        )
    with col_prev:
        if st.button("◀ ก่อนหน้า", use_container_width=True):
            st.session_state.view_date -= timedelta(days=1)
            st.rerun()
    with col_next:
        if st.button("ถัดไป ▶", use_container_width=True):
            st.session_state.view_date += timedelta(days=1)
            st.rerun()
    with col_today:
        if st.button("วันนี้", use_container_width=True):
            st.session_state.view_date = date.today()
            st.rerun()

    st.markdown(
        "🟢 **ว่าง** — กดปุ่มด้านล่างเพื่อจอง &nbsp;|&nbsp; 🔴 **จองแล้ว**",
        unsafe_allow_html=True,
    )
    st.markdown("")

    # ── Robot Status Grid ──
    booked_map = get_booked_robots_on_date(df, st.session_state.view_date)

    for group_name, robot_ids in ROBOTS.items():
        st.markdown(f"**{group_name}** <span style='font-size:12px;color:#888'>{len(robot_ids)} ตัว</span>",
                    unsafe_allow_html=True)
        cols = st.columns(len(robot_ids))
        for i, rid in enumerate(robot_ids):
            is_booked = rid in booked_map
            with cols[i]:
                if is_booked:
                    st.markdown(
                        f"<div class='robot-card-booked'>"
                        f"<div class='card-id-booked'>{rid}</div>"
                        f"<div class='card-status-booked'>จองแล้ว</div>"
                        f"<div class='card-who'>{booked_map[rid][:8]}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div class='robot-card-free'>"
                        f"<div class='card-id-free'>{rid}</div>"
                        f"<div class='card-status-free'>ว่าง</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if not is_booked:
                        if st.button("จอง", key=f"book_{rid}", use_container_width=True):
                            st.session_state.booking_robot = rid
                            st.session_state.selected_dates = []
                            st.session_state.show_form = True
                            st.rerun()
        st.markdown("")

    # ── Booking Form (แสดงด้านล่างเมื่อกดปุ่มจอง) ──
    if st.session_state.show_form and st.session_state.booking_robot:
        st.divider()
        st.markdown(
            f"### 📋 ฟอร์มจอง Demo — "
            f"<span style='background:#EAF3DE;color:#3B6D11;padding:3px 10px;"
            f"border-radius:6px;font-size:14px'>{st.session_state.booking_robot}</span>",
            unsafe_allow_html=True,
        )

        with st.form("booking_form", clear_on_submit=True):
            # Multi-date picker
            st.markdown("**เลือกวันที่จอง** (เลือกหลายวันได้)")
            selected_dates = st.multiselect(
                "วันที่",
                options=[
                    (date.today() + timedelta(days=i)).strftime("%Y-%m-%d")
                    for i in range(90)   # เลือกได้ 90 วันข้างหน้า
                ],
                format_func=lambda d: fmt_thai_date(
                    date(int(d[:4]), int(d[5:7]), int(d[8:10]))
                ),
                placeholder="คลิกเพื่อเลือกวันที่...",
                label_visibility="collapsed",
            )

            c1, c2 = st.columns(2)
            with c1:
                name  = st.text_input("ชื่อผู้จอง *", placeholder="ชื่อ-นามสกุล")
            with c2:
                phone = st.text_input("เบอร์โทรศัพท์", placeholder="08x-xxx-xxxx")

            c3, c4 = st.columns(2)
            with c3:
                start_time = st.selectbox("เวลาเริ่มต้น *",
                    ["09:00","10:00","11:00","13:00","14:00","15:00"])
            with c4:
                end_time = st.selectbox("เวลาสิ้นสุด *",
                    ["10:00","11:00","12:00","14:00","15:00","16:00"])

            note = st.text_input("หมายเหตุ", placeholder="วัตถุประสงค์ (ไม่บังคับ)")

            col_submit, col_cancel = st.columns([1, 3])
            with col_submit:
                submitted = st.form_submit_button(
                    "✅ ยืนยันการจอง", use_container_width=True, type="primary"
                )
            with col_cancel:
                cancelled = st.form_submit_button("ยกเลิก", use_container_width=False)

            if submitted:
                if not name:
                    st.error("กรุณาระบุชื่อผู้จอง")
                elif not selected_dates:
                    st.error("กรุณาเลือกอย่างน้อย 1 วัน")
                else:
                    ok = save_booking(
                        selected_dates,
                        st.session_state.booking_robot,
                        name, phone, start_time, end_time, note,
                    )
                    if ok:
                        dates_str = ", ".join([
                            fmt_thai_date(date(int(d[:4]),int(d[5:7]),int(d[8:10])))
                            for d in selected_dates
                        ])
                        st.success(
                            f"🎉 จองสำเร็จ! **{st.session_state.booking_robot}** "
                            f"วันที่: {dates_str}"
                        )
                        st.session_state.show_form = False
                        st.session_state.booking_robot = None
                        st.rerun()

            if cancelled:
                st.session_state.show_form = False
                st.session_state.booking_robot = None
                st.rerun()


# ══════════════════════════════════════════════
# ── PAGE: Admin Dashboard ──
# ══════════════════════════════════════════════
else:
    st.markdown("### 🗂 Admin Dashboard")

    if df.empty:
        st.info("ยังไม่มีข้อมูลการจอง")
        st.stop()

    # ── Stats ──
    total    = len(df)
    this_mon = df[df["dates"].str.startswith(date.today().strftime("%Y-%m"))].shape[0] if not df.empty else 0
    cancelled_n = df[df["status"] == "cancelled"].shape[0]
    top_robot = df[df["status"] != "cancelled"]["robot"].value_counts()
    top_name  = top_robot.index[0] if not top_robot.empty else "—"
    top_cnt   = int(top_robot.iloc[0]) if not top_robot.empty else 0

    s1, s2, s3, s4 = st.columns(4)
    for col, num, label in [
        (s1, total,       "การจองทั้งหมด"),
        (s2, this_mon,    "เดือนนี้"),
        (s3, cancelled_n, "ยกเลิกแล้ว"),
    ]:
        with col:
            st.markdown(
                f"<div class='stat-box'><div class='stat-num'>{num}</div>"
                f"<div class='stat-label'>{label}</div></div>",
                unsafe_allow_html=True,
            )
    with s4:
        st.markdown(
            f"<div class='stat-box'><div class='stat-num' style='font-size:18px'>{top_name}</div>"
            f"<div class='stat-label'>ยอดนิยม ({top_cnt} วัน-จอง)</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── Heatmap (เดือนปัจจุบัน) ──
    st.markdown("**ภาพรวมรายวัน (เดือนนี้)**")
    today = date.today()
    year, month = today.year, today.month
    days_in_month = calendar.monthrange(year, month)[1]
    first_weekday = calendar.monthrange(year, month)[0]  # 0=จันทร์

    # นับการจองต่อวัน
    month_str = today.strftime("%Y-%m")
    month_df  = df[(df["dates"].str.startswith(month_str)) & (df["status"] != "cancelled")]
    daily_cnt = month_df.groupby("dates").size().to_dict()
    max_cnt   = max(daily_cnt.values(), default=1)

    day_names = ["จ","อ","พ","พฤ","ศ","ส","อา"]
    hm_cols = st.columns(7)
    for i, d in enumerate(day_names):
        hm_cols[i].markdown(
            f"<div style='text-align:center;font-size:11px;color:#888;font-weight:600'>{d}</div>",
            unsafe_allow_html=True,
        )

    # เติมช่องว่างก่อนวันที่ 1 (ปฏิทินเริ่มจันทร์)
    all_cells = [""] * first_weekday
    for d in range(1, days_in_month + 1):
        all_cells.append(str(d))

    # padding ท้ายให้ครบแถว
    while len(all_cells) % 7 != 0:
        all_cells.append("")

    rows = [all_cells[i:i+7] for i in range(0, len(all_cells), 7)]
    for row in rows:
        row_cols = st.columns(7)
        for ci, cell in enumerate(row):
            if not cell:
                row_cols[ci].markdown("<div style='height:36px'></div>", unsafe_allow_html=True)
                continue
            day_key = f"{year}-{str(month).zfill(2)}-{str(cell).zfill(2)}"
            cnt = daily_cnt.get(day_key, 0)
            level = 0 if cnt == 0 else (3 if cnt >= 9 else (2 if cnt >= 5 else 1))
            today_mark = "border:2px solid #378ADD;" if int(cell) == today.day else ""
            row_cols[ci].markdown(
                f"<div class='hm-cell-{level}' style='{today_mark}'>"
                f"{cell}<br><span style='font-size:10px'>{cnt if cnt else ''}</span></div>",
                unsafe_allow_html=True,
            )

    st.markdown("")
    st.divider()

    # ── Filters ──
    st.markdown("**กรองข้อมูล**")
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 2])
    with fc1:
        f_from = st.date_input("จากวันที่", value=date(today.year, today.month, 1))
    with fc2:
        f_to   = st.date_input("ถึงวันที่",  value=date(today.year, today.month, days_in_month))
    with fc3:
        f_robot = st.selectbox("หุ่นยนต์", ["ทั้งหมด"] + ALL_ROBOTS)
    with fc4:
        f_status = st.selectbox("สถานะ", ["ทั้งหมด", "confirmed", "pending", "cancelled"])

    # Apply filters
    fdf = df.copy()
    fdf["dates"] = fdf["dates"].astype(str)
    fdf = fdf[
        (fdf["dates"] >= f_from.strftime("%Y-%m-%d")) &
        (fdf["dates"] <= f_to.strftime("%Y-%m-%d"))
    ]
    if f_robot != "ทั้งหมด":
        fdf = fdf[fdf["robot"] == f_robot]
    if f_status != "ทั้งหมด":
        fdf = fdf[fdf["status"] == f_status]

    st.markdown(f"**รายการจองทั้งหมด** — {len(fdf)} รายการ")

    # ── Booking Table ──
    if fdf.empty:
        st.info("ไม่พบรายการที่ตรงกับเงื่อนไข")
    else:
        STATUS_LABEL = {"confirmed":"✅ ยืนยันแล้ว","pending":"⏳ รอยืนยัน","cancelled":"❌ ยกเลิก"}

        for idx, (i, row) in enumerate(fdf.iterrows()):
            with st.expander(
                f"{'✅' if row['status']=='confirmed' else '⏳' if row['status']=='pending' else '❌'} "
                f"  {row['dates']}  |  {row['robot']}  |  {row['name']}  "
                f"  [{STATUS_LABEL.get(row['status'], row['status'])}]"
            ):
                dc1, dc2, dc3 = st.columns(3)
                dc1.markdown(f"**หุ่นยนต์:** {row['robot']}")
                dc1.markdown(f"**วันที่:** {row['dates']}")
                dc2.markdown(f"**ชื่อ:** {row['name']}")
                dc2.markdown(f"**เบอร์:** {row.get('phone','—')}")
                dc3.markdown(f"**เวลา:** {row.get('start_time','—')} – {row.get('end_time','—')}")
                dc3.markdown(f"**หมายเหตุ:** {row.get('note','—') or '—'}")

                ac1, ac2, ac3 = st.columns([2, 2, 4])
                new_status = ac1.selectbox(
                    "เปลี่ยนสถานะ",
                    ["confirmed","pending","cancelled"],
                    index=["confirmed","pending","cancelled"].index(row["status"]),
                    key=f"status_{i}",
                )
                if ac1.button("บันทึก", key=f"save_{i}"):
                    if update_status(idx, new_status):
                        st.success("อัปเดตสำเร็จ")
                        st.rerun()
                if ac2.button("🗑 ลบ", key=f"del_{i}", type="secondary"):
                    if delete_booking(idx):
                        st.success("ลบสำเร็จ")
                        st.rerun()

    # ── Export CSV ──
    st.divider()
    if not df.empty:
        csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "⬇️ ดาวน์โหลดข้อมูลทั้งหมด (CSV)",
            data=csv,
            file_name=f"robot_bookings_{date.today()}.csv",
            mime="text/csv",
        )
