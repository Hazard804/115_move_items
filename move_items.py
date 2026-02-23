from pathlib import Path
from p115client import P115Client
from p115client.tool.iterdir import iter_files, iter_dirs
from blacksheep import json, redirect, Application, Request
import time
import logging
from datetime import datetime
import re
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Dict


# 全局变量
client = None
logger = None
COOKIE_FILE = "115-cookies.txt"
LOG_DIR = "logs"

# iOS UA 配置
IOS_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 115wangpan_ios/36.2.20"
)


def get_ios_ua_app() -> Dict[str, str]:
    """
    获取 IOS 设备的 header（UA）和 APP
    """
    return {
        "headers": {"user-agent": IOS_UA},
        "app": "ios",
    }


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
    logger = logging.getLogger('move_items')
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


def save_cookie(cookie_str):
    """
    保存cookie到文件
    
    参数:
        cookie_str: cookie字符串
    """
    try:
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            f.write(cookie_str)
        return True
    except Exception as e:
        print(f"保存cookie失败: {e}")
        return False


def load_cookie():
    """
    从文件加载cookie
    
    返回:
        str: cookie字符串，如果文件不存在则返回None
    """
    if not os.path.exists(COOKIE_FILE):
        return None
    
    try:
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"读取cookie失败: {e}")
        return None


def test_cookie(cookie_str):
    """
    测试cookie是否有效（通过遍历根目录）
    
    参数:
        cookie_str: cookie字符串
    
    返回:
        P115Client: 如果cookie有效返回客户端对象，否则返回None
    """
    try:
        print("\n正在验证cookie...")
        test_client = P115Client(cookie_str)
        
        # 尝试遍历根目录的文件夹
        print("正在获取根目录信息...")
        dir_count = 0
        for dir_info in iter_dirs(
            client=test_client, cid=0, max_workers=0, **get_ios_ua_app()
        ):
            dir_count += 1
            if dir_count >= 3:  # 只获取前3个就够了
                break
        
        print(f"✓ Cookie验证成功！在根目录找到 {dir_count} 个文件夹")
        return test_client
    
    except Exception as e:
        print(f"✗ Cookie验证失败: {e}")
        return None


def init_client():
    """
    初始化115客户端，处理cookie的输入和验证
    
    返回:
        P115Client: 客户端对象，如果失败返回None
    """
    global client
    
    print("=" * 80)
    print("115网盘客户端初始化")
    print("=" * 80)
    
    # 检查是否存在已保存的cookie
    existing_cookie = load_cookie()
    
    if existing_cookie:
        print(f"\n检测到已保存的cookie文件: {COOKIE_FILE}")
        use_existing = input("是否使用已保存的cookie？(y/n): ").strip().lower()
        
        if use_existing == 'y':
            print("\n正在使用已保存的cookie...")
            test_client = test_cookie(existing_cookie)
            
            if test_client:
                client = test_client
                return client
            else:
                print("\n已保存的cookie无效，需要重新输入")
        else:
            print("\n将重新输入cookie")
    
    # 输入新的cookie
    print("\n" + "-" * 80)
    print("请输入115网盘的Cookie")
    print("-" * 80)
    print("\n如何获取Cookie：")
    print("  1. 打开浏览器，访问 https://115.com")
    print("  2. 登录你的账号")
    print("  3. 按F12打开开发者工具")
    print("  4. 切换到Network（网络）标签")
    print("  5. 刷新页面，找到任意请求")
    print("  6. 在请求头中找到Cookie字段，复制整个值")
    print("-" * 80)
    
    while True:
        cookie_str = input("\n请粘贴Cookie: ").strip()
        
        if not cookie_str:
            print("错误：Cookie不能为空")
            retry = input("是否重试？(y/n): ").strip().lower()
            if retry != 'y':
                return None
            continue
        
        # 测试cookie
        test_client = test_cookie(cookie_str)
        
        if test_client:
            # 保存cookie
            if save_cookie(cookie_str):
                print(f"✓ Cookie已保存到 {COOKIE_FILE}")
            else:
                print("⚠ Cookie保存失败，但仍可继续使用")
            
            client = test_client
            return client
        else:
            print("\n请检查Cookie是否正确")
            retry = input("是否重试？(y/n): ").strip().lower()
            if retry != 'y':
                return None


