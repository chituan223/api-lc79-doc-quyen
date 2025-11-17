import requests
import time
import threading
import statistics
import os
import math
from collections import deque
from typing import List, Dict, Optional, Tuple, Callable
from flask import Flask, jsonify

# Định nghĩa cấu trúc dữ liệu cho dự đoán
PredictionResult = Dict[str, any]

# Kích thước tối đa của lịch sử (cần đủ cho các thuật toán dài nhất)
MAX_HISTORY_SIZE = 30

# =========================================================
# I. KHU VỰC ĐỊNH NGHĨA THUẬT TOÁN (20 CHIẾN LƯỢC VIP PRO MỚI - V7.1)
# =========================================================

# Chức năng hỗ trợ
def _get_result_type(total: int) -> str:
    """Xác định kết quả là Tài hay Xỉu dựa trên tổng điểm."""
    if 11 <= total <= 17:
        return "Tài"
    elif 4 <= total <= 10:
        return "Xỉu"
    return "Lỗi Dữ Liệu"

def _get_momentum_bias(history: deque, totals: deque) -> str:
    """Xác định xu hướng ngắn hạn (3 phiên) để làm dự đoán mặc định khi không có tín hiệu mạnh."""
    if len(history) < 3:
        return "Tài" if history and history[-1] == "Tài" else "Xỉu"
    
    h_list = list(history)[-3:]
    t_list = list(totals)[-3:]
    
    # Đếm số lần Tài/Xỉu trong 3 phiên gần nhất
    count_tai = h_list.count("Tài")
    count_xiu = h_list.count("Xỉu")

    if count_tai >= 2:
        return "Tài"
    elif count_xiu >= 2:
        return "Xỉu"
    
    # Nếu cân bằng, dự đoán ngược lại kết quả cuối cùng (Nguyên tắc Hồi quy yếu)
    return "Xỉu" if history and history[-1] == "Tài" else "Tài"

# ==================== KHỐI 1: HỒI QUY & THỐNG KÊ CHUYÊN SÂU ====================

def new_ai1_double_mean_reversion_10(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Hồi quy kép về mức trung bình lý thuyết (10.5) trong 10 phiên. Chỉ dự đoán ngược lại xu hướng kéo dài."""
    if len(totals) < 10:
        return {"du_doan": "Tài", "do_tin_cay": 50.0}
    
    window = list(totals)[-10:]
    avg10 = statistics.mean(window)
    
    deviation = avg10 - 10.5
    
    if deviation > 1.5:
        # Tài kéo dài (avg > 12.0) -> Dự đoán hồi quy Xỉu (RẤT MẠNH)
        return {"du_doan": "Xỉu", "do_tin_cay": 91.5 + abs(deviation) * 2}
    if deviation < -1.5:
        # Xỉu kéo dài (avg < 9.0) -> Dự đoán hồi quy Tài (RẤT MẠNH)
        return {"du_doan": "Tài", "do_tin_cay": 91.0 + abs(deviation) * 2}
        
    # Trung tính: Dự đoán theo xu hướng ngắn hạn 3 phiên
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 60.0}

def new_ai2_bollinger_analog_std_15(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Dải Bollinger Analog: Nếu Total[-1] nằm ngoài 1.5 STD trong 15 phiên, dự đoán hồi quy."""
    if len(totals) < 15:
        return {"du_doan": "Xỉu", "do_tin_cay": 50.0}
        
    window = list(totals)[-15:]
    avg15 = statistics.mean(window)
    try:
        std15 = statistics.stdev(window)
    except statistics.StatisticsError:
        std15 = 0.0

    if std15 == 0.0:
        return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 60.0}

    upper_band = avg15 + 1.5 * std15
    lower_band = avg15 - 1.5 * std15
    current = totals[-1]
    
    if current > upper_band:
        # Chạm dải trên -> Quá mua -> Hồi quy Xỉu (MẠNH)
        return {"du_doan": "Xỉu", "do_tin_cay": 93.0 + (current - upper_band) * 2}
    if current < lower_band:
        # Chạm dải dưới -> Quá bán -> Hồi quy Tài (MẠNH)
        return {"du_doan": "Tài", "do_tin_cay": 92.5 + (lower_band - current) * 2}
        
    # Trong dải, dự đoán theo xu hướng trung bình
    if current > avg15:
        return {"du_doan": "Tài", "do_tin_cay": 70.0}
    else:
        return {"du_doan": "Xỉu", "do_tin_cay": 70.0}

