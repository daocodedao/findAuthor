import requests
import feedparser
import time
from datetime import datetime, timedelta
import json
import os
import re

import io
from openai import OpenAI
import schedule
import hashlib
from db_manager import DBManager
from model.paper import Paper
from model.paperAuthor import PaperAuthor

from utils.logger_settings import api_logger
from utils.pdfUtils import _get_xvid_from_pdf_url, _download_pdf, _extract_text_from_pdf

PUBDATEKEY = "发布日期"

class ArxivMonitor:
    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query?"

        # # 初始化数据库
        # self.engine = get_engine()
        # init_db(self.engine)
        # api_logger.info("数据库表已初始化")
        
        # 初始化数据库管理器
        self.db_manager = DBManager()
        
        # 设置 OpenAI API 密钥
        self.openAiClient = OpenAI(base_url="http://39.105.194.16:6691/v1", api_key="key")
        
    
    def _analyze_paper_with_openai(self, paper_text, paper_title, paper_authors, summary):

        try:
            # 清理文本，移除或替换不兼容的Unicode字符
            def clean_text(text):
                if not text:
                    return ""
                # 替换或移除可能导致编码问题的字符
                return text.encode('utf-8', errors='ignore').decode('utf-8')
            
            cleaned_paper_text = clean_text(paper_text)
            cleaned_paper_title = clean_text(paper_title)
            cleaned_summary = clean_text(summary)
            cleaned_authors = [clean_text(author) for author in paper_authors]
            
            prompt = f"""
            请分析以下学术论文信息，并提取以下内容（用中文回答）：
            1. 所有作者的姓名和所属机构，如果机构隶属于中国，要翻译成中文
            2. 每位作者的位置（第一作者、第二作者，其他作者，通讯作者等）
            3. 作者的邮箱地址
            4. 论文的主要研究方向
            5. 论文的主要内容和贡献
            
            论文标题: {cleaned_paper_title}
            论文摘要: {cleaned_summary}
            作者列表: {', '.join(cleaned_authors)}
            
            论文内容, 只提取前4000个字符:
            {cleaned_paper_text[:4000]}  
            
            请以 JSON 格式返回结果，格式如下, 不要做任何解释，只返回json:
            {{
                "中文标题": "论文中文标题",
                "作者信息": [
                    {{
                        "姓名": "作者姓名，直接使用原文里的名字，不要翻译",
                        "位置": "作者位置，第一作者、第二作者，其他作者，通讯作者等",
                        "单位": "作者单位，如果是中国大学或者中国公司，使用中文描述（不要带数字标记）, 否则还是用英文",
                        "邮箱": "作者邮箱",
                        "国家": "作者国家，翻译成中文"
                    }}
                ],
                "研究方向": "论文研究方向, 中文描述",
                "主要内容": "论文主要内容和贡献，中文描述"
                "nsfc": false "bool类型， 国家自然科学基金(nsfc)是否资助, 默认false"
            }}
            """

            # 记录日志，帮助调试
            api_logger.debug(f"发送到OpenAI的提示长度: {len(prompt)}")
            
            response = self.openAiClient.chat.completions.create(
                model="Qwen/Qwen3-8B",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的学术论文分析助手，擅长从论文中提取关键信息。",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            result = response.choices[0].message.content
            result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL)

            # 尝试解析 JSON 结果
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                # 如果无法解析为 JSON，尝试提取 JSON 部分
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    try:
                        return json.loads(result[json_start:json_end])
                    except:
                        pass

                api_logger.info("无法解析 OpenAI 返回的结果为 JSON 格式")
                return None

        except Exception as e:
            api_logger.info(f"OpenAI 分析失败: {e}")
            api_logger.debug(f"错误详情: {str(e)}")  # 添加更详细的错误日志
            return None

    # 在 search_papers 方法中
    def search_papers(self, query="cat:cs.*", max_results=10000, date_range=None):
        """搜索arXiv论文并下载PDF"""
        results = []
        start_index = 0
        batch_size = 100  # 每次请求100篇论文

        # 构建日期范围查询
        if date_range:
            query = f"{query}+AND+{date_range}"

        while len(results) < max_results:
            current_batch = min(batch_size, max_results - len(results))

            tryMaxAttempts = 5
            for i in range(tryMaxAttempts):
                # 构建查询
                query_url = f"{self.base_url}search_query={query}&start={start_index}&max_results={current_batch}&sortBy=submittedDate&sortOrder=descending"
                api_logger.info(f"正在查询: {query_url}")
                response = requests.get(query_url, timeout=30)
                response.raise_for_status()

                feed = feedparser.parse(response.content)
                if feed and len(feed.entries) > 0:
                    api_logger.info(f"找到 {len(feed.entries)} 篇论文")
                    break
                else:
                    api_logger.info(f"尝试 {i+1}/{tryMaxAttempts} 次，等待 10 秒后重试...")
                    time.sleep(10)
                
            try:
                for entry in feed.entries:
                    # 获取基本信息
                    title = entry.title
                    authors = [author.name for author in entry.authors]
                    # 生成论文唯一标识符
                    paper_id = entry.id

                    # 检查是否已处理过该论文
                    existing_paper = self.db_manager.get_paper(paper_id)
                    if existing_paper:
                        api_logger.debug(f"论文 '{title}' 已处理过，跳过")
                        continue

                    # 获取论文分类信息
                    categories = []
                    if hasattr(entry, "tags"):
                        for tag in entry.tags:
                            if tag.get("term") and tag.get("term").startswith("cs."):
                                categories.append(tag.get("term"))

                    # 获取PDF链接和网页链接
                    pdf_link = ""
                    web_link = ""
                    for link in entry.links:
                        if link.get("title", "") == "pdf":
                            pdf_link = link.href
                        elif (link.get("rel", "") == "alternate" and link.get("type", "") == "text/html"):
                            web_link = link.href

                    if not pdf_link:
                        api_logger.info(f"论文 '{title}' 没有PDF链接，跳过")
                        continue
 
                    # 如果没有找到网页链接，可以从 entry.id 或 PDF 链接构造
                    if not web_link and hasattr(entry, "id"):
                        web_link = entry.id
                    elif not web_link and pdf_link:
                        # 从 PDF 链接构造网页链接
                        arxiv_id = _get_xvid_from_pdf_url(pdf_link)
                        web_link = f"https://arxiv.org/abs/{arxiv_id}"

                    # 下载PDF
                    pdf_file = _download_pdf(pdf_link)
                    if not pdf_file:
                        api_logger.info(f"论文 '{title}' PDF下载失败，跳过")
                        continue

                    # 提取PDF文本
                    paper_text = _extract_text_from_pdf(pdf_file)
                    pdf_file.close()

                    if not paper_text:
                        api_logger.info(f"论文 '{title}' PDF文本提取失败，跳过")
                        continue

                    summary = entry.summary
                    # 使用OpenAI分析
                    api_logger.debug(f"使用OpenAI分析论文: {title}")
                    paper_info = self._analyze_paper_with_openai(paper_text, title, authors, summary)
                    if not paper_info:
                        api_logger.info(f"论文 '{title}' OpenAI分析失败，跳过")
                        continue
                    
                    paper_info["title"] = title
                    paper_info["paper_id"] = paper_id
                    paper_info["pdf_link"] = pdf_link
                    paper_info["web_link"] = web_link
                    paper_info["categories"] = categories
                    paper_info["has_chinese_author"] = False
                    paper_info["has_chinese_email"] = False
                    # 直接创建 Paper 对象
                    # 在代码中已经使用了 Paper 类
                    paper = Paper.from_dict(paper_info)
                    
                    # 将论文和作者信息保存到数据库
                    api_logger.info(f"添加论文: {title}")
                    self.db_manager.save_paper_with_authors(paper)
                    
                    # 添加到结果列表
                    results.append(paper)
                    
                    # 如果已经找到足够的论文，提前结束
                    if len(results) >= max_results:
                        break

                start_index += len(feed.entries)

                # 避免请求过于频繁
                time.sleep(3)

            except Exception as e:
                api_logger.info(f"查询出错: {e}")

        return results

    def run(
        self,
        query="cat:cs.*",
        max_results=10000,
        days_back=365,
    ):
        # 获取上次搜索日期
        last_search_date = self.db_manager.get_last_publish_date()
        today = datetime.now().date()
        
        # 确定搜索日期范围
        if last_search_date:
            # 如果有上次搜索记录，只搜索从上次搜索到今天的论文
            # 为了确保不遗漏，往前多搜索一天
            start_date = last_search_date - timedelta(days=1)
            api_logger.info(f"检测到上次处理日期: {last_search_date.strftime('%Y-%m-%d')}")
            api_logger.info(f"将搜索从 {start_date.strftime('%Y-%m-%d')} 到今天的论文")
        else:
            # 首次搜索，使用指定的天数
            start_date = today - timedelta(days=days_back)
            api_logger.info(f"首次搜索，将搜索过去 {days_back} 天的论文")

        # 构建日期范围查询
        date_range = f"submittedDate:[{start_date.strftime('%Y%m%d')}000000+TO+{today.strftime('%Y%m%d')}235959]"

        api_logger.info(f"开始搜索arxiv论文，查询: {query}")
        api_logger.info(f"日期范围: {start_date.strftime('%Y-%m-%d')} 到 {today.strftime('%Y-%m-%d')}...")
        results = self.search_papers(query=query, max_results=max_results, date_range=date_range)
        api_logger.info(f"找到 {len(results)} 篇来自中国大学的计算机科学论文")
        
        # 关闭数据库连接
        self.db_manager.close()

def daily_task():
    """每日执行的任务"""
    api_logger.info(f"开始执行每日任务，时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    monitor = ArxivMonitor()
    monitor.run()
    api_logger.info(f"每日任务完成，时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    # 立即执行一次
    daily_task()

    # 设置每小时执行一次
    schedule.every().hour.do(daily_task)

    api_logger.info("已设置每小时定时任务，程序将持续运行...")
    # 持续运行，等待定时任务
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次是否有待执行的任务