def list_directory_tree(cid=0, cur=0, order="user_ptime", asc=1, file_type=99):
    """
    列举指定目录的文件树
    
    参数:
        cid: 目录 id，默认为 0（根目录）
        cur: 是否仅列举当前目录。0: 遍历子目录树，1: 仅当前目录
        order: 排序方式，可选值：
               - "file_name": 文件名
               - "file_size": 文件大小
               - "file_type": 文件种类
               - "user_utime": 修改时间
               - "user_ptime": 创建时间
               - "user_otime": 上一次打开时间
        asc: 升序排列。0: 降序，1: 升序
        file_type: 文件类型过滤
               - 1: 文档
               - 2: 图片
               - 3: 音频
               - 4: 视频
               - 5: 压缩包
               - 6: 应用
               - 7: 书籍
               - 99: 所有文件
    
    返回:
        list: 包含所有文件信息的列表
    """
    print(f"正在列举目录 (cid={cid}) 的文件...")
    print("-" * 80)
    
    files_list = []
    file_count = 0
    
    for file_info in iter_files(
        client=client,
        cid=cid,
        type=file_type,
        order=order,
        asc=asc,
        cur=cur,
        page_size=1000,  # 每页获取1000个文件
        **get_ios_ua_app(),
    ):
        file_count += 1
        files_list.append(file_info)
        
        # 打印文件信息
        name = file_info.get('name', '')
        size = file_info.get('size', 0)
        fid = file_info.get('id', '')
        path = file_info.get('path', '')
        
        # 格式化文件大小
        size_str = format_file_size(size)
        
        print(f"{file_count}. {name}")
        print(f"   ID: {fid}")
        print(f"   大小: {size_str}")
        print(f"   路径: {path}")
        print()
    
    print("-" * 80)
    print(f"共找到 {file_count} 个文件")
    return files_list


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


def list_directories(cid=0, app='ios', max_dirs=0):
    """
    列举指定目录下的所有子目录
    
    参数:
        cid: 目录 id，默认为 0（根目录）
        app: 使用指定 app（设备）的接口，默认为 'ios'
        max_dirs: 估计最大存在的目录数，<= 0 时则无限，默认为 0
    
    返回:
        list: 包含所有目录信息的列表
    """
    print(f"正在列举目录 (cid={cid}) 的子目录...")
    print("-" * 80)
    
    dirs_list = []
    dir_count = 0
    
    for dir_info in iter_dirs(
        client=client,
        cid=cid,
        app=app,
        max_dirs=max_dirs,
        max_workers=0,  # 单工作者惰性执行
        **get_ios_ua_app() if app == 'ios' else {},
    ):
        dir_count += 1
        dirs_list.append(dir_info)
        
        # 打印目录信息
        name = dir_info.get('name', '')
        dir_id = dir_info.get('id', '')
        parent_id = dir_info.get('parent_id', '')
        path = dir_info.get('path', '')
        
        print(f"{dir_count}. [目录] {name}")
        print(f"   ID: {dir_id}")
        print(f"   父目录ID: {parent_id}")
        print(f"   路径: {path}")
        print()
    
    print("-" * 80)
    print(f"共找到 {dir_count} 个子目录")
    return dirs_list


