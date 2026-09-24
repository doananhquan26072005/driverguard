Mốc	Làm gì	Xong là thấy gì	Trạng thái
M0	Khối 1, 2: đọc video, resize, CLAHE	Cửa sổ hiện video chạy được	Xong (abca755)
M1	Khối 3, 6: MediaPipe, tính EAR, MAR, head pose	In ra EAR mỗi frame, vẽ landmark lên ảnh debug	Xong (e1a58d8)
M2	Khối 7: PERCLOS, microsleep, ngáp, gục đầu (+ khối 5 Eye-state CNN)	Terminal in ra khi phát hiện ngủ gật	Xong (4077bd5); sửa an toàn: nhắm mắt rồi gục đầu vẫn đếm tiếp closed_duration → L3; mốc pitch/yaw chỉ học lúc mắt mở (không trôi khi gật nhiều); giảm báo sai: không tính thời gian nhắm mắt lúc ngáp / đang nói (+1,5 s) vào closed_duration, MAR ngáp 0,45/0,34 (YawDD: L3 ở clip Yawning 13 → 1, Talking 20 → 4)
M3	Khối 4, 8: YOLO điện thoại, nhìn lệch	Phát hiện được mất tập trung	Xong (6dd7f99); sửa an toàn: điện thoại che mặt vẫn tính (nhớ khung mặt 3 s), thêm no_face_duration; hiệu chỉnh mốc nhìn đường 5 s đầu chuyến (camera lắp lệch > 30°)
M4	Khối 9, 10, 11, 12: risk engine, CAN giả lập, cooldown	Ra mức L0–L3 đúng theo kịch bản	Xong; sửa an toàn: mất mặt ≥ 3 s khi chạy → L2 (no_face), lý do mới cùng mức → alert mới, cooldown theo (mức, lý do)
M5	Khối 14 + backend FastAPI	Sự kiện hiện trong database	Xong
M6	Dashboard React + HUD	Giao diện 3 vai trò, nhật ký sự kiện	Xong
M7	Script eval + benchmark FPS	Bảng precision/recall/FP mỗi giờ, bảng FPS	Công cụ xong, bảng FPS đo trên video YawDD có mặt thật (146 FPS, Mac ARM); tools/dataset.py đo từng ảnh trên dataset Kaggle; chờ video có nhãn thời gian cho precision/recall