def new_ai3_heiken_ashi_trend_6(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Xác nhận xu hướng MA 3 phiên liên tục để xác định nến xu hướng. Chỉ dự đoán khi có xu hướng mạnh."""
    if len(totals) < 6:
        return {"du_doan": "Tài", "do_tin_cay": 50.0}
    
    t_list = list(totals)
    ma_prev_3 = [statistics.mean(t_list[i-3:i]) for i in range(3, len(t_list) + 1)]
    
    if len(ma_prev_3) < 4:
        return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 60.0}

    last_4_ma = ma_prev_3[-4:]

    is_up_trend = all(last_4_ma[i] > last_4_ma[i-1] for i in range(1, 4))
    is_down_trend = all(last_4_ma[i] < last_4_ma[i-1] for i in range(1, 4))
    
    if is_up_trend:
        # Xu hướng tăng mạnh (MA 3 liên tục tăng) -> Tiếp tục Tài (RẤT MẠNH)
        return {"du_doan": "Tài", "do_tin_cay": 94.0}
    if is_down_trend:
        # Xu hướng giảm mạnh (MA 3 liên tục giảm) -> Tiếp tục Xỉu (RẤT MẠNH)
        return {"du_doan": "Xỉu", "do_tin_cay": 93.5}
        
    # Không có xu hướng mạnh, dự đoán theo bias ngắn hạn
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 65.0}

def new_ai4_z_score_outlier_20(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Phát hiện điểm ngoại lai Z-Score trong 20 phiên: Nếu Total cuối cùng > 2.5 STD, dự đoán đảo chiều."""
    if len(totals) < 20:
        return {"du_doan": "Xỉu", "do_tin_cay": 50.0}
        
    window = list(totals)[-20:]
    previous_window = window[:-1]
    avg19 = statistics.mean(previous_window)
    try:
        std19 = statistics.stdev(previous_window)
    except statistics.StatisticsError:
        std19 = 0.0
        
    current = totals[-1]

    if std19 == 0.0:
        return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 60.0}
        
    z_score = (current - avg19) / std19

    if z_score >= 2.5:
        # Ngoại lai Tài (Rất Tài) -> Dự đoán Hồi quy Xỉu (RẤT MẠNH)
        return {"du_doan": "Xỉu", "do_tin_cay": 95.0}
    if z_score <= -2.5:
        # Ngoại lai Xỉu (Rất Xỉu) -> Dự đoán Hồi quy Tài (RẤT MẠNH)
        return {"du_doan": "Tài", "do_tin_cay": 94.5}
        
    # Dự đoán theo hướng trung bình (gần AVG hơn)
    return {"du_doan": "Tài" if current > avg19 else "Xỉu", "do_tin_cay": 70.0}

def new_ai5_fibonacci_mean_oscillator_8(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Dao động Fibonacci so với trung bình 8 phiên: Nếu Total vượt quá 1.618 lần độ lệch trung bình, dự đoán ngược."""
    if len(totals) < 8:
        return {"du_doan": "Tài", "do_tin_cay": 50.0}
        
    window = list(totals)[-8:]
    avg8 = statistics.mean(window)
    current = totals[-1]
    diff = current - avg8
    fib_ratio = 1.618
    
    try:
        # Độ lệch tuyệt đối trung bình (Average Absolute Deviation)
        avg_abs_dev = statistics.mean(abs(t - avg8) for t in window)
    except statistics.StatisticsError:
        avg_abs_dev = 1.0

    threshold = fib_ratio * avg_abs_dev
    
    if diff >= threshold and diff > 1.0: # Phải vượt qua ngưỡng và biên độ > 1.0
        # Total rất cao so với trung bình -> Hồi quy Xỉu (MẠNH)
        return {"du_doan": "Xỉu", "do_tin_cay": 90.5 + abs(diff) * 2}
    if diff <= -threshold and diff < -1.0:
        # Total rất thấp so với trung bình -> Hồi quy Tài (MẠNH)
        return {"du_doan": "Tài", "do_tin_cay": 90.0 + abs(diff) * 2}
        
    # Dự đoán theo xu hướng ngắn hạn 3 phiên
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 65.0}

# ==================== KHỐI 2: NHẬN DẠNG MẪU & CHUỖI HIẾM ====================

def new_ai6_perfect_wave_pattern_5(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Mẫu Sóng Hoàn Hảo (T X X T T / X T T X X): Dự đoán theo mô hình đảo chiều sóng (Trend Continuation)."""
    if len(history) < 5:
        return {"du_doan": "Xỉu", "do_tin_cay": 50.0}
        
    seq = "".join("T" if h == "Tài" else "X" for h in list(history)[-5:])
    
    if seq == "TXXTT":
        # Sóng Tài (T T) bị đảo chiều đột ngột (T X X) và đang hồi lại (T T) -> Dự đoán Tài tiếp tục (MẠNH)
        return {"du_doan": "Tài", "do_tin_cay": 93.0}
    if seq == "XTTXX":
        # Sóng Xỉu (X X) bị đảo chiều đột ngột (X T T) và đang hồi lại (X X) -> Dự đoán Xỉu tiếp tục (MẠNH)
        return {"du_doan": "Xỉu", "do_tin_cay": 92.5}
        
    # Không khớp mẫu hiếm, dự đoán theo bias ngắn hạn
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 68.0}

