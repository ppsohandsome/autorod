## 1.目录介绍

args.py 中存放可供修改的参数

auto_rod.py 为主程序

autorod_check/restart/stop分别为检查/重启/停止

## 2.args.py

```
bootstrap_servers = '192.168.1.13:9092'
auto_rod_url = 'rtsp://admin:abcd1234@192.168.1.142:554/h264/ch1/main/av_stream'
is_show = False
auto_rod_send_topic='auto_rod'
camera_id='78'
```

分别为：

 kafka ip+端口

自动干rtsp地址

可修改为True，表示是否显示opencv画面（用于调试，正常运行是为False）

kafka topic名称

相机id号码

## 3.启停脚本使用

使用方式为

```
./autorod_xxx.sh
```

默认位置为，可通过vi三个脚本文件来修改路径

```
/home/nvidia/project/SVM/auto_rod.py
```

## 4.requirement

注意：不要一次性全部装上！！！杂乱的太多了

运行auto_rod.py，然后缺啥补啥，requirement只是为了以防你找不到合适的版本！！

