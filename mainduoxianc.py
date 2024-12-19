import json
import threading
import time
import yaml
import cv2
import joblib
import numpy as np
from kafka import KafkaConsumer, KafkaProducer
import base64
from PIL import Image
from io import BytesIO
import args

# 创建一个队列来存储从Kafka获取的消息
message_queue = []

def base64_to_numpy(base64_image):
    decoded_image_data = base64.b64decode(base64_image)
    image_array = np.frombuffer(decoded_image_data, dtype=np.uint8)
    image = Image.open(BytesIO(image_array))
    # image = image.convert('BGR')  # 将图像转换为RGB通道顺序
    # 将RGB图像转换为BGR图像
    image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    image_np = np.array(image)
    return image_np

# 根据左下角坐标，宽度，高度截图
def crop_image_array(image_array, left, bottom, width, height):
    right = left + width
    top = bottom + height
    # 裁剪图像
    cropped_image_array = image_array[bottom:top, left:right, :]
    # 返回裁剪后的图像数组
    return cropped_image_array


def extractFeaturesFromImage(img):
    img = cv2.resize(img, (30, 30), interpolation=cv2.INTER_CUBIC)
    img = img.flatten()
    img = img / np.mean(img)
    return img


def draw_old(image, x, y, w, h, clf_collector, clf_switch, label):
    # 获取原图坐标
    # image_height, image_width, _ = image.shape
    # box_x, box_y, box_width, box_height = denormalization(image_width, image_height, x, y, w, h)
    # 切割图像
    cropped_array = crop_image_array(image, x, y, w, h)
    img = extractFeaturesFromImage(cropped_array)
    imageFeature = img.reshape(1, -1)
    text = ""
    if label == "collector":  # 受电弓
        #result = clf_collector.predict(imageFeature)[0]
        threshold = 1.2  # 受电弓的阈值
        if w / h > threshold:
            result = 0
        else:
            result = 1
    elif label == "switch":  # 隔离开关
        result = clf_switch.predict(imageFeature)[0]
    else:
        return image, text
    text = "ON" if int(result) == 1 else "OFF"
    # if label in ['collector', 'switch']:
    #cropped_image = Image.fromarray(cropped_array)
    #cropped_image.save('/home/nvidia/project/SVM/output_image/' + str(time.time())+"_"+text + '.jpg')
    # 在图像上绘制文本
    cv2.putText(image, text, (x + h, y + 20), cv2.FONT_HERSHEY_SIMPLEX,
                2.0,
                (0, 255, 0), 2, cv2.LINE_AA)
    return image, text

def draw(image, x, y, w, h, label):
    text = ""
    # 根据标签选择不同的阈值
    if label == "collector":
        threshold = 1.2  # 受电弓的阈值
    elif label == "switch":
        threshold = 1.2  # 隔离开关的阈值
    else:
        return image, text

    # 判断宽高比是否大于阈值
    if w / h > threshold:
        text = "OFF"
    else:
        text = "ON"
    # 在图像上绘制文本
    cv2.putText(image, text, (x + h, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
    return image, text

def process_message(message,producer):
    msg = message.value.decode('utf-8')
    msg = msg.replace('\n', '').replace('\r', '')
    msg = json.loads(msg)
    camera_id = msg['camera-id']
    timestemp = msg['timestemp']
    object = msg['object:']
    image = msg['image']
    image_np = base64_to_numpy(image)
    new_object = []
    for obj in object:
        mid = obj.split('|')
        label = mid[-1]
        x, y, w, h = int(float(mid[0])), int(float(mid[1])), int(float(mid[2])), int(float(mid[3]))
        if label in ['collector', 'switch']:
            img, text = draw_old(image_np, x, y, w, h, clf_collector, clf_switch, label)
            image_np = img
            obj = obj + "|" + text
        new_object.append(obj)
    _, buffer = cv2.imencode('.jpg', image_np)
    base64_image = base64.b64encode(buffer).decode('utf-8')
    message = {"image": base64_image, "camera-id": camera_id, "object": new_object, "timestemp": timestemp}
    print(message["camera-id"],message["timestemp"])
    future = producer.send(topic_send, value=json.dumps(message).encode('utf-8'))
    producer.flush()
    if future.exception is not None:
        print("kafka send fail:", future.exception)
    else:
        print("send success")

def consume_messages_and_store_in_queue(consumer):
    for msg in consumer:
        message_queue.append(msg)

def process_messages_from_queue(producer):
    while True:
        if message_queue:
            msg = message_queue.pop(0)
            process_message(msg,producer)



if __name__ == '__main__':
    # 省略配置和初始化...
    clf_collector = joblib.load(args.clf_collector)
    clf_switch = joblib.load(args.clf_switch)
    bootstrap_servers = args.bootstrap_servers
    topic_accept = args.topic_accept
    topic_send = args.topic_send
    consumer = KafkaConsumer(
        topic_accept,
        bootstrap_servers=[bootstrap_servers],
        auto_offset_reset='latest',
        fetch_max_bytes=104857600
    )
    producer = KafkaProducer(bootstrap_servers=bootstrap_servers, max_request_size=1048576000)
    print("kafka server: {},accept topic: {},send topic: {}".format(bootstrap_servers, topic_accept, topic_send))

    # 创建一个单独的线程用于从Kafka获取消息并存储在队列中
    kafka_consumer_thread = threading.Thread(target=consume_messages_and_store_in_queue, args=(consumer,))
    kafka_consumer_thread.start()

    # 创建多个线程用于处理消息
    num_processing_threads = 4
    processing_threads = []

    for _ in range(num_processing_threads):
        processing_thread = threading.Thread(target=process_messages_from_queue, args=(producer,))
        processing_threads.append(processing_thread)
        processing_thread.start()

    kafka_consumer_thread.join()
    for processing_thread in processing_threads:
        processing_thread.join()

    consumer.close()
    producer.close()
