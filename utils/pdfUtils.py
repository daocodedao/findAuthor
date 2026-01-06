import os,io
import requests
import PyPDF2
import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.logger_settings import api_logger


# 创建缓存目录结构
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
PDF_CACHE_DIR = os.path.join(CACHE_DIR, "pdf")
HTML_CACHE_DIR = os.path.join(CACHE_DIR, "html")

# 创建缓存目录（如果不存在）
if not os.path.exists(PDF_CACHE_DIR):
    os.makedirs(PDF_CACHE_DIR)

def _get_xvid_from_pdf_url( pdf_url):
        """从 PDF URL 中提取 xvid"""
        if not pdf_url:
            return None
        # 从 URL 中提取 xvid
        if "/pdf/" in pdf_url:
            arxiv_id =  pdf_url.split("/pdf/")[1].split(".pdf")[0]
        elif "/abs/" in pdf_url:
            arxiv_id = pdf_url.split("/abs/")[1]
        
        # safe_id = arxiv_id.replace("/", "_").replace(".", "_")
        return arxiv_id
    
def _get_cached_pdf_path( arxiv_id):
    """获取缓存的 PDF 文件路径"""
    if not arxiv_id:
        return None

    # 确保文件名安全
    safe_id = arxiv_id.replace("/", "_").replace(".", "_")
    return os.path.join(PDF_CACHE_DIR, f"{safe_id}.pdf")

def _download_pdf( pdf_url):
    """下载 PDF 文件，支持本地缓存"""
    try:
        # 从 URL 中提取 arxiv ID
        arxiv_id = _get_xvid_from_pdf_url(pdf_url)

        if not arxiv_id:
            api_logger.info(f"无法从 URL 提取 arxiv ID: {pdf_url}")
            return None

        # 检查缓存
        cached_path = _get_cached_pdf_path(arxiv_id)
        if cached_path and os.path.exists(cached_path):
            api_logger.debug(f"使用缓存的 PDF: {cached_path}")
            return open(cached_path, "rb")

        # 下载 PDF
        api_logger.info(f"下载 PDF: {pdf_url}")
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()

        # 保存到缓存
        if cached_path:
            with open(cached_path, "wb") as f:
                f.write(response.content)
            api_logger.info(f"PDF 已缓存: {cached_path}")
            return open(cached_path, "rb")
        else:
            return io.BytesIO(response.content)

    except Exception as e:
        api_logger.info(f"下载 PDF 失败: {e}")
        return None

def _extract_text_from_pdf( pdf_file):
    """从 PDF 文件中提取文本"""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        # 只提取前 2 页，避免处理过多内容
        max_pages = min(2, len(reader.pages))
        for i in range(max_pages):
            text += reader.pages[i].extract_text() + "\n"
        return text
    except Exception as e:
        api_logger.info(f"提取 PDF 文本失败: {e}")
        return ""


