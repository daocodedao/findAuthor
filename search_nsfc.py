#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
定时搜索PDF文件中的NSFC字符
每小时运行一次，检查cache/pdf目录下的新增PDF文件，判断是否包含NSFC字符
"""

import os
import sys
import time
import datetime
import PyPDF2
import schedule
from pathlib import Path
from utils.logger_settings import api_logger

# 基础目录
BASE_DIR = Path(__file__).parent
PDF_DIR = BASE_DIR / "cache" / "pdf"
NSFC_FILES_PATH = BASE_DIR / "nsfc_files_list.txt"

# 上次运行时间
last_run_time = None

def search_nsfc_in_pdf(pdf_path):
    """在PDF文件中搜索NSFC字符"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            
            # 搜索NSFC字符（不区分大小写）
            contains_nsfc = "NSFC" in text.upper()
            return contains_nsfc
    except Exception as e:
        api_logger.error(f"处理PDF文件 {pdf_path} 时出错: {str(e)}")
        return False

def scan_new_files():
    """扫描新增的PDF文件"""
    global last_run_time
    
    current_time = datetime.datetime.now()
    api_logger.info(f"开始扫描新增PDF文件... 当前时间: {current_time}")
    
    # 确保目录存在
    if not PDF_DIR.exists():
        api_logger.warning(f"PDF目录 {PDF_DIR} 不存在，将创建该目录")
        PDF_DIR.mkdir(parents=True, exist_ok=True)
    
    # 获取所有PDF文件
    pdf_files = list(PDF_DIR.glob("**/*.pdf"))
    
    # 如果是第一次运行，处理所有文件
    if last_run_time is None:
        new_files = pdf_files
        api_logger.info(f"首次运行，将处理所有 {len(new_files)} 个PDF文件")
    else:
        # 只处理上次运行后创建的文件
        new_files = []
        for pdf_file in pdf_files:
            # 获取文件创建时间
            creation_time = datetime.datetime.fromtimestamp(pdf_file.stat().st_ctime)
            # 如果文件创建时间晚于上次运行时间，则处理
            if creation_time > last_run_time:
                new_files.append(pdf_file)
        
        api_logger.info(f"发现 {len(new_files)} 个新增PDF文件（创建时间晚于 {last_run_time}）")
    
    # 处理新文件
    nsfc_files = []
    for pdf_file in new_files:
        api_logger.info(f"处理文件: {pdf_file}")
        contains_nsfc = search_nsfc_in_pdf(str(pdf_file))
        
        if contains_nsfc:
            nsfc_files.append(pdf_file)
            api_logger.info(f"文件 {pdf_file} 包含NSFC字符")
    
    # 更新NSFC文件列表
    update_nsfc_files_list(nsfc_files)
    
    # 更新上次运行时间
    last_run_time = current_time
    
    api_logger.info(f"处理完成，共有 {len(nsfc_files)} 个新文件包含NSFC字符")
    return nsfc_files

def update_nsfc_files_list(new_nsfc_files):
    """更新包含NSFC的文件列表"""
    if not new_nsfc_files:
        return
    
    # 读取现有的NSFC文件列表
    existing_nsfc_files = []
    if NSFC_FILES_PATH.exists():
        try:
            with open(NSFC_FILES_PATH, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 跳过标题行
                for line in lines:
                    if line.startswith('- '):
                        file_path = line.strip()[2:]  # 去掉"- "前缀
                        existing_nsfc_files.append(file_path)
        except Exception as e:
            api_logger.error(f"读取NSFC文件列表时出错: {str(e)}")
    
    # 合并新旧文件列表
    all_nsfc_files = existing_nsfc_files.copy()
    for file_path in new_nsfc_files:
        str_path = str(file_path)
        if str_path not in all_nsfc_files:
            all_nsfc_files.append(str_path)
    
    # 写入更新后的文件列表
    try:
        with open(NSFC_FILES_PATH, 'w', encoding='utf-8') as f:
            f.write(f"# 包含NSFC字符的文件列表 (更新时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n\n")
            for file_path in all_nsfc_files:
                f.write(f"- {file_path}\n")
        api_logger.info(f"已更新NSFC文件列表，共 {len(all_nsfc_files)} 个文件")
    except Exception as e:
        api_logger.error(f"更新NSFC文件列表时出错: {str(e)}")

def main():
    """主函数"""
    api_logger.info("NSFC搜索服务启动")
    
    # 立即执行一次扫描
    scan_new_files()
    
    # 设置定时任务，每小时执行一次
    schedule.every(1).hour.do(scan_new_files)
    
    # 运行定时任务
    api_logger.info("已设置每小时定时任务，程序将持续运行...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次是否有待执行的任务

if __name__ == "__main__":
    main()