from flask import Flask, jsonify
import requests
import time
import threading
from collections import deque
import statistics

app = Flask(__name__)

# =========================================================
# 💾 Bộ nhớ tạm – giữ VÔ HẠN PHIÊN (không xóa)
# =========================================================
history = deque()
totals = deque()
win_log = deque()

last_data = {
    "phien": None,
    "xucxac1": 0,
    "xucxac2": 0,
    "xucxac3": 0,
    "tong": 0,
    "ketqua": "",
    "du_doan": "Đang khởi động...",
    "do_tin_cay": 0,
    "pattern": "",
    "id": "độc quyền "
}

# =========================================================
# 🔹AI TRÍ TUE 2025 BẢN VIP PRO CỦA TUẤN
# =========================================================
def ai1_tanso(history, totals):
    if len(history) < 6: return {"du_doan": "Tài", "do_tin_cay": 70}
    t = history[-6:].count("Tài")
    x = history[-6:].count("Xỉu")
    if t > x: return {"du_doan": "Xỉu", "do_tin_cay": 88}
    elif x > t: return {"du_doan": "Tài", "do_tin_cay": 68}
    else: return {"du_doan": history[-1], "do_tin_cay": 80}

def ai2_chan_le(history, totals):
    if len(totals) < 5: return {"du_doan": "Tài", "do_tin_cay": 70}
    chan = sum(1 for t in totals[-5:] if t % 2 == 0)
    le = 5 - chan
    if chan > le: return {"du_doan": "Xỉu", "do_tin_cay": 86}
    else: return {"du_doan": "Tài", "do_tin_cay": 86}

def ai3_trung_binh(history, totals):
    if len(totals) < 5: return {"du_doan": "Tài", "do_tin_cay": 70}
    avg = statistics.mean(totals[-5:])
    if avg > 10.8: return {"du_doan": "Tài", "do_tin_cay": 98}
    elif avg < 10.2: return {"du_doan": "Xỉu", "do_tin_cay": 99}
    else: return {"du_doan": "Tài" if totals[-1] >= 11 else "Xỉu", "do_tin_cay": 80}

def ai4_bien_dong(history, totals):
    if len(totals) < 4: return {"du_doan": "Tài", "do_tin_cay": 70}
    diff = totals[-1] - totals[-3]
    if diff > 2: return {"du_doan": "Tài", "do_tin_cay": 90}
    elif diff < -2: return {"du_doan": "Xỉu", "do_tin_cay": 100}
    else: return {"du_doan": "Tài" if totals[-1] >= 11 else "Xỉu", "do_tin_cay": 78}

def ai5_cau_day(history, totals):
    if len(history) < 5: return {"du_doan": "Tài", "do_tin_cay": 70}
    last = history[-1]
    count = 0
    for h in reversed(history):
        if h == last: count += 1
        else: break
    if count >= 4: return {"du_doan": "Xỉu" if last == "Tài" else "Tài", "do_tin_cay": 93}
    else: return {"du_doan": last, "do_tin_cay": 80}

def ai6_nhip_dao(history, totals):
    if len(history) < 6: return {"du_doan": "Tài", "do_tin_cay": 70}
    seq = "".join("T" if h == "Tài" else "X" for h in history[-6:])
    if seq.endswith("TXTX") or seq.endswith("XTXT"):
        return {"du_doan": "Tài" if seq[-1] == "X" else "Xỉu", "do_tin_cay": 91}
    return {"du_doan": history[-1], "do_tin_cay": 80}

def ai7_lech_tong(history, totals):
    if len(totals) < 5: return {"du_doan": "Tài", "do_tin_cay": 35}
    avg = statistics.mean(totals[-5:])
    current = totals[-1]
    if current > avg + 1: return {"du_doan": "Xỉu", "do_tin_cay": 75}
    elif current < avg - 1: return {"du_doan": "Tài", "do_tin_cay": 83}
    else: return {"du_doan": history[-1], "do_tin_cay": 78}

def ai8_chan_le_cau(history, totals):
    if len(totals) < 5: return {"du_doan": "Tài", "do_tin_cay": 70}
    seq = [t % 2 for t in totals[-5:]]
    if all(s == 0 for s in seq): return {"du_doan": "Xỉu", "do_tin_cay": 91}
    if all(s == 1 for s in seq): return {"du_doan": "Tài", "do_tin_cay": 93}
    return {"du_doan": "Tài" if seq[-1] == 0 else "Xỉu", "do_tin_cay": 80}