def list_directories_tree(cid=0, app='ios', max_depth=None):
    """
    以树状结构列举目录树
    
    参数:
        cid: 目录 id，默认为 0（根目录）
        app: 使用指定 app（设备）的接口，默认为 'ios'
        max_depth: 最大遍历深度，None 表示无限制
    
    返回:
        dict: 目录树结构 {目录ID: {'info': 目录信息, 'children': [子目录列表]}}
    """
    print(f"正在构建目录树 (cid={cid})...")
    
    dir_tree = {}
    all_dirs = []
    
    for dir_info in iter_dirs(
        client=client,
        cid=cid,
        app=app,
        max_workers=0,
        **get_ios_ua_app() if app == 'ios' else {},
    ):
        all_dirs.append(dir_info)
        dir_id = dir_info.get('id')
        dir_tree[dir_id] = {
            'info': dir_info,
            'children': []
        }
    
    # 构建父子关系
    for dir_info in all_dirs:
        dir_id = dir_info.get('id')
        parent_id = dir_info.get('parent_id')
        
        if parent_id in dir_tree:
            dir_tree[parent_id]['children'].append(dir_id)
    
    print(f"目录树构建完成，共 {len(all_dirs)} 个目录")
    return dir_tree


def print_directory_tree(dir_tree, root_id=0, indent=0, max_depth=None):
    """
    打印目录树结构
    
    参数:
        dir_tree: 目录树字典（由 list_directories_tree 返回）
        root_id: 起始目录ID
        indent: 当前缩进级别
        max_depth: 最大显示深度
    """
    if max_depth is not None and indent >= max_depth:
        return
    
    if root_id not in dir_tree:
        return
    
    node = dir_tree[root_id]
    info = node['info']
    name = info.get('name', '根目录')
    dir_id = info.get('id')
    
    prefix = "  " * indent + ("└─ " if indent > 0 else "")
    print(f"{prefix}{name} (ID: {dir_id})")
    
    # 递归打印子目录
    for child_id in node['children']:
        print_directory_tree(dir_tree, child_id, indent + 1, max_depth)


def move_files(file_ids, target_pid=0, use_app_api=False):
    """
    移动文件或目录到指定目录
    
    ⚠️ 注意事项：
    1. 请不要并发执行
    2. 限制在 5 万个文件和目录以内
    3. 可以移动到不存在的目录id（会成为悬空节点）
    4. 使用 client.tool_space() 方法可以修复悬空节点（一天只能用一次）
    
    参数:
        file_ids: 文件或目录ID，可以是：
                 - 单个ID (int 或 str)
                 - ID列表 (list/tuple)
                 - 逗号分隔的ID字符串 (str)
        target_pid: 目标目录ID，默认为 0（根目录）
        use_app_api: 是否使用 app 接口（默认使用 web 接口）
                    - False: 使用 fs_move (web接口)
                    - True: 使用 fs_move_app (iOS接口)
    
    返回:
        dict: API 返回的结果
    """
    try:
        if use_app_api:
            # 使用 app 接口 (fs_move_app) - iOS 接口
            # 需要将 file_ids 转换为逗号分隔的字符串
            if isinstance(file_ids, (list, tuple)):
                ids_str = ','.join(str(fid) for fid in file_ids)
            else:
                ids_str = str(file_ids)
            
            payload = {
                'ids': ids_str,
                'to_cid': target_pid
            }
            
            result = client.fs_move_app(payload, pid=target_pid, **get_ios_ua_app())
        else:
            # 使用 web 接口 (fs_move)
            # payload 可以是单个ID、ID列表或字典
            result = client.fs_move(file_ids, pid=target_pid)
        
        return result
    
    except Exception as e:
        print(f"移动文件时发生错误: {e}")
        return {'state': False, 'error': str(e)}