def new_ai7_odd_even_bias_12(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Thiên vị Lẻ/Chẵn 12 phiên: Nếu có sự chênh lệch lớn về số lần Lẻ/Chẵn, dự đoán bù trừ (Reversal)."""
    if len(totals) < 12:
        return {"du_doan": "Tài", "do_tin_cay": 50.0}
        
    window = list(totals)[-12:]
    odd_count = sum(1 for t in window if t % 2 != 0)
    even_count = 12 - odd_count
    
    if odd_count >= 9:
        # Quá nhiều Lẻ (thường là Tài) -> Dự đoán Bù trừ Chẵn (dễ về Xỉu) (MẠNH)
        return {"du_doan": "Xỉu", "do_tin_cay": 89.0}
    if even_count >= 9:
        # Quá nhiều Chẵn (thường là Xỉu hoặc Tài Chẵn) -> Dự đoán Bù trừ Lẻ (dễ về Tài Lẻ) (MẠNH)
        return {"du_doan": "Tài", "do_tin_cay": 88.5}
        
    # Bình thường, dự đoán theo bias ngắn hạn
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 60.0}

def new_ai8_range_compression_8(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Nén phạm vi (Range Compression) 8 phiên: Biến động thấp (range < 3) -> Dự đoán Bùng nổ ngược lại kết quả cuối cùng."""
    if len(totals) < 8:
        return {"du_doan": "Xỉu", "do_tin_cay": 50.0}
        
    window = list(totals)[-8:]
    t_range = max(window) - min(window)
    
    if t_range <= 2:
        # Biến động cực thấp -> Sắp bùng nổ. Dự đoán ngược lại kết quả gần nhất (RẤT MẠNH)
        if history[-1] == "Tài":
            return {"du_doan": "Xỉu", "do_tin_cay": 91.0}
        else:
            return {"du_doan": "Tài", "do_tin_cay": 90.5}
            
    # Dự đoán theo bias ngắn hạn
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 65.0}

def new_ai9_triple_confirm_4(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Xác nhận 3 chỉ báo trong 4 phiên: 4 phiên liên tiếp T/X, 4 Total liên tục Tài/Xỉu biên, và MA 4 xác nhận. (Trend Continuation)"""
    if len(history) < 4 or len(totals) < 4:
        return {"du_doan": "Tài", "do_tin_cay": 50.0}
    
    h_list = list(history)[-4:]
    t_list = list(totals)[-4:]
    avg4 = statistics.mean(t_list)
    
    # Điều kiện nghiêm ngặt hơn
    is_trend_t = h_list == ["Tài", "Tài", "Tài", "Tài"] and all(t >= 12 for t in t_list) and avg4 >= 13.0
    is_trend_x = h_list == ["Xỉu", "Xỉu", "Xỉu", "Xỉu"] and all(t <= 9 for t in t_list) and avg4 <= 8.0
    
    if is_trend_t:
        return {"du_doan": "Tài", "do_tin_cay": 96.0} # Độ tin cậy cực cao
    if is_trend_x:
        return {"du_doan": "Xỉu", "do_tin_cay": 95.9} # Độ tin cậy cực cao
        
    # Dự đoán theo bias ngắn hạn
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 60.0}

def new_ai10_anti_martingale_3(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Ngăn chặn Martingale: Nếu mẫu xen kẽ (T X T) hoặc (X T X) xuất hiện, dự đoán Tài/Xỉu tiếp tục để phá vỡ chuỗi xen kẽ (Trend Continuation)."""
    if len(history) < 3:
        return {"du_doan": "Xỉu", "do_tin_cay": 50.0}
        
    seq = "".join("T" if h == "Tài" else "X" for h in list(history)[-3:])
    
    if seq == "TXT":
        # Đang xen kẽ, dự đoán T tiếp (chấm dứt chuỗi) (MẠNH)
        return {"du_doan": "Tài", "do_tin_cay": 90.0}
    if seq == "XTX":
        # Đang xen kẽ, dự đoán X tiếp (chấm dứt chuỗi) (MẠNH)
        return {"du_doan": "Xỉu", "do_tin_cay": 89.5}
        
    # Dự đoán theo bias ngắn hạn
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 65.0}

# ==================== KHỐI 3: DỰ ĐOÁN XU HƯỚNG VÀ GIAO CẮT ====================