def ai9_swing_ai(history, totals):
    if len(totals) < 6: return {"du_doan": "Tài", "do_tin_cay": 70}
    swing = max(totals[-6:]) - min(totals[-6:])
    if swing >= 6: return {"du_doan": "Tài", "do_tin_cay": 90}
    elif swing <= 2: return {"du_doan": "Xỉu", "do_tin_cay": 88}
    else: return {"du_doan": "Tài" if totals[-1] >= 11 else "Xỉu", "do_tin_cay": 80}

def ai10_cau_ngan(history, totals):
    if len(history) < 6: return {"du_doan": "Tài", "do_tin_cay": 74}
    last6 = history[-6:]
    if last6.count("Tài") == 3:
        return {"du_doan": "Tài" if last6[-1] == "Xỉu" else "Xỉu", "do_tin_cay": 77}
    return {"du_doan": history[-1], "do_tin_cay": 78}

def ai11_trend(history, totals):
    if len(totals) < 5: return {"du_doan": "Tài", "do_tin_cay": 70}
    diff = [totals[i] - totals[i - 1] for i in range(-1, -5, -1)]
    pos = sum(1 for d in diff if d > 0)
    neg = sum(1 for d in diff if d < 0)
    if pos >= 3: return {"du_doan": "Tài", "do_tin_cay": 65}
    if neg >= 3: return {"du_doan": "Xỉu", "do_tin_cay": 10}
    return {"du_doan": history[-1], "do_tin_cay": 80}

def ai12_median_ai(history, totals):
    if len(totals) < 5: return {"du_doan": "Tài", "do_tin_cay": 70}
    median = statistics.median(totals[-5:])
    if median > 10.5: return {"du_doan": "Tài", "do_tin_cay": 84}
    else: return {"du_doan": "Xỉu", "do_tin_cay": 86}

def ai13_stable(history, totals):
    if len(history) < 6: return {"du_doan": "Tài", "do_tin_cay": 70}
    stable = all(h == history[-1] for h in history[-3:])
    if stable: return {"du_doan": history[-1], "do_tin_cay": 93}
    else: return {"du_doan": "Tài" if history[-1] == "Xỉu" else "Xỉu", "do_tin_cay": 82}

def ai14_balance(history, totals):
    t = history.count("Tài")
    x = history.count("Xỉu")
    if t > x: return {"du_doan": "Xỉu", "do_tin_cay": 67}
    elif x > t: return {"du_doan": "Tài", "do_tin_cay": 40}
    else: return {"du_doan": history[-1], "do_tin_cay": 80}

def ai15_even_weight(history, totals):
    even = sum(1 for t in totals[-8:] if t % 2 == 0)
    if even >= 6: return {"du_doan": "Xỉu", "do_tin_cay": 60}
    if even <= 2: return {"du_doan": "Tài", "do_tin_cay": 50}
    return {"du_doan": "Tài" if totals[-1] >= 11 else "Xỉu", "do_tin_cay": 89}

def ai16_recent_shift(history, totals):
    if len(totals) < 4: return {"du_doan": "Tài", "do_tin_cay": 70}
    if (totals[-1] > totals[-2] < totals[-3]) or (totals[-1] < totals[-2] > totals[-3]):
        return {"du_doan": "Tài" if totals[-1] < 10 else "Xỉu", "do_tin_cay": 67}
    return {"du_doan": "Tài" if totals[-1] >= 11 else "Xỉu", "do_tin_cay": 80}

def ai17_gradient_ai(history, totals):
    if len(totals) < 5: return {"du_doan": "Tài", "do_tin_cay": 70}
    grad = (totals[-1] - totals[-5]) / 4
    if grad > 0.6: return {"du_doan": "Tài", "do_tin_cay": 90}
    elif grad < -0.6: return {"du_doan": "Xỉu", "do_tin_cay": 90}
    return {"du_doan": "Tài" if totals[-1] >= 11 else "Xỉu", "do_tin_cay": 88}

def ai18_wave_ai(history, totals):
    if len(history) < 6: return {"du_doan": "Tài", "do_tin_cay": 50}
    seq = "".join("T" if h == "Tài" else "X" for h in history[-6:])
    if "TXT" in seq: return {"du_doan": "Tài", "do_tin_cay": 89}
    if "XTX" in seq: return {"du_doan": "Xỉu", "do_tin_cay": 59}
    return {"du_doan": history[-1], "do_tin_cay": 80}

def ai19_weight_mix(history, totals):
    if len(history) < 6 or len(totals) < 6: return {"du_doan": "Tài", "do_tin_cay": 70}
    avg = statistics.mean(totals[-6:])
    last = history[-1]
    if avg >= 11 and last == "Tài": return {"du_doan": "Tài", "do_tin_cay": 94}
    if avg <= 10 and last == "Xỉu": return {"du_doan": "Xỉu", "do_tin_cay": 64}
    return {"du_doan": "Tài" if avg > 10.5 else "Xỉu", "do_tin_cay": 84}

