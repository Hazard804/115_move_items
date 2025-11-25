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
from functools import wraps
import signal
from contextlib import contextmanager
import requests


# 全局变量
client = None
logger = None
LOG_DIR = "/app/logs"
DATA_DIR = "/app/data"
COOKIE_FILE = os.path.join(DATA_DIR, "115-cookies.txt")

# 默认超时和重试配置
DEFAULT_API_TIMEOUT = 120  # 默认120秒超时
DEFAULT_API_RETRY_TIMES = 3  # 默认重试3次
BARK_URL = None  # Bark通知URL
CALLBACK_URL = None  # 文件移动后的回调URL


class TimeoutError(Exception):
    """超时异常"""
    pass


@contextmanager
def timeout_handler(seconds):
    """
    超时上下文管理器（仅限Unix/Linux系统）
    
    参数:
        seconds: 超时秒数
    """
    def timeout_signal_handler(signum, frame):
        raise TimeoutError(f"操作超时 ({seconds}秒)")
    
    # Windows系统不支持signal.alarm，直接返回
    if os.name == 'nt':
        yield
        return
    
    # 设置信号处理器
    old_handler = signal.signal(signal.SIGALRM, timeout_signal_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def with_retry_and_timeout(max_retries=None, timeout_seconds=None, operation_name="操作"):
    """
    为函数添加超时和重试机制的装饰器
    
    参数:
        max_retries: 最大重试次数，None表示使用全局配置
        timeout_seconds: 超时秒数，None表示使用全局配置
        operation_name: 操作名称，用于日志输出
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取全局配置
            retries = max_retries if max_retries is not None else DEFAULT_API_RETRY_TIMES
            timeout = timeout_seconds if timeout_seconds is not None else DEFAULT_API_TIMEOUT
            
            last_error = None
            
            for attempt in range(retries):
                try:
                    # Windows系统直接执行，不使用信号超时
                    if os.name == 'nt':
                        return func(*args, **kwargs)
                    
                    # Unix/Linux系统使用信号超时
                    with timeout_handler(timeout):
                        return func(*args, **kwargs)
                        
                except TimeoutError as e:
                    last_error = e
                    if attempt < retries - 1:
                        wait_time = (attempt + 1) * 2  # 递增等待时间
                        logger.warning(f"⚠️  {operation_name}超时 (尝试 {attempt + 1}/{retries})，{wait_time}秒后重试...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"❌ {operation_name}在 {retries} 次尝试后仍然超时")
                        logger.error("💡 建议: 如果持续超时，可能是网络问题或Cookie已失效")
                        logger.error("   1. 检查网络连接和代理设置")
                        logger.error("   2. 尝试重新获取Cookie并更新配置")
                        send_bark_notification(
                            f"115自动移动失败: {operation_name}",
                            f"操作超时({retries}次重试后仍失败)，请检查网络或Cookie",
                            "timeSensitive"
                        )
                        
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    
                    # 检查是否是认证错误（不重试）
                    if 'login' in error_str or 'auth' in error_str or 'cookie' in error_str:
                        logger.error(f"❌ {operation_name}失败: 认证错误，不进行重试")
                        raise
                    
                    # 其他错误进行重试
                    if attempt < retries - 1:
                        wait_time = (attempt + 1) * 2
                        logger.warning(f"⚠️  {operation_name}失败 (尝试 {attempt + 1}/{retries}): {e}")
                        logger.warning(f"   {wait_time}秒后重试...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"❌ {operation_name}在 {retries} 次尝试后仍然失败: {e}")
                        logger.error("💡 建议: 如果持续失败，可能是Cookie已失效")
                        logger.error("   请尝试重新获取Cookie并更新配置")
                        send_bark_notification(
                            f"115自动移动失败: {operation_name}",
                            f"操作失败({retries}次重试后): {str(e)[:100]}",
                            "timeSensitive"
                        )
            
            # 所有重试都失败
            raise last_error
        
        return wrapper
    return decorator


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


def send_bark_notification(title, content, level="passive"):
    """
    发送Bark通知
    
    参数:
        title: 通知标题
        content: 通知内容
        level: 通知级别 (active/timeSensitive/passive)
    """
    if not BARK_URL:
        return
    
    try:
        # 组合完整的Bark URL
        url = f"{BARK_URL.rstrip('/')}/{requests.utils.quote(title)}/{requests.utils.quote(content)}?level={level}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            logger.info(f"📱 Bark通知已发送: {title}")
        else:
            logger.warning(f"⚠️  Bark通知发送失败: HTTP {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠️  Bark通知发送异常: {e}")


def trigger_callback():
    """
    触发回调URL，用于通知外部系统文件已移动
    """
    if not CALLBACK_URL:
        return
    
    try:
        logger.info(f"🔔 正在触发回调: {CALLBACK_URL}")
        response = requests.get(CALLBACK_URL, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ 回调成功: HTTP {response.status_code}")
        else:
            logger.warning(f"⚠️  回调返回非200: HTTP {response.status_code}")
    except requests.exceptions.Timeout:
        logger.warning(f"⚠️  回调超时: {CALLBACK_URL}")
    except Exception as e:
        logger.warning(f"⚠️  回调失败: {e}")


def parse_path_mappings(mappings_str):
    """
    解析路径映射配置
    
    参数:
        mappings_str: 映射字符串，格式: "源路径1->目标路径1,源路径2->目标路径2"
    
    返回:
        list: [(源路径, 目标路径), ...] 或空列表
    """
    if not mappings_str or not mappings_str.strip():
        return []
    
    mappings = []
    pairs = mappings_str.split(',')
    
    for idx, pair in enumerate(pairs, 1):
        pair = pair.strip()
        if not pair:
            continue
            
        if '->' not in pair:
            logger.warning(f"⚠️  映射 {idx}: 格式错误（缺少 '->'）: {pair}")
            logger.warning(f"    正确格式: /源路径->/目标路径")
            continue
        
        parts = pair.split('->', 1)
        if len(parts) != 2:
            logger.warning(f"⚠️  映射 {idx}: 格式错误: {pair}")
            continue
        
        source = parts[0].strip()
        target = parts[1].strip()
        
        if not source or not target:
            logger.warning(f"⚠️  映射 {idx}: 路径不能为空: {pair}")
            continue
        
        if not source.startswith('/'):
            logger.warning(f"⚠️  映射 {idx}: 源路径必须以 '/' 开头: {source}")
            logger.warning(f"    已自动修正为: /{source}")
            source = '/' + source
        
        if not target.startswith('/'):
            logger.warning(f"⚠️  映射 {idx}: 目标路径必须以 '/' 开头: {target}")
            logger.warning(f"    已自动修正为: /{target}")
            target = '/' + target
        
        mappings.append((source, target))
        logger.info(f"✓ 映射 {idx}: {source} -> {target}")
    
    return mappings


def parse_exclude_extensions(extensions_str):
    """
    解析排除的文件后缀
    
    参数:
        extensions_str: 后缀字符串，格式: ".txt,.tmp,.log" 或 "txt,tmp,log"
    
    返回:
        set: 后缀集合（统一小写，包含点号）
    """
    if not extensions_str or not extensions_str.strip():
        return set()
    
    extensions = set()
    parts = extensions_str.split(',')
    
    for part in parts:
        ext = part.strip().lower()
        if not ext:
            continue
        
        # 确保后缀以点开头
        if not ext.startswith('.'):
            ext = '.' + ext
        
        extensions.add(ext)
    
    if extensions:
        logger.info(f"📋 已配置排除后缀: {', '.join(sorted(extensions))}")
    
    return extensions


def should_exclude_file(filename, exclude_extensions):
    """
    判断文件是否应该被排除
    
    参数:
        filename: 文件名
        exclude_extensions: 排除的后缀集合
    
    返回:
        bool: True表示应该排除，False表示不排除
    """
    if not exclude_extensions:
        return False
    
    # 获取文件后缀（小写）
    file_ext = os.path.splitext(filename)[1].lower()
    
    return file_ext in exclude_extensions


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
    根据路径查找目录ID（带超时和重试）
    
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
        current_path = '/' + '/'.join(path_parts[:i+1])
        logger.info(f"  🔍 查找: {current_path}")
        
        # 获取当前目录下的所有子目录（带超时和重试）
        found = False
        try:
            @with_retry_and_timeout(operation_name=f"扫描目录 {current_path}")
            def scan_subdirs():
                for dir_info in iter_dirs(client=client, cid=current_cid, max_workers=0):
                    if dir_info.get('name') == folder_name:
                        return dir_info.get('id')
                return None
            
            result_cid = scan_subdirs()
            if result_cid:
                current_cid = result_cid
                found = True
                logger.info(f"     ✓ 找到 (ID: {current_cid})")
                
        except Exception as e:
            logger.error(f"     ✗ 查询目录时出错: {e}")
            return None
        
        if not found:
            logger.error(f"     ✗ 未找到目录: {folder_name}")
            logger.error(f"     提示: 请检查路径是否正确（区分大小写）")
            return None
    
    return current_cid


def check_cookie_valid():
    """
    检查 Cookie 是否仍然有效
    
    返回:
        bool: True 表示有效，False 表示失效
    """
    try:
        user_info = client.user_info()
        if user_info and user_info.get('state'):
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"检查 Cookie 状态时出错: {e}")
        return False


def move_files(file_ids, target_pid=0):
    """
    移动文件或目录到指定目录（带重试机制）
    
    参数:
        file_ids: 文件或目录ID
        target_pid: 目标目录ID，默认为 0（根目录）
    
    返回:
        dict: API 返回的结果
    """
    @with_retry_and_timeout(operation_name="移动文件")
    def do_move():
        result = client.fs_move(file_ids, pid=target_pid)
        
        # 检查是否因为 Cookie 失效导致的错误
        if not result.get('state'):
            error_msg = result.get('error', result.get('error_msg', ''))
            # 常见的认证失败错误码或消息
            if 'login' in error_msg.lower() or 'auth' in error_msg.lower() or result.get('errno') == 99:
                logger.error("=" * 80)
                logger.error("❌ 检测到 Cookie 可能已失效！")
                logger.error("=" * 80)
                logger.error("")
                logger.error("请执行以下步骤更新 Cookie：")
                logger.error("  1. 访问 https://115.com 重新登录")
                logger.error("  2. 按 F12 打开开发者工具获取新的 Cookie")
                logger.error("  3. 更新 docker-compose.yml 中的 COOKIE 环境变量")
                logger.error("  4. 重启容器: docker-compose restart")
                logger.error("")
                logger.error("=" * 80)
                # 抛出异常以便上层识别为认证错误
                raise Exception(f"Cookie失效: {error_msg}")
        
        return result
    
    try:
        return do_move()
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
    logger.info("🔐 115网盘客户端初始化")
    logger.info("=" * 80)
    
    # 从环境变量读取cookie
    cookie_env = os.environ.get('COOKIE', '').strip()
    cookie_source = None
    
    if cookie_env:
        logger.info("📝 使用环境变量中的 Cookie")
        cookie_source = "环境变量"
    else:
        # 尝试从文件读取
        if os.path.exists(COOKIE_FILE):
            logger.info(f"📂 从持久化文件读取 Cookie: {COOKIE_FILE}")
            try:
                with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                    cookie_env = f.read().strip()
                logger.info("✓ Cookie 读取成功")
                cookie_source = "持久化文件"
            except Exception as e:
                logger.error(f"✗ 读取Cookie文件失败: {e}")
                return None
    
    if not cookie_env:
        logger.error("=" * 80)
        logger.error("❌ 错误: 未设置 COOKIE 环境变量")
        logger.error("=" * 80)
        logger.error("")
        logger.error("请通过以下方式设置 Cookie:")
        logger.error("  docker run -e COOKIE='你的Cookie' ...")
        logger.error("")
        logger.error("如何获取 Cookie:")
        logger.error("  1. 访问 https://115.com 并登录")
        logger.error("  2. 按 F12 打开开发者工具")
        logger.error("  3. 切换到 Network 标签")
        logger.error("  4. 刷新页面，选择任意请求")
        logger.error("  5. 在请求头中找到 Cookie 字段并复制")
        logger.error("")
        return None
    
    # 验证cookie
    try:
        logger.info("🔄 正在验证Cookie...")
        client = P115Client(cookie_env)
        
        # 测试连接 - 尝试获取用户信息（更快更可靠）
        try:
            logger.info("🌐 正在测试API连接...")
            # 使用更简单的API测试连接
            user_info = client.user_info()
            if user_info and user_info.get('state'):
                user_name = user_info.get('data', {}).get('user_name', '未知用户')
                logger.info("=" * 80)
                logger.info(f"✅ Cookie验证成功！")
                logger.info(f"👤 当前用户: {user_name}")
                logger.info("=" * 80)
            else:
                logger.error("=" * 80)
                logger.error("❌ Cookie验证失败: 无法获取用户信息")
                logger.error("=" * 80)
                logger.error("")
                logger.error("可能原因:")
                logger.error("  1. Cookie 格式错误")
                logger.error("  2. Cookie 已过期（需要重新获取）")
                logger.error("  3. 115账号异常")
                logger.error("")
                return None
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ 连接115 API失败: {e}")
            logger.error("=" * 80)
            logger.error("")
            logger.error("可能原因:")
            logger.error("  1. 网络连接问题，无法访问 115.com")
            logger.error("  2. Cookie 已过期或格式错误")
            logger.error("  3. 被防火墙或代理拦截")
            logger.error("")
            logger.error("解决方案:")
            logger.error("  1. 检查网络连接")
            logger.error("  2. 如果使用代理，添加: network_mode: host")
            logger.error("  3. 重新获取 Cookie")
            logger.error("")
            return None
        
        # 保存cookie到文件（用于下次重启）
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            
            # 检查是否需要更新文件
            need_update = True
            if os.path.exists(COOKIE_FILE):
                with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                    old_cookie = f.read().strip()
                if old_cookie == cookie_env:
                    need_update = False
            
            if need_update:
                with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
                    f.write(cookie_env)
                if cookie_source == "环境变量":
                    logger.info(f"💾 Cookie已更新并保存到 {COOKIE_FILE}")
                    logger.info("   （环境变量中的新 Cookie 已覆盖旧文件）")
                else:
                    logger.info(f"💾 Cookie已保存到 {COOKIE_FILE}")
            else:
                logger.info(f"💾 Cookie文件无需更新")
        except Exception as e:
            logger.warning(f"⚠️  保存Cookie文件失败（不影响运行）: {e}")
        
        return client
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ 初始化客户端失败: {e}")
        logger.error("=" * 80)
        return None


def auto_move_files_task(path_mappings, interval_minutes, min_size_bytes, exclude_extensions):
    """
    自动移动文件任务（支持多组路径映射）
    
    参数:
        path_mappings: 路径映射列表 [(源路径, 目标路径), ...]
        interval_minutes: 检查间隔（分钟）
        min_size_bytes: 最小文件大小（字节）
        exclude_extensions: 排除的文件后缀集合
    """
    logger.info("=" * 80)
    logger.info("🚀 自动移动文件任务启动")
    logger.info("=" * 80)
    logger.info(f"📊 配置信息:")
    logger.info(f"   ├─ 映射数量: {len(path_mappings)} 组")
    logger.info(f"   ├─ 检查间隔: {interval_minutes} 分钟")
    logger.info(f"   ├─ 最小文件: {format_file_size(min_size_bytes)}")
    if exclude_extensions:
        logger.info(f"   └─ 排除后缀: {', '.join(sorted(exclude_extensions))}")
    else:
        logger.info(f"   └─ 排除后缀: 无")
    logger.info("")
    
    for idx, (src, tgt) in enumerate(path_mappings, 1):
        logger.info(f"📁 映射 {idx}: {src} ➜ {tgt}")
    logger.info("=" * 80)
    
    # 解析所有路径映射
    mapping_cids = []
    failed_mappings = []
    
    for idx, (source_path, target_path) in enumerate(path_mappings, 1):
        logger.info(f"\n🔄 正在解析映射 {idx}/{len(path_mappings)}: {source_path} ➜ {target_path}")
        
        logger.info(f"📂 解析源目录: {source_path}")
        source_cid = find_directory_by_path(source_path)
        
        if source_cid is None:
            logger.error(f"❌ 无法找到源目录，跳过此映射")
            failed_mappings.append((source_path, target_path, "源目录不存在"))
            continue
        
        logger.info(f"📂 解析目标目录: {target_path}")
        target_cid = find_directory_by_path(target_path)
        
        if target_cid is None:
            logger.error(f"❌ 无法找到目标目录，跳过此映射")
            failed_mappings.append((source_path, target_path, "目标目录不存在"))
            continue
        
        mapping_cids.append({
            'index': idx,
            'source_path': source_path,
            'target_path': target_path,
            'source_cid': source_cid,
            'target_cid': target_cid
        })
        logger.info(f"✅ 映射解析成功")
    
    logger.info("")
    logger.info("=" * 80)
    if mapping_cids:
        logger.info(f"✅ 成功解析 {len(mapping_cids)}/{len(path_mappings)} 个路径映射")
    else:
        logger.error(f"❌ 没有有效的路径映射")
        
    if failed_mappings:
        logger.warning(f"⚠️  失败 {len(failed_mappings)} 个路径映射:")
        for src, tgt, reason in failed_mappings:
            logger.warning(f"   ├─ {src} ➜ {tgt}")
            logger.warning(f"   └─ 原因: {reason}")
    
    if not mapping_cids:
        logger.error("=" * 80)
        logger.error("❌ 任务终止: 没有可用的路径映射")
        logger.error("=" * 80)
        return False
    
    logger.info("=" * 80)
    
    # 开始循环检查
    run_count = 0
    interval_seconds = interval_minutes * 60
    total_moved = 0
    total_failed = 0
    cookie_check_interval = 10  # 每10轮检查一次 Cookie
    
    try:
        while True:
            run_count += 1
            
            # 定期检查 Cookie 是否有效
            if run_count % cookie_check_interval == 1 and run_count > 1:
                logger.info("")
                logger.info("🔐 定期检查 Cookie 状态...")
                if not check_cookie_valid():
                    logger.error("")
                    logger.error("=" * 80)
                    logger.error("❌ Cookie 已失效！程序将停止运行")
                    logger.error("=" * 80)
                    logger.error("")
                    logger.error("请执行以下步骤更新 Cookie：")
                    logger.error("  1. 访问 https://115.com 重新登录")
                    logger.error("  2. 按 F12 打开开发者工具")
                    logger.error("  3. 切换到 Network 标签，刷新页面")
                    logger.error("  4. 找到任意请求，复制 Cookie 值")
                    logger.error("  5. 更新环境变量:")
                    logger.error("     - 修改 docker-compose.yml 中的 COOKIE")
                    logger.error("     - 或删除 data/115-cookies.txt 并重启容器")
                    logger.error("  6. 重启容器: docker-compose restart")
                    logger.error("")
                    logger.error("=" * 80)
                    return False
                else:
                    logger.info("✅ Cookie 状态正常")
            
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"🔄 第 {run_count} 次检查开始")
            logger.info(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 80)
            
            round_moved = 0
            round_failed = 0
            
            # 处理每个映射
            for mapping in mapping_cids:
                idx = mapping['index']
                source_path = mapping['source_path']
                target_path = mapping['target_path']
                source_cid = mapping['source_cid']
                target_cid = mapping['target_cid']
                
                logger.info("")
                logger.info(f"📦 处理映射 {idx}/{len(mapping_cids)}")
                logger.info(f"   源: {source_path}")
                logger.info(f"   ➜  {target_path}")
                logger.info("-" * 80)
                
                try:
                    # 获取源目录中的文件（带超时和重试）
                    logger.info(f"🔍 扫描源目录 (ID: {source_cid})...")
                    files_to_move = []
                    total_files = 0
                    excluded_files = 0
                    small_files = 0
                    
                    @with_retry_and_timeout(operation_name=f"扫描文件列表 {source_path}")
                    def scan_source_files():
                        result = []
                        stats = {'total': 0, 'excluded': 0, 'small': 0}
                        
                        for file_info in iter_files(
                            client=client,
                            cid=source_cid,
                            cur=0,  # 遍历子目录树
                            page_size=1000
                        ):
                            stats['total'] += 1
                            file_size = file_info.get('size', 0)
                            file_name = file_info.get('name', '')
                            file_id = file_info.get('id', '')
                            file_path = file_info.get('path', '')
                            
                            # 如果path为空，使用name作为显示
                            display_path = file_path if file_path else file_name
                            
                            # 检查是否应该排除该文件
                            if should_exclude_file(file_name, exclude_extensions):
                                stats['excluded'] += 1
                                continue
                            
                            # 检查文件大小
                            if file_size >= min_size_bytes:
                                result.append({
                                    'id': file_id,
                                    'name': file_name,
                                    'size': file_size,
                                    'path': file_path,
                                    'display_path': display_path
                                })
                                logger.info(f"  ✓ {display_path} ({format_file_size(file_size)})")
                            else:
                                stats['small'] += 1
                        
                        return result, stats
                    
                    try:
                        files_to_move, file_stats = scan_source_files()
                        total_files = file_stats['total']
                        excluded_files = file_stats['excluded']
                        small_files = file_stats['small']
                    except Exception as e:
                        error_str = str(e).lower()
                        if 'login' in error_str or 'auth' in error_str or 'cookie' in error_str:
                            logger.error("")
                            logger.error("=" * 80)
                            logger.error("❌ 扫描文件时检测到 Cookie 已失效！")
                            logger.error("=" * 80)
                            logger.error("")
                            logger.error("请立即更新 Cookie 并重启容器")
                            logger.error("详细步骤请查看上方日志")
                            logger.error("=" * 80)
                            return False
                        else:
                            # 其他错误（包括超时）记录后继续处理下一个映射
                            logger.error(f"❌ 扫描目录失败: {e}")
                            logger.warning(f"⚠️  跳过此映射，继续处理下一个...")
                            continue
                    
                    logger.info("")
                    logger.info(f"📊 扫描完成:")
                    logger.info(f"   ├─ 总文件数: {total_files}")
                    if small_files > 0:
                        logger.info(f"   ├─ 过小文件: {small_files} (< {format_file_size(min_size_bytes)})")
                    if excluded_files > 0:
                        logger.info(f"   ├─ 排除文件: {excluded_files} (后缀过滤)")
                    logger.info(f"   └─ 待移动: {len(files_to_move)}")
                    
                    # 移动文件
                    if files_to_move:
                        logger.info("")
                        logger.info(f"📤 开始移动 {len(files_to_move)} 个文件...")
                        logger.info("-" * 80)
                        
                        success_count = 0
                        fail_count = 0
                        
                        for file_info in files_to_move:
                            try:
                                display_info = file_info.get('display_path') or file_info.get('name', '未知文件')
                                size_info = format_file_size(file_info['size'])
                                logger.info(f"  ➜ {display_info}")
                                logger.info(f"     大小: {size_info}, ID: {file_info['id']}")
                                
                                result = move_files(file_info['id'], target_cid)
                                
                                if result.get('state'):
                                    success_count += 1
                                    logger.info(f"     ✅ 成功")
                                else:
                                    fail_count += 1
                                    error_msg = result.get('error', result.get('error_msg', '未知错误'))
                                    logger.error(f"     ❌ 失败: {error_msg}")
                                
                                # 添加小延迟，避免请求过快
                                time.sleep(0.5)
                                
                            except Exception as e:
                                fail_count += 1
                                logger.error(f"     ❌ 异常: {e}")
                        
                        logger.info("")
                        logger.info(f"📈 移动结果: ✅ 成功 {success_count} | ❌ 失败 {fail_count}")
                        round_moved += success_count
                        round_failed += fail_count
                    else:
                        logger.info("")
                        logger.info("💤 没有符合条件的文件需要移动")
                    
                except Exception as e:
                    logger.error(f"❌ 处理映射时发生错误: {e}")
                    import traceback
                    logger.error(f"详细错误:\n{traceback.format_exc()}")
            
            # 本轮统计
            total_moved += round_moved
            total_failed += round_failed
            
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"📊 本轮统计: ✅ 移动 {round_moved} 个 | ❌ 失败 {round_failed} 个")
            logger.info(f"📊 总计统计: ✅ 已移动 {total_moved} 个 | ❌ 失败 {total_failed} 个")
            
            # 如果本轮有文件移动，触发回调
            if round_moved > 0:
                trigger_callback()
            
            # 等待下一次检查
            next_check_time = datetime.now().timestamp() + interval_seconds
            next_check_str = datetime.fromtimestamp(next_check_time).strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"⏰ 下次检查: {next_check_str}")
            logger.info(f"😴 等待 {interval_minutes} 分钟...")
            logger.info("=" * 80)
            
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 80)
        logger.info("🛑 收到中断信号，任务停止")
        logger.info("=" * 80)
        logger.info(f"📊 运行统计:")
        logger.info(f"   ├─ 执行次数: {run_count}")
        logger.info(f"   ├─ 成功移动: {total_moved} 个文件")
        logger.info(f"   └─ 移动失败: {total_failed} 个文件")
        logger.info("=" * 80)
        return True
    except Exception as e:
        logger.error("")
        logger.error("=" * 80)
        logger.error(f"❌ 任务异常终止: {e}")
        logger.error("=" * 80)
        import traceback
        logger.error(f"详细错误:\n{traceback.format_exc()}")
        return False


def main():
    """主函数 - Docker版本"""
    
    global DEFAULT_API_TIMEOUT, DEFAULT_API_RETRY_TIMES, BARK_URL, CALLBACK_URL
    
    # 读取环境变量
    source_path = os.environ.get('SOURCE_PATH', '').strip()
    target_path = os.environ.get('TARGET_PATH', '').strip()
    path_mappings_str = os.environ.get('PATH_MAPPINGS', '').strip()
    exclude_extensions_str = os.environ.get('EXCLUDE_EXTENSIONS', '').strip()
    check_interval = os.environ.get('CHECK_INTERVAL', '5').strip()
    min_file_size = os.environ.get('MIN_FILE_SIZE', '200MB').strip()
    log_retention_days = os.environ.get('LOG_RETENTION_DAYS', '7').strip()
    mode = os.environ.get('MODE', 'auto').strip().lower()
    
    # 读取超时和重试配置
    api_timeout = os.environ.get('API_TIMEOUT', str(DEFAULT_API_TIMEOUT)).strip()
    api_retry_times = os.environ.get('API_RETRY_TIMES', str(DEFAULT_API_RETRY_TIMES)).strip()
    
    # 读取Bark通知配置
    bark_url = os.environ.get('BARK_URL', '').strip()
    
    # 读取回调URL配置
    callback_url = os.environ.get('CALLBACK_URL', '').strip()
    
    # 设置日志
    try:
        log_days = int(log_retention_days)
        if log_days < 1:
            log_days = 7
    except:
        log_days = 7
    
    setup_logger(log_days)
    
    # 设置全局变量（在logger初始化之后）
    if bark_url:
        BARK_URL = bark_url
        logger.info(f"📱 Bark通知已启用")
    
    if callback_url:
        CALLBACK_URL = callback_url
        logger.info(f"🔔 文件移动回调已启用: {CALLBACK_URL}")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("🚀 115网盘文件移动工具 - Docker版本")
    logger.info("=" * 80)
    logger.info(f"📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📝 日志保留: {log_days} 天")
    logger.info(f"🔧 运行模式: {mode}")
    
    # 解析和设置超时配置
    try:
        timeout_val = int(api_timeout)
        if timeout_val < 10:
            logger.warning(f"⚠️  API_TIMEOUT 值 {timeout_val} 秒过短，已调整为最小值 10 秒")
            timeout_val = 10
        DEFAULT_API_TIMEOUT = timeout_val
        logger.info(f"⏱️  API超时: {DEFAULT_API_TIMEOUT} 秒")
    except:
        logger.warning(f"⚠️  API_TIMEOUT 值无效: {api_timeout}，使用默认值 {DEFAULT_API_TIMEOUT} 秒")
    
    # 解析和设置重试配置
    try:
        retry_val = int(api_retry_times)
        if retry_val < 1:
            logger.warning(f"⚠️  API_RETRY_TIMES 值 {retry_val} 过小，已调整为最小值 1")
            retry_val = 1
        elif retry_val > 10:
            logger.warning(f"⚠️  API_RETRY_TIMES 值 {retry_val} 过大，已调整为最大值 10")
            retry_val = 10
        DEFAULT_API_RETRY_TIMES = retry_val
        logger.info(f"🔄 API重试: {DEFAULT_API_RETRY_TIMES} 次")
    except:
        logger.warning(f"⚠️  API_RETRY_TIMES 值无效: {api_retry_times}，使用默认值 {DEFAULT_API_RETRY_TIMES} 次")
    
    logger.info("=" * 80)
    
    # 解析路径映射
    path_mappings = []
    
    logger.info("")
    logger.info("🔍 解析配置...")
    
    if path_mappings_str:
        # 使用新的 PATH_MAPPINGS 配置
        logger.info("📋 检测到 PATH_MAPPINGS 配置（多组映射模式）")
        path_mappings = parse_path_mappings(path_mappings_str)
        if not path_mappings:
            logger.error("")
            logger.error("=" * 80)
            logger.error("❌ 错误: PATH_MAPPINGS 格式无效")
            logger.error("=" * 80)
            logger.error("")
            logger.error("格式说明:")
            logger.error("  源路径1->目标路径1,源路径2->目标路径2")
            logger.error("")
            logger.error("示例:")
            logger.error("  PATH_MAPPINGS='/待处理/下载->/已完成/视频,/临时/缓存->/归档/2024'")
            logger.error("")
            logger.error("注意事项:")
            logger.error("  - 路径必须以 '/' 开头")
            logger.error("  - 使用 '->' 分隔源和目标")
            logger.error("  - 使用 ',' 分隔多组映射")
            logger.error("=" * 80)
            return 1
    elif source_path and target_path:
        # 使用旧的 SOURCE_PATH 和 TARGET_PATH 配置（兼容）
        logger.info("📋 检测到 SOURCE_PATH/TARGET_PATH 配置（单组映射模式）")
        path_mappings = [(source_path, target_path)]
        logger.info(f"✓ 映射 1: {source_path} -> {target_path}")
    else:
        logger.error("")
        logger.error("=" * 80)
        logger.error("❌ 错误: 未设置路径映射配置")
        logger.error("=" * 80)
        logger.error("")
        logger.error("请选择以下方式之一进行配置:")
        logger.error("")
        logger.error("方式1 - 多组映射（推荐）:")
        logger.error("  docker run -e PATH_MAPPINGS='/源1->/目标1,/源2->/目标2' ...")
        logger.error("")
        logger.error("方式2 - 单组映射（兼容旧版）:")
        logger.error("  docker run -e SOURCE_PATH='/待处理/下载' \\")
        logger.error("             -e TARGET_PATH='/已完成/视频' ...")
        logger.error("")
        logger.error("示例:")
        logger.error("  PATH_MAPPINGS='/待处理/下载->/已完成/视频,/临时->/归档'")
        logger.error("=" * 80)
        return 1
    
    logger.info(f"✅ 成功解析 {len(path_mappings)} 组路径映射")
    
    # 解析排除的文件后缀
    exclude_extensions = parse_exclude_extensions(exclude_extensions_str)
    
    # 验证环境变量
    if mode == 'auto':
        # 解析检查间隔
        try:
            interval_minutes = int(check_interval)
            if interval_minutes < 2:
                logger.warning(f"⚠️  检查间隔 {interval_minutes} 分钟过短，已调整为最小值 2 分钟")
                interval_minutes = 2
            logger.info(f"⏰ 检查间隔: {interval_minutes} 分钟")
        except:
            logger.error(f"❌ 错误: CHECK_INTERVAL 值无效: {check_interval}")
            logger.error("   必须是数字，单位为分钟")
            return 1
        
        # 解析文件大小
        min_size_bytes = parse_file_size(min_file_size)
        if min_size_bytes is None:
            logger.error(f"❌ 错误: MIN_FILE_SIZE 格式无效: {min_file_size}")
            logger.error("   支持格式: 200MB, 1.5GB, 500KB, 1TB 等")
            return 1
        
        logger.info(f"📏 最小文件: {format_file_size(min_size_bytes)}")
    
    # 初始化客户端
    logger.info("")
    if not init_client_from_env():
        logger.error("")
        logger.error("=" * 80)
        logger.error("❌ 程序退出: 客户端初始化失败")
        logger.error("=" * 80)
        return 1
    
    # 运行自动模式
    logger.info("")
    if mode == 'auto':
        auto_move_files_task(path_mappings, interval_minutes, min_size_bytes, exclude_extensions)
    else:
        logger.error("=" * 80)
        logger.error(f"❌ 错误: 不支持的模式: {mode}")
        logger.error("=" * 80)
        logger.error("当前Docker版本仅支持 auto 模式")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