def new_ai11_golden_cross_5_20(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Giao cắt Vàng/Tử thần MA 5 và 20 phiên. DỰ ĐOÁN THUẦN XU HƯỚNG."""
    if len(totals) < 20:
        return {"du_doan": "Tài", "do_tin_cay": 50.0}
    
    t_list = list(totals)
    
    # MA hiện tại (tính đến phiên cuối cùng)
    ma5_curr = statistics.mean(t_list[-5:])
    ma20_curr = statistics.mean(t_list[-20:])
    
    # MA phiên trước (tính đến phiên -1)
    ma5_prev = statistics.mean(t_list[-6:-1])
    ma20_prev = statistics.mean(t_list[-21:-1])
    
    if ma5_prev <= ma20_prev and ma5_curr > ma20_curr:
        # Giao cắt Vàng (Golden Cross) -> Dự đoán Tài (RẤT MẠNH)
        return {"du_doan": "Tài", "do_tin_cay": 94.0}
    if ma5_prev >= ma20_prev and ma5_curr < ma20_curr:
        # Giao cắt Tử thần (Death Cross) -> Dự đoán Xỉu (RẤT MẠNH)
        return {"du_doan": "Xỉu", "do_tin_cay": 93.8}
        
    # Không có giao cắt, nhưng MA ngắn vẫn nằm trên MA dài (Trend Continuation)
    if ma5_curr > ma20_curr:
        return {"du_doan": "Tài", "do_tin_cay": 75.0}
    elif ma5_curr < ma20_curr:
        return {"du_doan": "Xỉu", "do_tin_cay": 75.0}
        
    # Trung tính
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 60.0}

def new_ai12_bear_bull_trap_3(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Bẫy Tài/Xỉu (Trap): T T X (Xỉu nhẹ) -> Dự đoán Tài tiếp; X X T (Tài nhẹ) -> Dự đoán Xỉu tiếp (Trend Continuation)."""
    if len(history) < 3:
        return {"du_doan": "Xỉu", "do_tin_cay": 50.0}
        
    seq = "".join("T" if h == "Tài" else "X" for h in list(history)[-3:])
    
    if seq == "TTX" and totals[-1] <= 11:
        # 2 Tài mạnh bị một Xỉu nhẹ phủ nhận (Total Xỉu phải nhỏ/biên) -> Dự đoán Tài tiếp tục (MẠNH)
        return {"du_doan": "Tài", "do_tin_cay": 92.0}
    if seq == "XXT" and totals[-1] >= 10:
        # 2 Xỉu mạnh bị một Tài nhẹ phủ nhận (Total Tài phải nhỏ/biên) -> Dự đoán Xỉu tiếp tục (MẠNH)
        return {"du_doan": "Xỉu", "do_tin_cay": 91.5}
        
    # Dự đoán theo bias ngắn hạn
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 65.0}

def new_ai13_cumulative_delta_7(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Delta tích lũy 7 phiên: Tổng chênh lệch so với 10.5. Nếu Delta > 7 hoặc < -7, dự đoán Hồi quy."""
    if len(totals) < 7:
        return {"du_doan": "Tài", "do_tin_cay": 50.0}
    
    window = list(totals)[-7:]
    # Tính Cumulative Delta (Total - 10.5)
    cumulative_delta = sum(t - 10.5 for t in window)
    
    if cumulative_delta > 7.0:
        # Tích lũy Tài quá lớn -> Hồi quy Xỉu (MẠNH)
        return {"du_doan": "Xỉu", "do_tin_cay": 92.5}
    if cumulative_delta < -7.0:
        # Tích lũy Xỉu quá lớn -> Hồi quy Tài (MẠNH)
        return {"du_doan": "Tài", "do_tin_cay": 92.0}
        
    # Dự đoán theo hướng cân bằng (ngược lại xu hướng Delta)
    if cumulative_delta > 0:
        return {"du_doan": "Xỉu", "do_tin_cay": 70.0}
    elif cumulative_delta < 0:
        return {"du_doan": "Tài", "do_tin_cay": 70.0}
    else:
        return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 60.0}

def new_ai14_volatility_breakout_8(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Vượt ngưỡng biến động: 7 phiên ổn định (STD < 1.5) và phiên cuối cùng là Tài/Xỉu biên (>= 15 hoặc <= 6). (Trend Continuation)"""
    if len(totals) < 8:
        return {"du_doan": "Xỉu", "do_tin_cay": 50.0}
    
    window = list(totals)[-8:]
    current = totals[-1]
    
    try:
        # Tính STD trên 7 phiên trước (không bao gồm phiên cuối cùng)
        std7 = statistics.stdev(window[:-1])
    except statistics.StatisticsError:
        std7 = 0.0
        
    # 7 phiên trước ổn định (STD thấp)
    is_low_volatility = std7 <= 1.5
    
    if is_low_volatility:
        if current >= 15:
            # Bùng nổ Tài mạnh -> Tiếp tục Tài (RẤT MẠNH)
            return {"du_doan": "Tài", "do_tin_cay": 94.5}
        if current <= 6:
            # Bùng nổ Xỉu mạnh -> Tiếp tục Xỉu (RẤT MẠNH)
            return {"du_doan": "Xỉu", "do_tin_cay": 94.0}
            
    # Dự đoán theo bias ngắn hạn
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 60.0}

