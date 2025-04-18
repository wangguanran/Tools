import os
import zipfile
import gzip
import shutil
import re
import argparse
from pathlib import Path
from datetime import datetime
import heapq
from ParseLog.module.cx2560x.cx2560x import (
    check_cx2560x_ic,
    parse_cx2560x_registers,
    process_cx2560x,
    parse_register
)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='日志解析工具')
    parser.add_argument('--output-charge-log', action='store_true',
                      help='输出充电相关日志到charge.log')
    parser.add_argument('--parse-charger-cx2560x', action='store_true',
                      help='解析cx2560x充电IC的寄存器信息')
    parser.add_argument('--parse-register', nargs=2, metavar=('REG', 'VALUE'),
                      help='解析指定的寄存器值，例如: --parse-register 00 5d')
    return parser.parse_args()

def parse_timestamp(line):
    """解析日志行中的时间戳"""
    try:
        # 尝试匹配时间戳格式，根据实际日志格式可能需要调整
        match = re.search(r'(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}.\d{3})', line)
        if match:
            timestamp_str = match.group(1)
            # 解析时间戳，添加年份（因为日志中可能没有年份）
            return datetime.strptime(f"2024-{timestamp_str}", "%Y-%m-%d %H:%M:%S.%f")
    except Exception as e:
        print(f"解析时间戳失败: {e}")
    return None

def filter_and_sort_logs(directory):
    """筛选并排序日志"""
    pattern = r'(cx2560x)|(sprdbat)|(sprdchg)|(battery)'
    matching_lines = []
    
    # 遍历所有日志文件，但只在kernel目录中查找
    for root, _, files in os.walk(directory):
        if 'kernel' in root.lower():
            for file in files:
                if file.endswith('.log'):
                    file_path = os.path.join(root, file)
                    print(f"处理kernel日志文件: {file_path}")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                if re.search(pattern, line, re.IGNORECASE):
                                    timestamp = parse_timestamp(line)
                                    if timestamp:
                                        # 使用时间戳作为排序键
                                        matching_lines.append((timestamp, line.strip()))
                    except Exception as e:
                        print(f"处理文件 {file_path} 时出错: {e}")
    
    # 按时间戳排序
    matching_lines.sort(key=lambda x: x[0])
    
    # 写入结果到charge.log
    with open('charge.log', 'w', encoding='utf-8') as f:
        for _, line in matching_lines:
            f.write(line + '\n')
    
    print(f"\n在kernel日志中找到 {len(matching_lines)} 条匹配的日志记录")
    print(f"结果已保存到 charge.log")
    
    # 检查是否使用cx2560x充电IC
    if check_cx2560x_ic('charge.log'):
        print("\n检测到使用cx2560x充电IC")
        parse_cx2560x_registers('charge.log')

def is_valid_zip(file_path):
    """检查文件是否是有效的zip文件"""
    try:
        # 首先检查文件头
        with open(file_path, 'rb') as f:
            header = f.read(4)
            print(f"文件头: {header}")
            if header != b'PK\x03\x04':
                print(f"文件头不匹配: 期望 PK\\x03\\x04, 实际 {header}")
                return True  # 即使文件头不匹配也继续尝试
        
        # 然后尝试打开zip文件
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # 尝试读取zip文件信息
            zip_ref.testzip()
            return True
    except (zipfile.BadZipFile, zipfile.LargeZipFile, Exception) as e:
        print(f"检查zip文件时出错: {str(e)}")
        return True  # 即使出错也继续尝试

def extract_gzip(file_path, extract_path):
    """解压gzip文件"""
    try:
        # 确保目标目录存在
        os.makedirs(os.path.dirname(extract_path), exist_ok=True)
        
        # 解压gzip文件
        with gzip.open(file_path, 'rb') as f_in:
            # 移除.zip扩展名
            output_file = extract_path.rstrip('.zip')
            with open(output_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        print(f"成功解压到: {output_file}")
        return True
    except Exception as e:
        print(f"解压gzip文件失败: {str(e)}")
        return False

def unzip_files(directory):
    """解压指定目录下的所有zip文件"""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.zip'):
                zip_path = os.path.join(root, file)
                # 检查解压后的文件是否已经存在
                extract_path = os.path.join(root, file.rstrip('.zip'))
                
                # 如果解压后的文件已经存在，跳过解压
                if os.path.exists(extract_path):
                    print(f"\n文件已存在，跳过解压: {extract_path}")
                    continue
                
                print(f"\n处理文件: {zip_path}")
                print(f"文件大小: {os.path.getsize(zip_path) / 1024:.2f} KB")
                
                try:
                    # 首先尝试作为gzip文件解压
                    if extract_gzip(zip_path, extract_path):
                        continue
                        
                    # 如果gzip解压失败，尝试作为zip文件解压
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        # 获取zip文件中的文件列表
                        file_list = zip_ref.namelist()
                        print(f"zip文件包含 {len(file_list)} 个文件")
                        
                        # 确保目标目录存在
                        os.makedirs(extract_path, exist_ok=True)
                        
                        # 解压文件
                        zip_ref.extractall(extract_path)
                        print(f"成功解压到: {extract_path}")
                    
                except Exception as e:
                    print(f"解压失败 {zip_path}: {str(e)}")
                    print(f"错误类型: {type(e).__name__}")
                    # 打印更详细的错误信息
                    import traceback
                    print("详细错误信息:")
                    print(traceback.format_exc())

def search_kernel_files(directory):
    """在kernel目录中搜索文件"""
    kernel_files = []
    for root, _, files in os.walk(directory):
        if 'kernel' in root.lower():
            for file in files:
                file_path = os.path.join(root, file)
                kernel_files.append(file_path)
    return kernel_files

def process_charge_log(directory):
    """处理充电日志相关的功能"""
    # 筛选并排序日志
    print("\n开始筛选并排序日志...")
    filter_and_sort_logs(directory)
    
    # 搜索kernel目录下的文件
    print("\n开始搜索kernel目录下的文件...")
    kernel_files = search_kernel_files(directory)
    
    # 输出结果
    if kernel_files:
        print("\n找到以下kernel目录下的文件:")
        for file in kernel_files:
            print(file)
    else:
        print("\n未找到kernel目录下的文件")

def main():
    # 解析命令行参数
    args = parse_args()
    
    # 获取当前工作目录
    current_dir = os.getcwd()
    
    # 解压所有zip文件
    print("开始解压zip文件...")
    unzip_files(current_dir)
    
    # 根据命令行参数执行相应功能
    if args.output_charge_log:
        process_charge_log(current_dir)
    
    if args.parse_charger_cx2560x:
        process_cx2560x(None)  # 不再需要传入 charge.log 文件
    
    if args.parse_register:
        reg, value = args.parse_register
        parse_register(reg, value)

if __name__ == "__main__":
    main() 