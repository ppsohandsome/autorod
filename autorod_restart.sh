#!/bin/bash

# 查找并获取jetsonDetect进程的PID
jetson_detect_pids=$(pidof python3.7  /home/nvidia/project/SVM/auto_rod.py)

# 检查进程是否存在
if [ -z "$jetson_detect_pids" ]; then
    echo "auto_rod.py not running"
else
    echo "auto_rod.py running in PIDs: $jetson_detect_pids, now kill them"
    # 杀死所有匹配的进程
    for pid in $jetson_detect_pids; do
        kill -9 $pid
    done
fi

# 重新启动进程
echo "auto_rod.py restarting..."
python3.7 -u /home/nvidia/project/SVM/auto_rod.py >> /home/nvidia/project/SVM/log/autoRod_$(date +\%Y-%m-%d).log 2>&1 &
echo "auto_rod.py has restarted"