def new_ai15_stochastic_extreme_5(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Cực trị Ngẫu nhiên 5 phiên: Total nằm sát Max/Min 4 phiên trước đó, dự đoán ngược (Hồi quy)."""
    if len(totals) < 5:
        return {"du_doan": "Tài", "do_tin_cay": 50.0}
        
    window = list(totals)[-5:]
    low = min(window[:-1]) # Min của 4 phiên trước
    high = max(window[:-1]) # Max của 4 phiên trước
    current = totals[-1]
    
    if high - low == 0:
        return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 60.0}
        
    # Tỷ lệ so với phạm vi (0% = min, 100% = max)
    percent_k = ((current - low) / (high - low)) * 100
    
    if percent_k >= 95.0:
        # Rất gần mức Max -> Hồi quy Xỉu (MẠNH)
        return {"du_doan": "Xỉu", "do_tin_cay": 93.5}
    if percent_k <= 5.0:
        # Rất gần mức Min -> Hồi quy Tài (MẠNH)
        return {"du_doan": "Tài", "do_tin_cay": 93.0}
        
    # Dự đoán theo hướng Stochastic (Nếu > 50 -> Tài, < 50 -> Xỉu)
    if percent_k >= 50:
        return {"du_doan": "Tài", "do_tin_cay": 70.0}
    else:
        return {"du_doan": "Xỉu", "do_tin_cay": 70.0}

# ==================== KHỐI 4: PHÂN TÍCH CHU KỲ VÀ ĐỘNG LƯỢNG (HOÀN THIỆN) ====================

def new_ai16_power_trend_5(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Xu hướng Quyền lực 5 phiên: Nếu 5 phiên Tài liên tiếp có Total tăng dần (hoặc 5 Xỉu giảm dần). (Trend Continuation)"""
    if len(totals) < 5 or len(history) < 5:
        return {"du_doan": "Xỉu", "do_tin_cay": 50.0}
    
    t = list(totals)[-5:]
    h = list(history)[-5:]
    
    # Tài có Total tăng dần (từ 11->17)
    is_t_increasing = h == ["Tài"] * 5 and all(t[i] >= t[i-1] for i in range(1, 5))
    # Xỉu có Total giảm dần (từ 10->4)
    is_x_decreasing = h == ["Xỉu"] * 5 and all(t[i] <= t[i-1] for i in range(1, 5))
    
    if is_t_increasing:
        return {"du_doan": "Tài", "do_tin_cay": 95.0} # Trend Tài cực mạnh
    if is_x_decreasing:
        return {"du_doan": "Xỉu", "do_tin_cay": 94.5} # Trend Xỉu cực mạnh
        
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 65.0}

def new_ai17_mean_crossing_5(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Kiểm tra Giao cắt MA 5: Nếu Total vượt qua MA 5, dự đoán tiếp tục xu hướng (Trend Continuation)."""
    if len(totals) < 6:
        return {"du_doan": "Tài", "do_tin_cay": 50.0}
    
    t_list = list(totals)
    current = t_list[-1]
    
    # MA 5 phiên hiện tại và phiên trước
    ma5_curr = statistics.mean(t_list[-5:])
    ma5_prev = statistics.mean(t_list[-6:-1])
    
    # Giao cắt Tài (Total vượt MA từ dưới lên)
    if t_list[-2] < ma5_prev and current > ma5_curr:
        return {"du_doan": "Tài", "do_tin_cay": 90.0}
    
    # Giao cắt Xỉu (Total vượt MA từ trên xuống)
    if t_list[-2] > ma5_prev and current < ma5_curr:
        return {"du_doan": "Xỉu", "do_tin_cay": 89.5}
    
    # Nếu đang nằm trên/dưới MA, tiếp tục xu hướng
    if current > ma5_curr:
        return {"du_doan": "Tài", "do_tin_cay": 75.0}
    if current < ma5_curr:
        return {"du_doan": "Xỉu", "do_tin_cay": 75.0}
        
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 60.0}

def new_ai18_reversal_block_4(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Mẫu Đảo chiều Khối 4: T T T X hoặc X X X T. Dự đoán tiếp tục xu hướng trước đó (Reversal)."""
    if len(history) < 4:
        return {"du_doan": "Xỉu", "do_tin_cay": 50.0}
    
    seq = "".join("T" if h == "Tài" else "X" for h in list(history)[-4:])
    
    if seq == "TTTX":
        # 3 Tài bị 1 Xỉu đảo ngược -> Dự đoán hồi quy Tài (MẠNH)
        return {"du_doan": "Tài", "do_tin_cay": 92.0}
    if seq == "XXXT":
        # 3 Xỉu bị 1 Tài đảo ngược -> Dự đoán hồi quy Xỉu (MẠNH)
        return {"du_doan": "Xỉu", "do_tin_cay": 91.5}
        
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 65.0}

