import base64
import time
import json
import numpy as np
import cv2
from kafka import KafkaProducer
from datetime import datetime

import args

# 打开视频文件（也可以从摄像头读取）
url = args.auto_rod_url
cap = cv2.VideoCapture(url)
format = "%Y-%m-%d|%H:%M:%S"
frame_count = 0

lower_red1 = np.array([160, 50, 0])
upper_red1 = np.array([179, 255, 255])
lower_red2 = np.array([0, 50, 0])
upper_red2 = np.array([10, 255, 255])
producer = KafkaProducer(bootstrap_servers=args.bootstrap_servers, max_request_size=1048576000)
# producer = KafkaProducer(bootstrap_servers=args.bootstrap_servers, max_request_size=1048576000)
while (cap.isOpened()):
    # 读帧
    ret, frame = cap.read()
    #检测不到图片后输出
    if not ret:
        print("流关闭")
        break
    frame_count += 1
    #每40张图片选取一张
    if frame_count % 40 == 0:
        frame_count = 0
        #时间
        t = datetime.now().strftime(format)
        start = time.time()

        # 红色提取
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = mask1 + mask2

        #   中值滤波
        red_mask = cv2.medianBlur(red_mask, 5)
        # 存图用于展示
        aa = red_mask.copy()

        #不重要部分用黑色覆盖
        cv2.rectangle(red_mask, (0, int(red_mask.shape[0] * 11 / 20)),
                      (red_mask.shape[1] - 1, (red_mask.shape[0] - 1)),
                      (0, 0, 0), -1)
        cv2.rectangle(red_mask, (0, 0), (200, red_mask.shape[0] - 1), (0, 0, 0), -1)

        #  查找图片中白色轮廓
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # 去除小面积的轮廓
        filtered_contours = [contour for contour in contours if
                             cv2.contourArea(contour) >= 1]
        dilated = cv2.drawContours(red_mask, filtered_contours, -1, (0, 0, 255), 3)
        # 初始化最大高度和对应的区域索引
        max_height = 0
        max_height_index = -1
        # 遍历所有区域
        for index, contour in enumerate(filtered_contours):
            # 计算区域的边界框
            x, y, w, h = cv2.boundingRect(contour)
            # 寻找图片中高度最高的轮廓
            if h > max_height:
                max_height = h
                max_height_index = index

        text = "close"

        # 防止没有提取到任何区域
        if (max_height_index != -1):
            max_contour = filtered_contours[max_height_index]
            # 矩形框框出目标区域
            x1 = min(i[0][0] for i in max_contour)
            x2 = max(i[0][0] for i in max_contour)
            y1 = min(i[0][1] for i in max_contour)
            y2 = max(i[0][1] for i in max_contour)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 10)

            # 在图像上打印文本          y2 - y1 > frame.shape[0] / 5 and
            text = "open" if ((y2 - y1) / (x2 - x1) > 1) else "close"

            img_with_text = cv2.putText(frame, text, (x1, y1 - 30), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 4,
                                        cv2.LINE_AA)
            # print(text, t)
            _, buffer = cv2.imencode('.jpg', img_with_text)
            base64_image = base64.b64encode(buffer).decode('utf-8')
            producer.send(args.auto_rod_send_topic,
                          value=json.dumps({"image": base64_image,
                                            "timestemp": t,
                                            "camera-id": args.camera_id,
                                            "result": text,
                                            "left-x": str(x1),
                                            "left-y": str(y1),
                                            "right-x": str(x2),
                                            "right-y": str(y2)
                                            }).encode('utf-8'))
            print(t, args.camera_id, text, x1, y1, x2, y2)
            # producer.flush()
        if args.is_show:
            frame = cv2.resize(frame, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_LINEAR)

            aa = cv2.resize(aa, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_LINEAR)
            cv2.imshow('frame', frame)
            cv2.imshow('a2', red_mask)
            cv2.imshow('a1', aa)

            cv2.imwrite("frame.jpg", frame)

        #        if cv2.waitKey(1) & 0xFF == ord('q'):
        #            break
        print(time.time() - start)
cap.release()
cv2.destroyAllWindows()