def ai20_final_balance(history, totals):
    if len(history) < 10: return {"du_doan": "Tài", "do_tin_cay": 71}
    last5 = history[-5:]
    t = last5.count("Tài")
    x = last5.count("Xỉu")
    avg = statistics.mean(totals[-5:])
    if t > x and avg > 11: return {"du_doan": "Tài", "do_tin_cay": 96}
    elif x > t and avg < 10: return {"du_doan": "Xỉu", "do_tin_cay": 55}
    else: return {"du_doan": "Tài" if totals[-1] >= 11 else "Xỉu", "do_tin_cay": 81}

# =========================================================
# 🔹 AI THONG MINH 2025
# =========================================================
algos = [
    ai1_tanso, ai2_chan_le, ai3_trung_binh, ai4_bien_dong,
    ai5_cau_day, ai6_nhip_dao, ai7_lech_tong, ai8_chan_le_cau,
    ai9_swing_ai, ai10_cau_ngan, ai11_trend, ai12_median_ai,
    ai13_stable, ai14_balance, ai15_even_weight, ai16_recent_shift,
    ai17_gradient_ai, ai18_wave_ai, ai19_weight_mix, ai20_final_balance
]

# =========================================================
# 🔹 API Tele68 (nguồn thật)
# =========================================================
def get_taixiu_data():
    url = "https://wtxmd52.tele68.com/v1/txmd5/sessions"
    try:
        res = requests.get(url, timeout=8)
        data = res.json()
        if "list" in data and len(data["list"]) > 0:
            newest = data["list"][0]
            phien = newest.get("id")
            dice = newest.get("dices", [1, 2, 3])
            tong = newest.get("point", sum(dice))
            ketqua = newest.get("resultTruyenThong", "").upper()
            ketqua = "Tài" if ketqua == "TAI" else "Xỉu"
            return phien, dice, tong, ketqua
    except Exception as e:
        print(f"[❌] Lỗi lấy dữ liệu: {e}")
    return None

# =========================================================
# 🔹 Thread cập nhật dữ liệu + chọn thuật toán tốt nhất
# =========================================================
def background_updater():
    global last_data
    last_phien = None

    while True:
        data = get_taixiu_data()
        if data:
            phien, dice, tong, ketqua = data
            if phien != last_phien:
                history.append(ketqua)
                totals.append(tong)

                results = []
                for algo in algos:
                    try:
                        r = algo(history, totals)
                        if "du_doan" in r and "do_tin_cay" in r:
                            results.append((algo.__name__, r))
                    except Exception as e:
                        print(f"[⚠️] Lỗi {algo.__name__}: {e}")

                best_algo, best_res = max(results, key=lambda x: x[1]["do_tin_cay"])
                du_doan = best_res["du_doan"]
                tin_cay = best_res["do_tin_cay"]

                win_log.append(du_doan == ketqua)

                last_data = {
                    "phien": phien,
                    "xucxac1": dice[0],
                    "xucxac2": dice[1],
                    "xucxac3": dice[2],
                    "tong": tong,
                    "ketqua": ketqua,
                    "du_doan": du_doan,
                    "do_tin_cay": tin_cay,
                    "pattern": "".join("T" if h == "Tài" else "X" for h in history),
                  
                    "id": "Độc quyền "
                }

                print(f"[✅] Phiên {phien} | 🎲 {dice} ({tong}) → {ketqua} | 🔮 {best_algo} → {du_doan} ({tin_cay}%)")
                last_phien = phien
        else:
            print("[⚠️] Không lấy được dữ liệu, chờ 5s...")
        time.sleep(5)

# =========================================================
# 🔹 API Endpoint
# =========================================================
@app.route("/api/taixiu", methods=["GET"])
def api_taixiu():
    return jsonify(last_data)

@app.route("/api/taixiu/pattern", methods=["GET"])
def api_pattern():
    pattern = "".join("T" if h == "Tài" else "X" for h in history)
    return jsonify({
        "pattern": pattern,
        "length": len(pattern),
        "du_doan": last_data["du_doan"],
        "do_tin_cay": last_data["do_tin_cay"],
        
    })

# =========================================================
# 🔹 Chạy nền
# =========================================================
if __name__ == "__main__":
    # Khởi động luồng nền để cập nhật dữ liệu liên tục
    threading.Thread(target=background_updater, daemon=True).start()
    
    # Chạy Flask API thật (dùng cho Termux, Pydroid, VPS đều được)
    app.run(host="0.0.0.0", port=5000)