def new_ai19_fibonacci_retracement_3(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Hồi phục Fibonacci 3: T X T hoặc X T X, trong đó phiên giữa (X/T) có Total gần với MA 3 phiên (Reversion to Mean)."""
    if len(totals) < 3:
        return {"du_doan": "Tài", "do_tin_cay": 50.0}
    
    t_list = list(totals)[-3:]
    h_list = list(history)[-3:]
    avg3 = statistics.mean(t_list)
    
    # Kiểm tra mô hình T X T hoặc X T X
    if h_list[0] == h_list[2] and h_list[0] != h_list[1]:
        # Phiên giữa (h_list[1]) phải gần MA (nghĩa là một cú hồi phục yếu)
        if abs(t_list[1] - avg3) <= 0.5:
            if h_list[0] == "Tài": # T X T (X gần mean) -> Dự đoán T tiếp tục
                return {"du_doan": "Tài", "do_tin_cay": 90.5}
            else: # X T X (T gần mean) -> Dự đoán X tiếp tục
                return {"du_doan": "Xỉu", "do_tin_cay": 90.0}
            
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 60.0}

def new_ai20_perfect_balance_10(history: deque, totals: deque, win_log: deque) -> PredictionResult:
    """Kiểm tra Cân bằng Hoàn hảo 10 phiên: Tỉ lệ T:X gần 5:5 -> Dự đoán Bùng nổ (ngược lại kết quả cuối cùng)."""
    if len(history) < 10:
        return {"du_doan": "Xỉu", "do_tin_cay": 50.0}
    
    h_list = list(history)[-10:]
    count_tai = h_list.count("Tài")
    count_xiu = 10 - count_tai
    
    # Nếu Tỉ lệ là 5:5 hoặc 6:4 / 4:6 (cân bằng) -> Dự đoán Bùng nổ ngược lại (Reversal)
    if 4 <= count_tai <= 6:
        if history[-1] == "Tài":
            # Thị trường cân bằng, kết thúc bằng Tài -> Dự đoán Xỉu (Bùng nổ)
            return {"du_doan": "Xỉu", "do_tin_cay": 91.0}
        else:
            # Thị trường cân bằng, kết thúc bằng Xỉu -> Dự đoán Tài (Bùng nổ)
            return {"du_doan": "Tài", "do_tin_cay": 90.5}
        
    return {"du_doan": _get_momentum_bias(history, totals), "do_tin_cay": 65.0}

# Danh sách tất cả 20 thuật toán VIP PRO
ALL_ALGOS: List[Callable] = [
    new_ai1_double_mean_reversion_10, new_ai2_bollinger_analog_std_15,
    new_ai3_heiken_ashi_trend_6, new_ai4_z_score_outlier_20,
    new_ai5_fibonacci_mean_oscillator_8, new_ai6_perfect_wave_pattern_5,
    new_ai7_odd_even_bias_12, new_ai8_range_compression_8,
    new_ai9_triple_confirm_4, new_ai10_anti_martingale_3,
    new_ai11_golden_cross_5_20, new_ai12_bear_bull_trap_3,
    new_ai13_cumulative_delta_7, new_ai14_volatility_breakout_8,
    new_ai15_stochastic_extreme_5, new_ai16_power_trend_5,
    new_ai17_mean_crossing_5, new_ai18_reversal_block_4,
    new_ai19_fibonacci_retracement_3, new_ai20_perfect_balance_10
]


# =========================================================
# II. KHU VỰC ĐỊNH NGHĨA LỚP PREDICTOR (V7.1)
# =========================================================

class TaiXiuPredictor:
    """
    Lớp chính thực hiện việc fetch dữ liệu, lưu trữ lịch sử và đưa ra
    dự đoán Đồng Thuận (Consensus) dựa trên 20 thuật toán đã định nghĩa.
    """
    def __init__(self, api_url: str, app_id: str):
        self.api_url = api_url
        self.app_id = app_id
        
        # Lịch sử kết quả (Tài/Xỉu), Tổng điểm, và Log Win/Loss
        self.history: deque[str] = deque(maxlen=MAX_HISTORY_SIZE)
        self.totals: deque[int] = deque(maxlen=MAX_HISTORY_SIZE)
        self.win_log: deque[bool] = deque(maxlen=30)
        
        # ID phiên cuối cùng đã được xử lý
        self.last_phien_id: Optional[int] = None
        # Lưu trữ dự đoán của phiên cuối cùng (dùng để đánh giá Win/Loss cho phiên hiện tại)
        self.last_prediction_data: Optional[PredictionResult] = None
        
        # Danh sách thuật toán
        self.algos = ALL_ALGOS
        
        # Dữ liệu phiên mới nhất và dự đoán
        self.last_data: PredictionResult = {
            "phien": None,
            "xucxac1": 0, "xucxac2": 0, "xucxac3": 0,
            "tong": 0, "ketqua": "",
            "du_doan": "Đang khởi động...",
            "do_tin_cay": 0.0,
            "best_algo": "N/A",
            "id": f"VIP Analyzer Consensus V7.1 for {self.app_id}",
            "win_loss": "N/A"
        }

    def _fetch_data(self) -> Optional[Tuple[int, List[int], int, str]]:
        """Lấy dữ liệu phiên Tai Xiu từ API và chuẩn hóa."""
        # Thực hiện 3 lần thử lại với exponential backoff
        for attempt in range(3): 
            try:
                # API của bạn có thể yêu cầu header hoặc tham số khác
                res = requests.get(self.api_url, timeout=15)
                res.raise_for_status()
                data = res.json()
                
                if "list" in data and len(data["list"]) > 0:
                    newest = data["list"][0]
                    phien = int(newest.get("id", 0))
                    
                    # Xử lý dữ liệu xúc xắc (dices)
                    dices_raw = newest.get("dices", [])
                    if isinstance(dices_raw, str):
                        dice = [int(d) for d in dices_raw.split(',') if d.strip().isdigit()][:3]
                    elif isinstance(dices_raw, list):
                        dice = [int(d) for d in dices_raw][:3]
                    else:
                        dice = []
                        
                    # Tính lại tổng, đảm bảo dữ liệu chuẩn
                    tong = sum(dice) if len(dice) == 3 else newest.get("point", 0)
                    
                    # Chuẩn hóa kết quả (Tai/Xiu)
                    ketqua = _get_result_type(tong)
                        
                    # Chỉ trả về dữ liệu hợp lệ (tổng từ 4 đến 17)
                    if ketqua != "Lỗi Dữ Liệu":
                        return phien, dice, tong, ketqua
                
            except requests.exceptions.RequestException as e:
                # print(f"[❌] Lỗi lấy dữ liệu API (Thử {attempt+1}): {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt) # Exponential backoff
            except Exception as e:
                # print(f"[❌] Lỗi xử lý dữ liệu (Thử {attempt+1}): {e}")
                pass
                
        return None

    def _get_all_algorithm_predictions(self) -> List[Tuple[str, float, str]]:
        """Thực thi tất cả 20 thuật toán và trả về danh sách (du_doan, do_tin_cay, ten_algo)."""
        results = []
        for algo in self.algos:
            try:
                r = algo(self.history, self.totals, self.win_log)
                # Đảm bảo độ tin cậy nằm trong [50, 100]
                confidence = round(max(50.0, min(100.0, r["do_tin_cay"])), 2)
                
                # Chỉ đưa vào danh sách các thuật toán có độ tin cậy > 50.0 (tức là có dự đoán)
                if confidence > 50.0:
                    results.append((r["du_doan"], confidence, algo.__name__))
            except Exception as e:
                # print(f"[⚠️] Lỗi {algo.__name__}: {e}")
                pass
        return results

    def _consensus_prediction(self) -> PredictionResult:
        """Áp dụng cơ chế Đồng Thuận (Consensus) có trọng số từ 20 thuật toán."""
        
        all_results = self._get_all_algorithm_predictions()
        
        if not all_results:
            return {
                "du_doan": "Đang phân tích",
                "do_tin_cay": 0.0,
                "best_algo": "Chưa đủ dữ liệu (N/A)"
            }
        
        # 1. Tính điểm trọng số (Loại bỏ 50% cơ bản)
        weighted_score_tai = 0.0
        weighted_score_xiu = 0.0
        
        # 2. Theo dõi thuật toán mạnh nhất (để hiển thị)
        best_algo_name = "N/A"
        max_single_conf = 0.0

        for du_doan, conf, algo_name in all_results:
            # Update best single algo for display
            if conf > max_single_conf:
                max_single_conf = conf
                best_algo_name = algo_name
                
            # Trọng số: (Confidence - 50) => 0 đến 50 điểm
            weight = conf - 50.0
            
            if du_doan == "Tài":
                weighted_score_tai += weight
            elif du_doan == "Xỉu":
                weighted_score_xiu += weight
        
        # 3. Quyết định dựa trên Đồng Thuận
        if weighted_score_tai > weighted_score_xiu:
            final_du_doan = "Tài"
            total_weight = weighted_score_tai + weighted_score_xiu
            # Độ tin cậy = 50 + % margin của phe thắng so với tổng điểm trọng số (Margin * 50 điểm)
            if total_weight > 0:
                margin_percent = (weighted_score_tai - weighted_score_xiu) / total_weight
                final_conf = round(50.0 + margin_percent * 50.0, 2)
            else:
                final_conf = 50.0
            
        elif weighted_score_xiu > weighted_score_tai:
            final_du_doan = "Xỉu"
            total_weight = weighted_score_tai + weighted_score_xiu
            if total_weight > 0:
                margin_percent = (weighted_score_xiu - weighted_score_tai) / total_weight
                final_conf = round(50.0 + margin_percent * 50.0, 2)
            else:
                final_conf = 50.0

        else:
            # Hòa điểm, sử dụng bias ngắn hạn 3 phiên
            final_du_doan = _get_momentum_bias(self.history, self.totals) if self.history else "Tài"
            final_conf = 50.0
        
        final_conf = max(50.0, min(100.0, final_conf))

        # Trả về tên thuật toán mạnh nhất đơn lẻ để tiện theo dõi
        return {
             "du_doan": final_du_doan,
             "do_tin_cay": final_conf,
             "best_algo": f"Consensus (Strongest: {best_algo_name} with {max_single_conf}%)"
            }


    def predict(self):
        """Kiểm tra dữ liệu mới, cập nhật lịch sử và đưa ra dự đoán."""
        data = self._fetch_data()
        
        if data:
            phien, dice, tong, ketqua = data
            
            # 1. Phát hiện phiên mới (Nếu ID phiên mới hơn ID đã lưu)
            if phien != self.last_phien_id and phien is not None and len(dice) == 3:
                
                # --- CHU TRÌNH 1: Đánh giá phiên VỪA KẾT THÚC ---
                is_win_log = ""
                if self.last_phien_id is not None and self.last_prediction_data:
                    # Ghi lại kết quả dự đoán (Win/Loss) cho phiên vừa xong
                    last_prediction = self.last_prediction_data.get("du_doan")
                    if last_prediction not in ["Đang khởi động...", "Đang phân tích"]:
                        is_win = (last_prediction == ketqua)
                        self.win_log.append(is_win)
                        is_win_log = "WIN" if is_win else "LOSS"
                
                # 2. Cập nhật lịch sử với kết quả phiên mới
                self.history.append(ketqua)
                self.totals.append(tong)
                
                # --- CHU TRÌNH 2: Dự đoán cho phiên TIẾP THEO (Sử dụng Consensus) ---
                prediction_for_next = self._consensus_prediction()

                # 3. Cập nhật dữ liệu mới nhất (là kết quả phiên vừa xong)
                self.last_data = {
                    "phien": phien,
                    "xucxac1": dice[0],
                    "xucxac2": dice[1],
                    "xucxac3": dice[2],
                    "tong": tong,
                    "ketqua": ketqua,
                    # Dự đoán cho phiên TIẾP THEO
                    "du_doan": prediction_for_next["du_doan"],
                    "do_tin_cay": prediction_for_next["do_tin_cay"],
                    "best_algo": prediction_for_next["best_algo"],
                    "win_loss": is_win_log, # Thêm log Win/Loss vào kết quả hiển thị
                    "id": self.last_data["id"]
                }
                
                # Cập nhật ID phiên và lưu dự đoán để đánh giá trong lần chạy tiếp theo
                self.last_phien_id = phien
                self.last_prediction_data = prediction_for_next
                
                # print(f"[✅] Phiên {phien}: {ketqua} ({tong}). Dự đoán tiếp theo: {prediction_for_next['du_doan']} ({prediction_for_next['do_tin_cay']}%) - {is_win_log}")
            
            # 2. Nếu phiên KHÔNG mới (vẫn đang trong chu kỳ chờ)
            elif phien == self.last_phien_id:
                # Chỉ cập nhật dữ liệu phiên vừa xong (nếu cần) và giữ nguyên dự đoán
                self.last_data["phien"] = phien
                self.last_data["xucxac1"] = dice[0]
                self.last_data["xucxac2"] = dice[1]
                self.last_data["xucxac3"] = dice[2]
                self.last_data["tong"] = tong
                self.last_data["ketqua"] = ketqua
                # print(f"[⏳] Chờ phiên mới. Dự đoán hiện tại: {self.last_prediction_data.get('du_doan')} ({self.last_prediction_data.get('do_tin_cay')}%)")

        return self.last_data

# =========================================================
# III. KHU VỰC THỰC THI CHÍNH (FLASK API VÀ CHU TRÌNH LẶP)
# =========================================================

# Khai báo Flask App và Predictor
app = Flask(__name__)

# CẤU HÌNH QUAN TRỌNG: Thay đổi URL API và ID ứng dụng của bạn tại đây
# Vui lòng thay thế bằng API thực tế của bạn
API_URL = "https://wtxmd52.tele68.com/v1/txmd5/sessions" 
APP_ID = "MyTaiXiuAnalyzer"

predictor = TaiXiuPredictor(api_url=API_URL, app_id=APP_ID)

# Hàm chạy chu trình dự đoán liên tục trong luồng nền
def _run_predictor_loop(interval_seconds: int = 1):
    """Liên tục fetch dữ liệu, cập nhật lịch sử và đưa ra dự đoán."""
    print(f"[{APP_ID}] Bắt đầu chu trình dự đoán nền. Kiểm tra mỗi {interval_seconds} giây.")
    while True:
        try:
            predictor.predict()
        except Exception as e:
            # Ghi log lỗi nhưng không dừng chương trình
            print(f"[🔴 Lỗi Chu Trình] Không thể cập nhật dự đoán: {e}")
        time.sleep(interval_seconds)

@app.route('/predict', methods=['GET'])
def get_prediction():
    """Endpoint trả về dự đoán mới nhất."""
    # Trả về dữ liệu đã được cập nhật bởi luồng nền
    return jsonify(predictor.last_data)

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint kiểm tra trạng thái hoạt động."""
    return jsonify({"status": "OK", "app_id": APP_ID, "last_phien": predictor.last_phien_id})

if __name__ == '__main__':
    # 1. Khởi tạo và chạy luồng nền dự đoán (Daemon=True: tự động tắt khi luồng chính tắt)
    # Tần suất kiểm tra: 1 giây (có thể điều chỉnh)
    thread = threading.Thread(target=_run_predictor_loop, args=(1,), daemon=True)
    thread.start()

    # 2. Khởi chạy Flask API (sẽ block luồng chính)
    print(f"\n[{APP_ID}] Khởi động Flask API tại http://0.0.0.0:5000/predict")
    # Tắt use_reloader để tránh luồng nền bị khởi động 2 lần
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
