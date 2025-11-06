from flask import Flask, jsonify
import requests
import time
import threading
from collections import deque

app = Flask(__name__)

# =========================================================
# 💾 Bộ nhớ tạm – giữ VÔ HẠN PHIÊN (không xóa)
# =========================================================
history = deque()  # không giới hạn maxlen
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
    "id": "biios2502"
}

# =========================================================
# 🔹 10 Thuật toán soi cầu nâng cao Pentter AI Mix (deterministic)
# =========================================================

def algo_v1_basic(history, totals, win_log):
    if len(history) < 2:
        return {"du_doan": "Đang khởi tạo...", "do_tin_cay": 0}
    return {"du_doan": "Tài" if history[-1] == "Xỉu" else "Xỉu", "do_tin_cay": 78}

def algo_v2_repeat_break(history, totals, win_log):
    if len(history) < 3:
        return {"du_doan": "Đang học cầu...", "do_tin_cay": 0}
    if history[-1] == history[-2]:
        return {"du_doan": history[-1], "do_tin_cay": 83}
    return {"du_doan": "Tài" if history[-1] == "Xỉu" else "Xỉu", "do_tin_cay": 79}

def algo_v3_sumtrend(history, totals, win_log):
    if len(totals) < 3:
        return {"du_doan": "Đang khởi động...", "do_tin_cay": 0}
    avg = sum(totals[-3:]) / 3
    trend = "Tài" if avg > 10.5 else "Xỉu"
    return {"du_doan": trend, "do_tin_cay": 85}

def algo_v4_balance(history, totals, win_log):
    count_tai = history.count("Tài")
    count_xiu = history.count("Xỉu")
    if abs(count_tai - count_xiu) > 3:
        # nếu lệch, dự đoán đảo chiều cho cân bằng
        return {"du_doan": "Tài" if count_tai < count_xiu else "Xỉu", "do_tin_cay": 87}
    return {"du_doan": history[-1] if len(history)>0 else "Tài", "do_tin_cay": 82}

def algo_v5_truebalance(history, totals, win_log):
    if len(history) < 3:
        return {"du_doan": "Đang học cầu...", "do_tin_cay": 0}
    last3 = list(history)[-3:]
    win_rate = win_log.count(True) / max(1, len(win_log))
    if all(h == last3[0] for h in last3):
        return {"du_doan": last3[0], "do_tin_cay": round(94 + win_rate * 3, 1)}
    if len(totals) >= 2 and abs(totals[-1] - totals[-2]) >= 3:
        trend = "Tài" if totals[-1] > 10.5 else "Xỉu"
        return {"du_doan": trend, "do_tin_cay": round(88 + win_rate * 6, 1)}
    return {"du_doan": "Tài" if win_rate < 0.5 else "Xỉu", "do_tin_cay": round(77 + win_rate * 15, 1)}

def algo_v6_wave(history, totals, win_log):
    if len(history) < 5:
        return {"du_doan": "Đang chờ dữ liệu...", "do_tin_cay": 0}
    pattern = history[-5:]
    if pattern.count("Tài") == 3:
        return {"du_doan": "Tài", "do_tin_cay": 90}
    if pattern.count("Xỉu") == 3:
        return {"du_doan": "Xỉu", "do_tin_cay": 90}
    return {"du_doan": "Tài" if (totals and totals[-1] > 11) else "Xỉu", "do_tin_cay": 80}

def algo_v7_pentter(history, totals, win_log):
    if len(history) < 6:
        return {"du_doan": "Đang học cầu...", "do_tin_cay": 0}
    last6 = history[-6:]
    pattern = "".join("T" if x == "Tài" else "X" for x in last6)
    if pattern in ["TTTTTT", "XXXXXX"]:
        return {"du_doan": last6[-1], "do_tin_cay": 95}
    elif pattern.endswith("TXTXTX"):
        return {"du_doan": "Tài", "do_tin_cay": 88}
    elif pattern.endswith("XTXTXT"):
        return {"du_doan": "Xỉu", "do_tin_cay": 88}
    return {"du_doan": history[-1], "do_tin_cay": 80}

def algo_v8_adapt_winrate(history, totals, win_log):
    win_rate = win_log.count(True) / max(1, len(win_log))
    if win_rate < 0.5:
        trend = "Tài"
    elif win_rate > 0.7:
        trend = "Xỉu"
    else:
        trend = "Tài" if (totals and totals[-1] > 11) else "Xỉu"
    return {"du_doan": trend, "do_tin_cay": round(75 + win_rate * 25, 1)}

