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
# 💎 Pentter UltraHybrid V4.4 TruePredict
# =========================================================
def algo_pentter_ultrahybrid_v44(history, totals, win_log):
    """
    💎 Pentter UltraHybrid V4.4 TruePredict
    🎯 Dự đoán sau 2 phiên đầu (học cầu sớm hơn)
    🔹 Cân bằng pattern, không thiên Tài
    🔹 Độ tin cậy 75–97%
    """
    if len(history) < 2:
        return {"du_doan": "Đang thu thập...", "do_tin_cay": 0.0}

    win_rate = win_log.count(True) / max(len(win_log), 1)
    recent = list(history)[-6:] if len(history) >= 6 else list(history)
    pattern = "".join("T" if h == "Tài" else "X" for h in recent)
    last = recent[-1]

    # ======= 1️⃣ Cầu bệt mạnh =======
    if len(recent) >= 4 and all(h == last for h in recent[-4:]):
        return {"du_doan": last, "do_tin_cay": round(93 + win_rate*4, 1)}

    # ======= 2️⃣ Cầu đảo xen kẽ =======
    if pattern.endswith(("TXTX", "XTXT")):
        next_pred = "Tài" if pattern[-1] == "X" else "Xỉu"
        return {"du_doan": next_pred, "do_tin_cay": round(89 + win_rate*6, 1)}

    # ======= 3️⃣ Cầu 2-1-2 hoặc 1-2-1 =======
    if len(recent) >= 3 and recent[-3] == recent[-1] and recent[-2] != recent[-1]:
        return {"du_doan": recent[-1], "do_tin_cay": round(87 + win_rate*5, 1)}

    # ======= 4️⃣ Cân bằng thống kê nhanh =======
    count_tai = recent.count("Tài")
    count_xiu = len(recent) - count_tai
    if abs(count_tai - count_xiu) >= 3:
        next_pred = "Xỉu" if count_tai > count_xiu else "Tài"
        return {"du_doan": next_pred, "do_tin_cay": round(86 + win_rate*5, 1)}

    # ======= 5️⃣ Phân tích biến thiên tổng =======
    if len(totals) >= 3:
        diff = totals[-1] - totals[-2]
        trend = "Tài" if totals[-1] > 10.5 else "Xỉu"
        conf = 80 + abs(diff)*2 + win_rate*8
        return {"du_doan": trend, "do_tin_cay": round(min(conf, 96), 1)}

    # ======= 6️⃣ Nếu chưa nhận cầu rõ, dựa theo nhịp thắng gần nhất =======
    du_doan = "Tài" if win_rate < 0.45 else "Xỉu"
    return {"du_doan": du_doan, "do_tin_cay": round(75 + win_rate*20, 1)}


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
# 🔹 Thread cập nhật dữ liệu
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

                # chạy thuật toán Pentter UltraHybrid v4.4
                result = algo_pentter_ultrahybrid_v44(history, totals, win_log)
                du_doan = result["du_doan"]
                tin_cay = result["do_tin_cay"]
                pattern = "".join("T" if h == "Tài" else "X" for h in history)

                # ghi log đúng/sai
                if len(history) > 1 and du_doan in ["Tài", "Xỉu"]:
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
                    "id": "biios2502"
                }

                print(f"[✅] Phiên {phien} | 🎲 {dice} ({tong}) → {ketqua} | 🔮 Dự đoán: {du_doan} ({tin_cay}%) | Pattern: {pattern}")
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
        "du_doan": last_data["du_doan"],
        "do_tin_cay": last_data["do_tin_cay"],
        "phien": last_data["phien"]
    })


# =========================================================
# 🚀 Khởi chạy Flask Server
# =========================================================
if __name__ == "__main__":
    threading.Thread(target=background_updater, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
