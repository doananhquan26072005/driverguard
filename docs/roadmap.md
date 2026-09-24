Mốc	Làm gì	Xong là thấy gì
M0	Khối 1, 2: đọc video, resize, CLAHE	Cửa sổ hiện video chạy được
M1	Khối 3, 6: MediaPipe, tính EAR, MAR, head pose	In ra EAR mỗi frame, vẽ landmark lên ảnh debug
M2	Khối 7: PERCLOS, microsleep, ngáp, gục đầu	Terminal in ra khi phát hiện ngủ gật
M3	Khối 4, 8: YOLO điện thoại, nhìn lệch	Phát hiện được mất tập trung
M4	Khối 9, 10, 11, 12: risk engine, CAN giả lập, cooldown	Ra mức L0–L3 đúng theo kịch bản
M5	Khối 14 + backend FastAPI	Sự kiện hiện trong database
M6	Dashboard React + HUD	Giao diện 3 vai trò, nhật ký sự kiện
M7	Script eval + benchmark FPS	Bảng precision/recall/FP mỗi giờ, bảng FPS