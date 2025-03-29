#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
定时搜索PDF文件中的NSFC字符
每小时运行一次，检查cache/pdf目录下的新增PDF文件，判断是否包含NSFC字符
"""

import os
import sys
import time
import logging
import datetime
import PyPDF2
import schedule
import json
from pathlib import Path
from utils.logger_settings import api_logger



# 基础目录
BASE_DIR = Path(__file__).parent
PDF_DIR = BASE_DIR / "cache" / "pdf"
PROCESSED_FILES_PATH = BASE_DIR / "processed_nsfc_files.json"

def load_processed_files():
    """加载已处理的文件记录"""
    if not PROCESSED_FILES_PATH.exists():
        return {}
    
    try:
        with open(PROCESSED_FILES_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        api_logger.error(f"加载已处理文件记录时出错: {str(e)}")
        return {}

def save_processed_files(processed_files):
    """保存已处理的文件记录"""
    try:
        with open(PROCESSED_FILES_PATH, 'w', encoding='utf-8') as f:
            json.dump(processed_files, f, ensure_ascii=False, indent=2)
    except Exception as e:
        api_logger.error(f"保存已处理文件记录时出错: {str(e)}")

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
    api_logger.info("开始扫描新增PDF文件...")
    
    # 确保目录存在
    if not PDF_DIR.exists():
        api_logger.warning(f"PDF目录 {PDF_DIR} 不存在，将创建该目录")
        PDF_DIR.mkdir(parents=True, exist_ok=True)
    
    # 获取已处理的文件记录
    processed_files = load_processed_files()
    
    # 获取所有PDF文件
    pdf_files = [str(f) for f in PDF_DIR.glob("**/*.pdf")]
    new_files = [f for f in pdf_files if f not in processed_files]
    
    api_logger.info(f"发现 {len(new_files)} 个新增PDF文件")
    
    # 处理新文件
    nsfc_files = []
    for pdf_file in new_files:
        api_logger.info(f"处理文件: {pdf_file}")
        contains_nsfc = search_nsfc_in_pdf(pdf_file)
        
        # 记录处理结果
        processed_files[pdf_file] = {
            "contains_nsfc": contains_nsfc,
            "processed_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if contains_nsfc:
            nsfc_files.append(pdf_file)
            api_logger.info(f"文件 {pdf_file} 包含NSFC字符")
    
    # 保存处理记录
    save_processed_files(processed_files)
    
    # 生成包含NSFC的文件列表
    if nsfc_files:
        nsfc_list_path = BASE_DIR / "nsfc_files_list.txt"
        try:
            with open(nsfc_list_path, 'w', encoding='utf-8') as f:
                f.write(f"# 包含NSFC字符的文件列表 (更新时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n\n")
                for file_path in nsfc_files:
                    f.write(f"- {file_path}\n")
            api_logger.info(f"已生成包含NSFC的文件列表: {nsfc_list_path}")
        except Exception as e:
            api_logger.error(f"生成NSFC文件列表时出错: {str(e)}")
    
    api_logger.info(f"处理完成，共有 {len(nsfc_files)} 个文件包含NSFC字符")
    return nsfc_files

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