def move_files_batch(file_ids, target_pid=0, batch_size=1000, use_app_api=False):
    """
    批量移动文件（自动分批处理大量文件）
    
    参数:
        file_ids: 文件或目录ID列表
        target_pid: 目标目录ID
        batch_size: 每批处理的文件数量，默认1000（建议不超过5万）
        use_app_api: 是否使用 app 接口
    
    返回:
        list: 每批操作的结果列表
    """
    if not isinstance(file_ids, (list, tuple)):
        file_ids = [file_ids]
    
    results = []
    total = len(file_ids)
    
    print(f"准备移动 {total} 个文件/目录到目标目录 (pid={target_pid})")
    
    # 分批处理
    for i in range(0, total, batch_size):
        batch = file_ids[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        
        print(f"正在处理第 {batch_num}/{total_batches} 批 ({len(batch)} 个文件)...")
        
        result = move_files(batch, target_pid, use_app_api)
        results.append(result)
        
        if result.get('state'):
            print(f"✓ 第 {batch_num} 批移动成功")
        else:
            print(f"✗ 第 {batch_num} 批移动失败: {result.get('error', '未知错误')}")
    
    print(f"\n移动操作完成，共处理 {total_batches} 批")
    return results


def find_directory_by_path(path, start_cid=0):
    """
    根据路径查找目录ID
    
    参数:
        path: 目录路径，格式如 "/folder1/folder2/folder3" 或 "folder1/folder2"
               路径以 / 开头表示从根目录开始
               不以 / 开头则从 start_cid 开始查找
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
        print(f"正在查找: {folder_name} (当前目录ID: {current_cid})")
        
        # 获取当前目录下的所有子目录
        found = False
        for dir_info in iter_dirs(
            client=client, cid=current_cid, max_workers=0, **get_ios_ua_app()
        ):
            if dir_info.get('name') == folder_name:
                current_cid = dir_info.get('id')
                found = True
                print(f"  ✓ 找到: {folder_name} (ID: {current_cid})")
                break
        
        if not found:
            print(f"  ✗ 未找到目录: {folder_name}")
            print(f"  提示: 在目录 {current_cid} 下找不到名为 '{folder_name}' 的子目录")
            return None
    
    print(f"\n✓ 成功找到目标目录 ID: {current_cid}")
    return current_cid


def get_directory_input(prompt_text="目录"):
    """
    获取用户输入的目录（支持路径或ID）
    
    参数:
        prompt_text: 提示文本，用于区分源目录、目标目录等
    
    返回:
        int: 目录ID
    """
    print(f"\n请输入{prompt_text}（支持两种方式）:")
    print("  1. 输入目录路径，如: /我的文件/视频")
    print("  2. 输入目录ID，如: 12345")
    print("  3. 直接回车使用根目录")
    print("\n⚠️  路径输入注意事项:")
    print("  - 路径必须以 / 开头（表示从根目录开始）")
    print("  - 路径区分大小写，请确保与实际文件夹名称完全一致")
    print("  - 示例：/我的文件/视频/电影")
    print("  - 错误示例：我的文件/视频（缺少开头的 /）")
    
    user_input = input(f"\n请输入{prompt_text}: ").strip()
    
    if not user_input:
        print("使用根目录 (ID: 0)")
        return 0
    
    # 判断是路径还是ID
    if user_input.startswith('/') or '/' in user_input:
        # 是路径
        print(f"\n正在解析路径: {user_input}")
        cid = find_directory_by_path(user_input)
        
        if cid is None:
            print("\n路径解析失败，是否使用根目录？(y/n): ", end='')
            if input().strip().lower() == 'y':
                return 0
            else:
                return None
        
        return cid
    else:
        # 尝试作为ID解析
        try:
            cid = int(user_input)
            print(f"使用目录ID: {cid}")
            return cid
        except ValueError:
            print(f"错误：'{user_input}' 不是有效的目录ID或路径")
            return None


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


def get_time_input(prompt, min_minutes=2):
    """
    获取用户输入的时间（分钟）
    
    参数:
        prompt: 提示信息
        min_minutes: 最小分钟数
    
    返回:
        int: 分钟数，失败返回 None
    """
    while True:
        user_input = input(prompt).strip()
        
        if not user_input:
            return None
        
        try:
            minutes = int(user_input)
            if minutes < min_minutes:
                print(f"错误：时间不能小于 {min_minutes} 分钟")
                continue
            return minutes
        except ValueError:
            print(f"错误：'{user_input}' 不是有效的数字")
            continue


def get_size_input(prompt):
    """
    获取用户输入的文件大小
    
    参数:
        prompt: 提示信息
    
    返回:
        int: 字节数，失败返回 None
    """
    while True:
        print("\n文件大小格式示例：")
        print("  - 200MB 或 200M")
        print("  - 1.5GB 或 1.5G")
        print("  - 500KB 或 500K")
        
        user_input = input(prompt).strip()
        
        if not user_input:
            return None
        
        size_bytes = parse_file_size(user_input)
        
        if size_bytes is None:
            print(f"错误：'{user_input}' 不是有效的文件大小格式")
            continue
        
        # 显示解析结果
        print(f"已解析为: {format_file_size(size_bytes)}")
        confirm = input("确认使用这个大小？(y/n): ").strip().lower()
        
        if confirm == 'y':
            return size_bytes


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
                    page_size=1000,
                    **get_ios_ua_app(),
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
                            # 使用display_path，如果没有则用name
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


def run_auto_move_mode():
    """
    运行自动移动模式
    """
    print("\n" + "=" * 80)
    print("自动移动文件模式")
    print("=" * 80)
    print("\n此模式将定期检查指定目录，自动移动符合条件的文件")
    print("\n⚠️  注意事项:")
    print("  1. 路径区分大小写，请仔细检查")
    print("  2. 路径格式示例: /我的文件/视频")
    print("  3. 程序将持续运行，按 Ctrl+C 可停止")
    print(f"  4. 日志将按天保存到 {LOG_DIR} 目录")
    
    # 获取源目录
    print("\n" + "-" * 80)
    print("步骤 1/4: 设置源目录（待检查的目录）")
    print("-" * 80)
    print("\n⚠️  路径输入规则:")
    print("  - 必须以 / 开头")
    print("  - 严格区分大小写")
    print("  - 示例: /待处理/下载")
    source_path = input("\n请输入源目录路径: ").strip()
    
    if not source_path:
        print("错误：源目录路径不能为空")
        return
    
    # 获取目标目录
    print("\n" + "-" * 80)
    print("步骤 2/4: 设置目标目录（文件将移动到此目录）")
    print("-" * 80)
    print("\n⚠️  路径输入规则:")
    print("  - 必须以 / 开头")
    print("  - 严格区分大小写")
    print("  - 示例: /已完成/视频")
    target_path = input("\n请输入目标目录路径: ").strip()
    
    if not target_path:
        print("错误：目标目录路径不能为空")
        return
    
    if source_path == target_path:
        print("错误：源目录和目标目录不能相同")
        return
    
    # 获取检查间隔
    print("\n" + "-" * 80)
    print("步骤 3/4: 设置检查间隔")
    print("-" * 80)
    interval_minutes = get_time_input("\n请输入检查间隔（分钟，最少2分钟）: ", min_minutes=2)
    
    if interval_minutes is None:
        print("错误：未设置检查间隔")
        return
    
    # 获取最小文件大小
    print("\n" + "-" * 80)
    print("步骤 4/4: 设置最小文件大小")
    print("-" * 80)
    min_size_bytes = get_size_input("\n请输入最小文件大小: ")
    
    if min_size_bytes is None:
        print("错误：未设置最小文件大小")
        return
    
    # 确认配置
    print("\n" + "=" * 80)
    print("配置确认")
    print("=" * 80)
    print(f"源目录路径: {source_path}")
    print(f"目标目录路径: {target_path}")
    print(f"检查间隔: {interval_minutes} 分钟")
    print(f"最小文件大小: {format_file_size(min_size_bytes)}")
    print("=" * 80)
    
    confirm = input("\n确认以上配置并开始任务？(y/n): ").strip().lower()
    
    if confirm != 'y':
        print("任务已取消")
        return
    
    # 启动任务
    print("\n正在启动任务...\n")
    auto_move_files_task(source_path, target_path, interval_minutes, min_size_bytes)


def run_manual_mode():
    """
    运行手动模式（原有功能）
    """
    # 获取要列举的目录
    print("=== 选择要列举的目录 ===")
    cid = get_directory_input("要列举的目录")
    
    if cid is None:
        print("目录输入无效，程序退出")
        return
    
    # 询问是否遍历子目录
    cur_input = input("是否仅列举当前目录？(y/n，默认n遍历子目录): ").strip().lower()
    cur = 1 if cur_input == 'y' else 0
    
    print(f"\n=== 列举目录 (ID: {cid}) 的文件树 ===\n")
    files_list = list_directory_tree(cid=cid, cur=cur)
    
    # 如果没有文件，直接退出
    if not files_list:
        print("没有找到任何文件")
        return
    
    # 询问用户是否要移动文件
    print("\n" + "=" * 80)
    move_input = input("\n是否要移动文件？(y/n): ").strip().lower()
    
    if move_input == 'y':
        while True:
            # 让用户选择要移动的文件
            file_index_input = input(f"\n请输入要移动的文件序号 (1-{len(files_list)})，输入 q 退出: ").strip()
            
            if file_index_input.lower() == 'q':
                print("退出移动操作")
                break
            
            try:
                file_index = int(file_index_input)
                if file_index < 1 or file_index > len(files_list):
                    print(f"错误：序号必须在 1-{len(files_list)} 之间")
                    continue
                
                # 获取选中的文件
                selected_file = files_list[file_index - 1]
                file_id = selected_file.get('id')
                file_name = selected_file.get('name')
                
                print(f"\n已选择文件: {file_name} (ID: {file_id})")
                
                # 获取目标目录
                print("\n=== 选择目标目录 ===")
                target_pid = get_directory_input("目标目录")
                
                if target_pid is None:
                    print("目标目录输入无效，取消移动操作")
                    continue
                
                # 确认操作
                confirm = input(f"\n确认将 '{file_name}' 移动到目录 {target_pid}？(y/n): ").strip().lower()
                
                if confirm == 'y':
                    print(f"\n正在移动文件...")
                    result = move_files(file_id, target_pid)
                    
                    if result.get('state'):
                        print(f"✓ 移动成功！")
                    else:
                        error_msg = result.get('error', result.get('error_msg', '未知错误'))
                        print(f"✗ 移动失败: {error_msg}")
                else:
                    print("已取消移动操作")
                
                # 询问是否继续移动其他文件
                continue_input = input("\n是否继续移动其他文件？(y/n): ").strip().lower()
                if continue_input != 'y':
                    print("退出移动操作")
                    break
                    
            except ValueError:
                print(f"错误：无效的序号 '{file_index_input}'")
                continue
    else:
        print("未执行移动操作")


if __name__ == "__main__":
    print("=" * 80)
    print("115网盘文件移动工具")
    print("=" * 80)
    
    # 初始化客户端
    if not init_client():
        print("\n客户端初始化失败，程序退出")
        exit(1)
    
    # 设置日志
    print("\n" + "-" * 80)
    print("日志配置")
    print("-" * 80)
    print(f"日志将按天保存到 {LOG_DIR} 目录")
    
    log_days_input = input("\n请输入日志保留天数（默认7天，直接回车使用默认值）: ").strip()
    
    if log_days_input:
        try:
            log_retention_days = int(log_days_input)
            if log_retention_days < 1:
                print("日志保留天数不能小于1，使用默认值7天")
                log_retention_days = 7
        except ValueError:
            print("输入无效，使用默认值7天")
            log_retention_days = 7
    else:
        log_retention_days = 7
    
    setup_logger(log_retention_days)
    logger.info(f"日志系统已初始化，保留 {log_retention_days} 天")
    
    # 选择运行模式
    print("\n" + "=" * 80)
    print("请选择运行模式：")
    print("  1. 手动模式 - 浏览目录并手动选择文件移动")
    print("  2. 自动模式 - 定期自动检查并移动符合条件的文件")
    
    mode = input("\n请输入模式编号 (1 或 2): ").strip()
    
    if mode == '1':
        run_manual_mode()
    elif mode == '2':
        run_auto_move_mode()
    else:
        print("无效的模式选择")
