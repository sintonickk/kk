import os
import time
import queue
import threading
import cv2
import argparse
from frame_analyzer import frame_analyzer
from alarm_handler import alarm_handler
from config_manager import load_config
from logger_setup import get_logger

def get_all_image_files(folder):
    """递归获取文件夹下所有图片文件"""
    extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    image_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(extensions):
                image_files.append(os.path.join(root, file))
    return image_files

def process_images(folder, frame_queue, stop_event):
    """处理图片文件夹"""
    logger = get_logger(__name__)
    
    # 获取所有图片文件
    image_files = get_all_image_files(folder)
    if not image_files:
        logger.error(f"在 {folder} 及其子文件夹中未找到图片文件")
        stop_event.set()
        return
        
    logger.info(f"找到 {len(image_files)} 张图片，开始处理...")
    
    for image_path in image_files:
        if stop_event.is_set():
            break
            
        try:
            frame = cv2.imread(image_path)
            if frame is not None:
                # 如果队列已满，等待直到可以放入
                while not stop_event.is_set():
                    try:
                        frame_queue.put(
                            frame,  # 只传递帧数据，不传递元组
                            timeout=1.0  # 1秒超时，然后检查是否应该停止
                        )
                        break  # 成功放入队列，跳出循环
                    except queue.Full:
                        # 队列已满，等待后重试
                        logger.debug("队列已满，等待...")
                        continue
            else:
                logger.warning(f"无法读取图片: {image_path}")
        except Exception as e:
            logger.error(f"处理图片 {image_path} 时出错: {str(e)}")
    
    logger.info("所有图片处理完成")
    # stop_event.set()

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='从文件夹读取图片进行处理')
    parser.add_argument('folder', help='包含图片的文件夹路径')
    args = parser.parse_args()
    
    logger = get_logger(__name__)
    
    # 检查文件夹是否存在
    if not os.path.isdir(args.folder):
        logger.error(f"文件夹不存在: {args.folder}")
        return
    
    # 初始化队列
    frame_queue = queue.Queue(maxsize=100)
    alarm_queue = queue.Queue(maxsize=20000)
    stop_event = threading.Event()
    
    # 启动图片处理线程
    process_thread = threading.Thread(
        target=process_images,
        args=(args.folder, frame_queue, stop_event),
        daemon=True
    )
    
    # 启动帧分析线程
    analyzer_thread = threading.Thread(
        target=frame_analyzer,
        args=(frame_queue, alarm_queue, stop_event),
        daemon=True
    )
    
    # 启动报警处理线程
    alarm_thread = threading.Thread(
        target=alarm_handler,
        args=(alarm_queue, stop_event, queue.Queue()),
        daemon=True
    )
    
    # 启动所有线程
    process_thread.start()
    analyzer_thread.start()
    alarm_thread.start()
    
    try:
        # 主线程等待处理完成或收到中断信号
        while not stop_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("\n正在停止...")
        stop_event.set()
    
    # 等待线程结束
    process_thread.join()
    analyzer_thread.join()
    alarm_thread.join()
    logger.info("处理完成")

if __name__ == "__main__":
    main()
