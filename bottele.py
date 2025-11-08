import os
import math
from flask import Flask
import threading
import telebot

# ====== TOKEN ======
# Bạn giữ nguyên cách dùng token trực tiếp hay ENV đều được.
TOKEN = "8542527882:AAE6lAkI8u5PBCtLg1Q80S746IMiOzDKLJg"
bot = telebot.TeleBot(TOKEN)

# ================== HÀM TÍNH TOÁN ==================
def lam_tron_quy_tac(x: float) -> int:
    """
    Làm tròn: nếu phần thập phân trong [0.5 .. 0.9] -> làm tròn lên.
    Ngược lại dùng round mặc định.
    """
    frac = x - int(x)
    if 0.5 <= frac <= 0.9:
        return math.ceil(x)
    return round(x)

def tinh_Rs(p_raw: int, b_raw: int, o: int, t: int):
    """
    Áp dụng thay thế:
      - Nếu P=0 -> 2 ; Nếu B=0 -> 3
      - P=1, B=1 giữ nguyên
    R1..R5 theo thứ tự ưu tiên nhân/chia trước, cộng/trừ sau.
    """
    p_calc = 2 if p_raw == 0 else p_raw
    b_calc = 3 if b_raw == 0 else b_raw

    R1 = (p_calc * 2) + (b_calc * 3) / t
    R2 = (p_calc * 2) + (b_calc * 3) - o
    R3 = (p_calc * 2) + (b_calc * 3) + o
    R4 = (p_calc * 2) + (b_calc * 3) - t
    R5 = (p_calc * 2) + (b_calc * 3) + t

    return [lam_tron_quy_tac(x) for x in (R1, R2, R3, R4, R5)]

def dinh_dang_o_va_xu_huong(p_raw: int, b_raw: int):
    """
    Bước 3: Định dạng Ô và xu hướng chính xác theo mô tả của bạn.

    - Ô (O-label):
        P chẵn -> 0, P lẻ -> 1 ; B chẵn -> 0, B lẻ -> 1
        00->CC, 11->LL, 10->LC, 01->CL

    - Quy tắc xu hướng:
        CC: P0 < B0 -> Ngược ; P0 > B0 -> Thuận ; P0 = B0 -> Ngược
        LL: P1 < B1 -> Ngược ; P1 > B1 -> Thuận ; P1 = B1 -> Thuận
        CL: P0 < B1 -> Ngược ; P0 > B1 -> Thuận
        LC: P1 < B0 -> Ngược ; P1 > B0 -> Thuận
    """
    p_even = (p_raw % 2 == 0)
    b_even = (b_raw % 2 == 0)

    if p_even and b_even:
        o_label = "CC"
        if p_raw < b_raw:
            xu = "Ngược"
        elif p_raw > b_raw:
            xu = "Thuận"
        else:
            xu = "Ngược"  # bằng nhau trong CC -> Ngược
    elif (not p_even) and (not b_even):
        o_label = "LL"
        if p_raw < b_raw:
            xu = "Ngược"
        elif p_raw > b_raw:
            xu = "Thuận"
        else:
            xu = "Thuận"  # bằng nhau trong LL -> Thuận
    elif p_even and (not b_even):
        o_label = "CL"
        xu = "Thuận" if p_raw > b_raw else "Ngược"
    else:
        o_label = "LC"
        xu = "Thuận" if p_raw > b_raw else "Ngược"

    return o_label, xu

def quyet_dinh_cuoi(R, xu_huong: str):
    """
    @Xu hướng 1 (Thuận):
        - Nhóm (R1,R2,R3): nếu ĐA SỐ lẻ -> Player (P), nếu ĐA SỐ chẵn -> Banker (B)
        - Nhóm (R4,R5): nếu CÓ ÍT NHẤT 1 số chẵn -> Player (P), nếu cả 2 đều lẻ -> Banker (B)
    @Xu hướng 2 (Ngược):
        - Nhóm (R1,R2,R3): nếu ĐA SỐ chẵn -> Player (P), nếu ĐA SỐ lẻ -> Banker (B)
        - Nhóm (R4,R5): nếu CÓ ÍT NHẤT 1 số lẻ -> Player (P), nếu cả 2 đều chẵn -> Banker (B)

    Gộp 2 phán quyết: nếu trùng -> chọn kết quả đó, nếu mâu thuẫn -> tie-break
    dùng đa số (tổng số lẻ của 5 R). Nếu vẫn khó xử, ưu tiên R5 >= 2*R2 -> Banker, ngược lại Player.
    (Tie-break chỉ dùng khi 2 nhánh mâu thuẫn; phần mô tả gốc không nêu, nên đây là quy tắc phân xử tối thiểu.)
    """
    r1, r2, r3, r4, r5 = R
    group1_odd_cnt = sum(x % 2 for x in (r1, r2, r3))
    group1_even_cnt = 3 - group1_odd_cnt
    group2_has_even = (r4 % 2 == 0) or (r5 % 2 == 0)
    group2_has_odd = (r4 % 2 == 1) or (r5 % 2 == 1)

    if xu_huong == "Thuận":
        d1 = "P" if group1_odd_cnt >= 2 else "B"
        d2 = "P" if group2_has_even else "B"
    else:  # Ngược
        d1 = "P" if group1_even_cnt >= 2 else "B"
        d2 = "P" if group2_has_odd else "B"

    if d1 == d2:
        final_side = d1
    else:
        # Tie-break: dựa đa số toàn cục
        total_odd = sum(x % 2 for x in (r1, r2, r3, r4, r5))
        total_even = 5 - total_odd
        if total_odd > total_even:
            final_side = "P" if xu_huong == "Thuận" else "B"
        elif total_even > total_odd:
            final_side = "B" if xu_huong == "Thuận" else "P"
        else:
            # Cực hiếm khi 2-2-1 cân bằng cảm giác; dùng chốt R5 vs 2*R2
            final_side = "B" if r5 >= 2 * r2 else "P"

    return "Banker (B)" if final_side == "B" else "Player (P)"

# ================== BOT HANDLER ==================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    text = message.text.strip()
    try:
        pb, o, t = text.split('-')
        p_raw, b_raw = map(int, pb.split('/'))
        o = int(o)
        t = int(t)

        R = tinh_Rs(p_raw, b_raw, o, t)
        o_label, xu_huong = dinh_dang_o_va_xu_huong(p_raw, b_raw)
        ket_qua_cuoi = quyet_dinh_cuoi(R, xu_huong)

        reply = (
            f"📌 {text}\n\n"
            f"35-A-LV1b@{text}\n"
            f"R1={R[0]}  R2={R[1]}  R3={R[2]}  R4={R[3]}  R5={R[4]}\n\n"
            f"Xu hướng: {xu_huong}\n"
            f"Ô: {o_label}\n\n"
            f"👉 KẾT QUẢ CUỐI CÙNG: {ket_qua_cuoi}"
        )
    except Exception:
        reply = "⚠️ Nhập đúng dạng: P/B-O-T (vd: 2/4-1-4)"

    bot.reply_to(message, reply)

print("🤖 Bot đang chạy (Auto Restart Enabled)...")

def start_bot():
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print("⚠️ Bot lỗi, đang tự khởi động lại...", e)

# chạy bot trong luồng riêng
threading.Thread(target=start_bot, daemon=True).start()

# Flask giữ bot sống trên Render
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running and auto-restarting!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

