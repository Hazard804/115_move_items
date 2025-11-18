#!/usr/bin/env python3
"""
115网盘文件移动工具 - Docker版本
支持通过环境变量配置所有参数
"""

from pathlib import Path
from p115client import P115Client
from p115client.tool.iterdir import iter_files, iter_dirs
import time
import logging
from datetime import datetime
import re
import os
from logging.handlers import TimedRotatingFileHandler


# 全局变量
client = None
logger = None
LOG_DIR = "/app/logs"
DATA_DIR = "/app/data"
COOKIE_FILE = os.path.join(DATA_DIR, "115-cookies.txt")


def setup_logger(log_retention_days=7):
    """
    设置日志记录器，按天分割，自动清理旧日志
    
    参数:
        log_retention_days: 日志保留天数，默认7天
    """
    global logger
    
    # 创建日志目录
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    # 创建logger
    logger = logging.getLogger('move_items_docker')
    logger.setLevel(logging.INFO)
    
    # 清除已有的处理器
    logger.handlers.clear()
    
    # 文件处理器 - 按天分割
    log_file = os.path.join(LOG_DIR, 'move_items.log')
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=log_retention_days,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def format_file_size(size):
    """格式化文件大小显示"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 ** 2:
        return f"{size / 1024:.2f} KB"
    elif size < 1024 ** 3:
        return f"{size / (1024 ** 2):.2f} MB"
    else:
        return f"{size / (1024 ** 3):.2f} GB"


def parse_file_size(size_str):
    """
    解析文件大小字符串，转换为字节数
    
    参数:
        size_str: 文件大小字符串，如 "200MB", "1.5GB", "500KB", "100M"
    
    返回:
        int: 字节数，解析失败返回 None
    """
    size_str = size_str.strip().upper()
    
    # 定义单位转换
    units = {
        'B': 1,
        'KB': 1024,
        'K': 1024,
        'MB': 1024 ** 2,
        'M': 1024 ** 2,
        'GB': 1024 ** 3,
        'G': 1024 ** 3,
        'TB': 1024 ** 4,
        'T': 1024 ** 4,
    }
    
    # 使用正则表达式解析
    pattern = r'^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$'
    match = re.match(pattern, size_str)
    
    if not match:
        return None
    
    value = float(match.group(1))
    unit = match.group(2) or 'B'
    
    if unit not in units:
        return None
    
    return int(value * units[unit])


def find_directory_by_path(path, start_cid=0):
    """
    根据路径查找目录ID
    
    参数:
        path: 目录路径，格式如 "/folder1/folder2/folder3"
        start_cid: 起始目录ID，默认为 0（根目录）
    
    返回:
        int: 目录ID，如果找不到则返回 None
    """
    # 处理路径
    path = path.strip()
    
    # 如果是空路径或只有 /，返回根目录
    if not path or path == '/':
        return 0
    
    # 移除开头和结尾的斜杠
    path = path.strip('/')
    
    # 分割路径
    path_parts = [p for p in path.split('/') if p]
    
    if not path_parts:
        return start_cid
    
    current_cid = start_cid
    
    # 逐层查找
    for i, folder_name in enumerate(path_parts):
        logger.info(f"正在查找: {folder_name} (当前目录ID: {current_cid})")
        
        # 获取当前目录下的所有子目录
        found = False
        for dir_info in iter_dirs(client=client, cid=current_cid, max_workers=0):
            if dir_info.get('name') == folder_name:
                current_cid = dir_info.get('id')
                found = True
                logger.info(f"  ✓ 找到: {folder_name} (ID: {current_cid})")
                break
        
        if not found:
            logger.error(f"  ✗ 未找到目录: {folder_name}")
            logger.error(f"  提示: 在目录 {current_cid} 下找不到名为 '{folder_name}' 的子目录")
            return None
    
    logger.info(f"✓ 成功找到目标目录 ID: {current_cid}")
    return current_cid


def move_files(file_ids, target_pid=0):
    """
    移动文件或目录到指定目录
    
    参数:
        file_ids: 文件或目录ID
        target_pid: 目标目录ID，默认为 0（根目录）
    
    返回:
        dict: API 返回的结果
    """
    try:
        result = client.fs_move(file_ids, pid=target_pid)
        return result
    except Exception as e:
        logger.error(f"移动文件时发生错误: {e}")
        return {'state': False, 'error': str(e)}


def init_client_from_env():
    """
    从环境变量初始化115客户端
    
    返回:
        P115Client: 客户端对象，如果失败返回 None
    """
    global client
    
    logger.info("=" * 80)
    logger.info("115网盘客户端初始化 (Docker模式)")
    logger.info("=" * 80)
    
    # 从环境变量读取cookie
    cookie_env = os.environ.get('COOKIE', '').strip()
    
    if not cookie_env:
        # 尝试从文件读取
        if os.path.exists(COOKIE_FILE):
            logger.info(f"从文件读取Cookie: {COOKIE_FILE}")
            try:
                with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                    cookie_env = f.read().strip()
            except Exception as e:
                logger.error(f"读取Cookie文件失败: {e}")
                return None
    
    if not cookie_env:
        logger.error("错误: 未设置COOKIE环境变量，且未找到cookie文件")
        logger.error("请通过 -e COOKIE='your_cookie' 设置cookie")
        return None
    
    # 验证cookie
    try:
        logger.info("正在验证Cookie...")
        client = P115Client(cookie_env)
        
        # 测试连接 - 尝试获取用户信息（更快更可靠）
        try:
            logger.info("正在测试API连接...")
            # 使用更简单的API测试连接
            user_info = client.user_info()
            if user_info and user_info.get('state'):
                user_name = user_info.get('data', {}).get('user_name', '未知用户')
                logger.info(f"✓ Cookie验证成功！当前用户: {user_name}")
            else:
                logger.error("✗ Cookie验证失败: 无法获取用户信息")
                return None
        except Exception as e:
            logger.error(f"✗ 连接115 API失败: {e}")
            logger.error("可能原因:")
            logger.error("  1. 网络连接问题，无法访问 115.com")
            logger.error("  2. Cookie 已过期或格式错误")
            logger.error("  3. 被防火墙或代理拦截")
            return None
        
        # 保存cookie到文件（用于下次重启）
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            f.write(cookie_env)
        logger.info(f"✓ Cookie已保存到 {COOKIE_FILE}")
        
        return client
        
    except Exception as e:
        logger.error(f"✗ Cookie验证失败: {e}")
        return None


def auto_move_files_task(source_path, target_path, interval_minutes, min_size_bytes):
    """
    自动移动文件任务
    
    参数:
        source_path: 源目录路径
        target_path: 目标目录路径
        interval_minutes: 检查间隔（分钟）
        min_size_bytes: 最小文件大小（字节）
    """
    logger.info("=" * 80)
    logger.info("自动移动文件任务启动")
    logger.info(f"源目录路径: {source_path}")
    logger.info(f"目标目录路径: {target_path}")
    logger.info(f"检查间隔: {interval_minutes} 分钟")
    logger.info(f"最小文件大小: {format_file_size(min_size_bytes)}")
    logger.info("=" * 80)
    
    # 解析目录路径
    logger.info("正在解析源目录路径...")
    source_cid = find_directory_by_path(source_path)
    
    if source_cid is None:
        logger.error(f"无法找到源目录: {source_path}")
        return False
    
    logger.info(f"源目录 ID: {source_cid}")
    
    logger.info("正在解析目标目录路径...")
    target_cid = find_directory_by_path(target_path)
    
    if target_cid is None:
        logger.error(f"无法找到目标目录: {target_path}")
        return False
    
    logger.info(f"目标目录 ID: {target_cid}")
    
    # 开始循环检查
    run_count = 0
    interval_seconds = interval_minutes * 60
    
    try:
        while True:
            run_count += 1
            logger.info("\n" + "=" * 80)
            logger.info(f"第 {run_count} 次检查开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 80)
            
            try:
                # 获取源目录中的文件
                logger.info(f"正在扫描源目录 (ID: {source_cid})...")
                files_to_move = []
                total_files = 0
                
                for file_info in iter_files(
                    client=client,
                    cid=source_cid,
                    cur=0,  # 遍历子目录树
                    page_size=1000
                ):
                    total_files += 1
                    file_size = file_info.get('size', 0)
                    file_name = file_info.get('name', '')
                    file_id = file_info.get('id', '')
                    file_path = file_info.get('path', '')
                    
                    # 如果path为空，使用name作为显示
                    display_path = file_path if file_path else file_name
                    
                    # 检查文件大小
                    if file_size >= min_size_bytes:
                        files_to_move.append({
                            'id': file_id,
                            'name': file_name,
                            'size': file_size,
                            'path': file_path,
                            'display_path': display_path
                        })
                        logger.info(f"  → 符合条件: {display_path} ({format_file_size(file_size)})")
                
                logger.info(f"\n扫描完成: 共 {total_files} 个文件，{len(files_to_move)} 个符合移动条件")
                
                # 移动文件
                if files_to_move:
                    logger.info(f"\n开始移动 {len(files_to_move)} 个文件到目标目录 (ID: {target_cid})...")
                    
                    success_count = 0
                    fail_count = 0
                    
                    for file_info in files_to_move:
                        try:
                            display_info = file_info.get('display_path') or file_info.get('name', '未知文件')
                            logger.info(f"  移动: {display_info} (ID: {file_info['id']})")
                            result = move_files(file_info['id'], target_cid)
                            
                            if result.get('state'):
                                success_count += 1
                                logger.info(f"    ✓ 成功")
                            else:
                                fail_count += 1
                                error_msg = result.get('error', result.get('error_msg', '未知错误'))
                                logger.warning(f"    ✗ 失败: {error_msg}")
                            
                            # 添加小延迟，避免请求过快
                            time.sleep(0.5)
                            
                        except Exception as e:
                            fail_count += 1
                            logger.error(f"    ✗ 异常: {e}")
                    
                    logger.info(f"\n移动结果: 成功 {success_count} 个，失败 {fail_count} 个")
                else:
                    logger.info("没有符合条件的文件需要移动")
                
            except Exception as e:
                logger.error(f"检查过程中发生错误: {e}")
            
            # 等待下一次检查
            next_check_time = datetime.now().timestamp() + interval_seconds
            next_check_str = datetime.fromtimestamp(next_check_time).strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"\n下次检查时间: {next_check_str}")
            logger.info(f"等待 {interval_minutes} 分钟...")
            
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        logger.info("\n\n收到中断信号，任务停止")
        logger.info(f"总共执行了 {run_count} 次检查")
        return True
    except Exception as e:
        logger.error(f"任务异常终止: {e}")
        return False


def main():
    """主函数 - Docker版本"""
    
    # 读取环境变量
    source_path = os.environ.get('SOURCE_PATH', '').strip()
    target_path = os.environ.get('TARGET_PATH', '').strip()
    check_interval = os.environ.get('CHECK_INTERVAL', '5').strip()
    min_file_size = os.environ.get('MIN_FILE_SIZE', '200MB').strip()
    log_retention_days = os.environ.get('LOG_RETENTION_DAYS', '7').strip()
    mode = os.environ.get('MODE', 'auto').strip().lower()
    
    # 设置日志
    try:
        log_days = int(log_retention_days)
        if log_days < 1:
            log_days = 7
    except:
        log_days = 7
    
    setup_logger(log_days)
    
    logger.info("=" * 80)
    logger.info("115网盘文件移动工具 - Docker版本")
    logger.info("=" * 80)
    logger.info(f"日志保留天数: {log_days} 天")
    logger.info(f"运行模式: {mode}")
    
    # 验证环境变量
    if mode == 'auto':
        if not source_path:
            logger.error("错误: 未设置 SOURCE_PATH 环境变量")
            logger.error("示例: -e SOURCE_PATH='/待处理/下载'")
            return 1
        
        if not target_path:
            logger.error("错误: 未设置 TARGET_PATH 环境变量")
            logger.error("示例: -e TARGET_PATH='/已完成/视频'")
            return 1
        
        # 解析检查间隔
        try:
            interval_minutes = int(check_interval)
            if interval_minutes < 2:
                logger.warning(f"检查间隔 {interval_minutes} 分钟过短，使用最小值 2 分钟")
                interval_minutes = 2
        except:
            logger.error(f"错误: CHECK_INTERVAL 值无效: {check_interval}")
            return 1
        
        # 解析文件大小
        min_size_bytes = parse_file_size(min_file_size)
        if min_size_bytes is None:
            logger.error(f"错误: MIN_FILE_SIZE 格式无效: {min_file_size}")
            logger.error("支持格式: 200MB, 1.5GB, 500KB 等")
            return 1
        
        logger.info(f"源目录: {source_path}")
        logger.info(f"目标目录: {target_path}")
        logger.info(f"检查间隔: {interval_minutes} 分钟")
        logger.info(f"最小文件大小: {format_file_size(min_size_bytes)}")
    
    # 初始化客户端
    if not init_client_from_env():
        logger.error("客户端初始化失败，程序退出")
        return 1
    
    # 运行自动模式
    if mode == 'auto':
        auto_move_files_task(source_path, target_path, interval_minutes, min_size_bytes)
    else:
        logger.error(f"错误: 不支持的模式: {mode}")
        logger.error("当前Docker版本仅支持 auto 模式")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