def algo_v9_combo(history, totals, win_log):
    if len(history) < 4 or len(totals) < 4:
        return {"du_doan": "Đang khởi tạo...", "do_tin_cay": 0}
    avg = sum(totals[-4:]) / 4
    trend = "Tài" if avg > 10 else "Xỉu"
    if history[-1] == trend:
        return {"du_doan": trend, "do_tin_cay": 91}
    return {"du_doan": trend, "do_tin_cay": 84}

def algo_v10_dynamic(history, totals, win_log):
    if len(history) < 8:
        return {"du_doan": "Đang thu thập dữ liệu...", "do_tin_cay": 0}
    last8 = history[-8:]
    count_t = last8.count("Tài")
    count_x = last8.count("Xỉu")
    if count_t > count_x:
        return {"du_doan": "Tài", "do_tin_cay": 89}
    elif count_x > count_t:
        return {"du_doan": "Xỉu", "do_tin_cay": 89}
    else:
        trend = "Tài" if (totals and totals[-1] > 11) else "Xỉu"
        return {"du_doan": trend, "do_tin_cay": 83}

# danh sách thuật toán (deterministic)
algos = [
    algo_v1_basic, algo_v2_repeat_break, algo_v3_sumtrend, algo_v4_balance,
    algo_v5_truebalance, algo_v6_wave, algo_v7_pentter, algo_v8_adapt_winrate,
    algo_v9_combo, algo_v10_dynamic
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
# 🔹 Thread cập nhật dữ liệu + chọn thuật toán tốt nhất (NO RANDOM)
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

                # chạy tất cả thuật toán (deterministic) và chọn best theo do_tin_cay
                results = []
                for algo in algos:
                    try:
                        r = algo(history, totals, win_log)
                        # đảm bảo cấu trúc đúng
                        if isinstance(r, dict) and "du_doan" in r and "do_tin_cay" in r:
                            results.append((algo, r))
                    except Exception as e:
                        # nếu 1 thuật toán lỗi thì bỏ qua (log để debug)
                        print(f"[⚠️] Algo {algo.__name__} lỗi: {e}")

                # lọc những dự đoán đã sẵn sàng (do_tin_cay>0 và du_doan là Tài/Xỉu)
                ready = [item for item in results if item[1]["do_tin_cay"] and item[1]["du_doan"] in ("Tài","Xỉu")]

                if ready:
                    # chọn thuật toán có do_tin_cay lớn nhất (deterministic)
                    best_algo, best_res = max(ready, key=lambda x: x[1]["do_tin_cay"])
                else:
                    # fallback: dùng algo_v5_truebalance nếu chưa có algo sẵn sàng
                    best_algo = algo_v5_truebalance
                    best_res = best_algo(history, totals, win_log)

                du_doan = best_res["du_doan"]
                tin_cay = best_res["do_tin_cay"]
                pattern = "".join("T" if h == "Tài" else "X" for h in history)

                # ghi log đúng/sai (chỉ khi dự đoán là rõ ràng)
                if len(history) > 1 and du_doan in ("Tài","Xỉu"):
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
                    "pattern": pattern,
                    "algo": best_algo.__name__,
                    "id": "biios2502"
                }

                print(f"[✅] Phiên {phien} | 🎲 {dice} ({tong}) → {ketqua} | 🔮 {best_algo.__name__} → {du_doan} ({tin_cay}%) | Pattern: {pattern}")
                last_phien = phien
        else:
            print("[⚠️] Không lấy được dữ liệu, chờ 5s...")
        time.sleep(5)

# =========================================================
# 🔹 API Endpoint 1: dữ liệu đầy đủ
# =========================================================
@app.route("/api/taixiu", methods=["GET"])
def api_sunwin():
    return jsonify(last_data)

# =========================================================
# 🔹 API Endpoint 2: pattern soi cầu Pentter cho JS
# =========================================================
@app.route("/api/taixiu/pattern", methods=["GET"])
def api_pattern():
    pattern = "".join("T" if h == "Tài" else "X" for h in history)
    return jsonify({
        "pattern": pattern,
        "length": len(pattern),
        "last5": pattern[-5:],
        "last10": pattern[-10:],
        "du_doan": last_data.get("du_doan"),
        "do_tin_cay": last_data.get("do_tin_cay"),
        "phien": last_data.get("phien"),
        "algo": last_data.get("algo")
    })

# =========================================================
# 🚀 Khởi chạy Flask Server
# =========================================================
if __name__ == "__main__":
    threading.Thread(target=background_updater, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
