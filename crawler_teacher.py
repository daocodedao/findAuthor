#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网站爬虫工具
用于获取指定网站下的所有子页面
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time
import re
from collections import deque
import json
from openai import OpenAI
import asyncio
import os
from datetime import datetime
from crawl4ai import AsyncWebCrawler
from utils.logger_settings import api_logger
from utils.pdfUtils import HTML_CACHE_DIR
from model.universityCollege import UniversityCollege
from model.universityTeacher import UniversityTeacher
from db_manager import DBManager
import schedule
import threading

# 添加任务锁，防止任务重叠执行
task_lock = threading.Lock()
is_task_running = False
    
    
db_manager = DBManager()
db_session = db_manager._get_session()

                    
class CollegeWebCrawler:

    college:UniversityCollege = None
    
    def __init__(self, max_pages=1000, delay=1, timeout=30, headers=None):
        """初始化爬虫
        
        Args:
            max_pages: 最大爬取页面数
            delay: 每次请求之间的延迟（秒）
            timeout: 请求超时时间（秒）
            headers: 请求头
        """
        self.max_pages = max_pages
        self.delay = delay
        self.timeout = timeout
        self.visited_urls = set()
        self.urls_to_visit = deque()
        self.domain_name = ""
        
        # 设置请求头
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        
        self.disallowed_paths = []
    
        self.openAiClient = OpenAI(
            base_url="http://39.105.194.16:6691/v1", api_key="key"
        )
    
    def ifValidUrlText(self, link_text):
        if not link_text:
            return False
        if len(link_text) < 2:
            return False
        if "分享" in link_text:
            return False
        if "收藏" in link_text:
            return False
        if "首页" in link_text:
            return False
        if "TOP" in link_text:
            return False
        
        return True
    
    
    def _is_valid_url(self, url):
        """检查URL是否有效且属于同一域名"""
        parsed_url = urlparse(url)
        
        # 检查URL是否属于同一域名
        if parsed_url.netloc != self.domain_name:
            return False
            
        # 检查URL是否是有效的HTTP/HTTPS链接
        if parsed_url.scheme not in ['http', 'https']:
            return False
            
        # 过滤常见的非HTML内容
        if re.search(r'\.(jpg|jpeg|png|gif|pdf|doc|docx|ppt|pptx|xls|xlsx|zip|rar|tar|gz|mp3|mp4|avi|mov)$', parsed_url.path, re.IGNORECASE):
            return False
        
        if "english" in url.lower():
            return False
        
        return True
          
    async def parseHtml(self, url):
        """解析HTML页面，提取教师信息"""     
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=url,
                verbose=False
            )
            markdown_content = result.markdown
            # 去掉图片 ![alt](url) 或 ![](url)
            markdown_content = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_content)
            # 只保留超链接文本，去掉URL部分 [text](url) -> text
            markdown_content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', markdown_content)
            # 将多个连续的换行符替换为单个换行符
            markdown_content = re.sub(r'\n{2,}', '\n', markdown_content)
            # print(result.markdown) 
            
            # 构建提示，让OpenAI分析页面内容
            prompt = f"""
            分析以下 markdown 内容，如果是某个教师，副教授，教授，研究员，院士介绍的详情页面，提取信息：
            请只返回 json 内容，格式如下，不要输出额外内容，返回的内容要能直接解析为json:
            {{
                "is_teacher_page": false, # "bool 类型。如果页面不止介绍了一个人，或者是院系的教师列表页面返回false”
                "name": "教师姓名",
                "sex": 0, #"int 类型。性别, 0: 未知, 1: 男, 2: 女",
                "is_national_fun": false, #"bool 类型。是否主持国家基金项目 比如 国家自然基金，国家自然科学基金, 默认 false"
                "is_cs": false, #"bool 类型。是否是计算机相关教师 默认 false",
                "bookname": "出版的图书名称，如《计算机科学导论》等，可以不止一本",
                "sciencep_bookname": "科学出版社出版的图书名称，如《计算机科学导论》等，可以不止一本",
                "is_pub_book": false "是否出过专著, 默认 false",
                "is_pub_book_sciencep": false "是否在科学出版社出过专著v",
                "collage_name": "院系名称",
                "title": "职称 如教授、副教授，讲师，院士等",
                "job_title": "职位 如系主任、院长等",
                "tel": "联系电话",
                "email": "电子邮箱， 转换为标准邮箱地址",
                "research_direction": "研究方向",
                "papers": "代表性论文，有1，2篇就行"
            }}

            
            等待分析 markdown 内容：
            {markdown_content}

            """
            
            try:    
                # 调用OpenAI API分析内容
                response = self.openAiClient.chat.completions.create(
                    model="Qwen/Qwen2.5-7B-Instruct",
                    messages=[
                        {"role": "system", "content": "你是一个专业的网页内容分析工具，能够准确提取教师信息。"},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                # 获取分析结果
                analysis_result = response.choices[0].message.content.strip()
                api_logger.info(f"页面分析结果: {analysis_result}")
                
                # 初始化teacher_info变量
                teacher_info = None
                
                # 尝试解析JSON结果
                try:
                    teacher_info = json.loads(analysis_result)
                except json.JSONDecodeError:
                    # 如果无法解析为 JSON，尝试提取 JSON 部分
                    json_start = analysis_result.find("{")
                    json_end = analysis_result.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        try:
                            teacher_info = json.loads(analysis_result[json_start:json_end])
                        except:
                            api_logger.error(f"无法解析OpenAI返回的JSON: {analysis_result}")
                    
                # 如果是教师页面，保存信息
                if self.college and teacher_info and teacher_info.get("is_teacher_page") != False:
                    # 创建教师对象
                    teacher = UniversityTeacher(
                        college_id=self.college.id,
                        university_id=self.college.university_id,
                        name=teacher_info.get("name", ""),
                        sex=int(teacher_info.get("sex", 0)),
                        email=teacher_info.get("email", ""),
                        is_national_fun=teacher_info.get("is_national_fun", False),
                        is_cs=teacher_info.get("is_cs", False),
                        is_pub_book=teacher_info.get("is_pub_book", False),
                        is_pub_book_sciencep=teacher_info.get("is_pub_book_sciencep", False),
                        bookname=teacher_info.get("bookname", ""),
                        sciencep_bookname=teacher_info.get("sciencep_bookname", ""),
                        title=teacher_info.get("title", ""),
                        job_title=teacher_info.get("job_title", ""),
                        tel=teacher_info.get("tel", ""),
                        research_direction=teacher_info.get("research_direction", ""),
                        papers=teacher_info.get("papers", ""),
                        homepage=url
                    )
                    
                    # 保存到数据库
                    success = UniversityTeacher.save(db_session, teacher)
                    if success:
                        api_logger.info(f"成功保存教师信息: {teacher_info.get('name')}")
                    else:
                        api_logger.error(f"保存教师信息失败: {teacher_info.get('name')}")
                    
                    return teacher_info
                else:
                    api_logger.info("不是教师介绍页面")
                    return None
                    
            except Exception as e:
                api_logger.error(f"分析页面内容出错: {e}")
                return None
    
    def get_all_pages(self, start_url):
        """获取指定网站下的所有子页面
        
        Args:
            start_url: 起始URL
            
        Returns:
            页面URL列表
        """
        # 解析起始URL
        parsed_url = urlparse(start_url)
        self.domain_name = parsed_url.netloc
        
        # 初始化队列
        self.urls_to_visit.append(start_url)
        page_info_list = []
        
        api_logger.info(f"开始爬取网站: {start_url}")
          
        # 开始爬取
        while self.urls_to_visit and len(self.visited_urls) < self.max_pages:
            # 获取下一个URL
            current_url = self.urls_to_visit.popleft()
            
            # 如果已经访问过，跳过
            if current_url in self.visited_urls:
                continue
            
            teacherInfo = UniversityTeacher.search_by_homepage(db_session, current_url)
            if teacherInfo:
                api_logger.info(f"已爬取过教师页面: {current_url}")
                continue
                
            api_logger.info(f"正在爬取 ({len(self.visited_urls) + 1}/{self.max_pages}): {current_url}")
            
            try:
                # 发送请求，允许重定向
                response = requests.get(current_url, headers=self.headers, timeout=self.timeout, allow_redirects=True)
                
                # 标记为已访问
                self.visited_urls.add(current_url)
                
                # 检查响应状态
                if response.status_code != 200:
                    api_logger.warning(f"获取页面失败，状态码: {response.status_code}, URL: {current_url}")
                    continue
                
                # 检查是否有JavaScript重定向
                soup = BeautifulSoup(response.text, 'html.parser')
                js_redirect = soup.find('script', string=re.compile(r'window\.location\.href'))
                
                if js_redirect:
                    # 提取重定向URL
                    redirect_match = re.search(r'window\.location\.href\s*=\s*[\'"]([^\'"]+)[\'"]', js_redirect.string)
                    if redirect_match:
                        redirect_url = redirect_match.group(1)
                        # 处理相对URL
                        absolute_redirect_url = urljoin(current_url, redirect_url)
                        api_logger.info(f"发现JavaScript重定向: {absolute_redirect_url}")
                        
                        # 将重定向URL添加到队列前面，优先处理
                        if absolute_redirect_url not in self.visited_urls and self._is_valid_url(absolute_redirect_url):
                            self.urls_to_visit.appendleft(absolute_redirect_url)
                            continue
                
                # 检查内容类型
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type.lower():
                    api_logger.debug(f"跳过非HTML内容: {content_type}, URL: {current_url}")
                    continue
                
                # 处理编码问题
                if 'charset' in content_type:
                    # 从Content-Type中提取编码
                    charset = re.search(r'charset=([^\s;]+)', content_type)
                    if charset:
                        response.encoding = charset.group(1)
                else:
                    # 尝试使用apparent_encoding自动检测编码
                    response.encoding = response.apparent_encoding
                    
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 提取页面标题
                title = "无标题"
                if soup.title:
                    title = soup.title.string.strip() if soup.title.string else "无标题"

                api_logger.info(f"页面标题: {title}")
                    
                # 保存页面信息
                page_info = {
                    'url': current_url,
                    'title': title,
                }
                
                # 分析页面内容，提取关键信息
                teacher_info = asyncio.run(self.parseHtml(current_url))
                
                # 如果是教师页面，将信息添加到页面信息中
                if teacher_info:
                    teacher_info["homepage"] = current_url
                    page_info['teacher_info'] = teacher_info
                
                page_info_list.append(page_info)
                
                # 提取所有链接，但排除导航栏中的链接
                main_content = self._extract_content_with_openai(soup, current_url)
                links_to_follow = []
                
                if main_content:
                    # 如果成功识别到主内容区域，只从主内容中提取链接
                    for link in main_content.find_all('a', href=True):
                        links_to_follow.append(link)
                else:
                    # 如果无法识别主内容区域，则使用全部链接但尝试排除导航栏
                    for link in soup.find_all('a', href=True):
                        links_to_follow.append(link)
                
                # 处理提取到的链接
                for link in links_to_follow:
                    href = link.get('href')
                    link_text = link.get_text(strip=True)
                    if not self.ifValidUrlText(link_text):
                        continue
                        
                    # 处理相对URL
                    absolute_url = urljoin(current_url, href)
                    # 检查URL是否有效
                    if self._is_valid_url(absolute_url) and absolute_url not in self.visited_urls:
                        api_logger.info(f"发现新链接: {absolute_url}")
                        # if absolute_url == "https://ai.hebut.edu.cn/index.htm":
                        #     api_logger.info("发现无用页面")
                        self.urls_to_visit.append(absolute_url)
                        
                # 延迟，避免请求过于频繁
                time.sleep(self.delay)
                
            except Exception as e:
                api_logger.error(f"爬取页面出错: {e}, URL: {current_url}")
                
        api_logger.info(f"爬取完成，共获取 {len(page_info_list)} 个页面")
        

                
        return page_info_list


    def _extract_content_with_openai(self, soup, url):
        """
        使用OpenAI API来识别网页的主要内容区域
        
        Args:
            soup: BeautifulSoup对象
            url: 当前页面URL
            
        Returns:
            BeautifulSoup对象的子集，表示主要内容区域
        """
        # 提取页面的HTML结构（简化版，只保留标签结构）
        simplified_html = self._simplify_html_structure(soup)
        
        # 构建提示
        prompt = f"""
        分析以下 HTML 页面，页面可能分为：
        1. 顶部导航
        2. 中间页面
        3. 底部导航
        4. 底部foot
        
        识别 2. 中间页面，返回准确的 CSS 选择器
        
        网页URL: {url}
        HTML结构:
        {simplified_html}
        
        只返回一个CSS选择器，不要有任何解释。
        """
        
        # 调用OpenAI API
        response = self.openAiClient.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[
                {"role": "system", "content": "你是一个专业的网页分析工具，能够准确识别网页的指定内容区域。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        # 获取返回的选择器
        selector = response.choices[0].message.content.strip()
        api_logger.info(f"OpenAI识别的主要内容选择器: {selector}")
        
        # 使用选择器查找元素
        try:
            element = soup.select_one(selector)    
            return element
        except Exception as e:
            api_logger.warning(f"使用OpenAI返回的选择器查找元素失败: {e}")
            
        # 如果无法找到元素，返回None
        return None
    
    def _simplify_html_structure(self, soup, isSaveHtml=False):
        """
        获取简化的HTML结构，去掉图片、视频等元素，用于发送给OpenAI
        同时保存到本地文件以便查看
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            简化后的HTML内容字符串
        """
        # 创建一个新的BeautifulSoup对象，避免修改原始对象
        soup_copy = BeautifulSoup(str(soup), 'html.parser')
        
        # 移除所有图片元素
        for img in soup_copy.find_all('img'):
            img.decompose()
        
        # 移除所有视频元素
        for video in soup_copy.find_all('video'):
            video.decompose()
        
        # 移除所有iframe元素（通常用于嵌入视频）
        for iframe in soup_copy.find_all('iframe'):
            iframe.decompose()
            
        # 移除所有embed元素（用于嵌入多媒体内容）
        for embed in soup_copy.find_all('embed'):
            embed.decompose()
            
        # 移除所有object元素（用于嵌入多媒体内容）
        for obj in soup_copy.find_all('object'):
            obj.decompose()
            
        # 移除所有audio元素
        for audio in soup_copy.find_all('audio'):
            audio.decompose()
            
        # 移除所有canvas元素
        for canvas in soup_copy.find_all('canvas'):
            canvas.decompose()
            
        # 移除所有svg元素
        for svg in soup_copy.find_all('svg'):
            svg.decompose()
        
        # 获取简化后的HTML内容
        html_str = str(soup_copy)
        
        # 保存HTML到本地文件
        try:
            # 创建保存目录
            if isSaveHtml:
                os.makedirs(HTML_CACHE_DIR, exist_ok=True)
                # 使用URL的哈希值和时间戳创建唯一文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{HTML_CACHE_DIR}/{timestamp}.html"
                
                # 写入文件
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(html_str)
                    
                api_logger.info(f"已保存HTML到文件: {filename}")
        except Exception as e:
            api_logger.error(f"保存HTML到本地文件失败: {e}")
        
        # 如果内容过长，可以进行截断以适应API限制
        if len(html_str) > 16000:  # 限制长度，避免超出OpenAI的token限制
            html_str = html_str[:16000] + "..."
            
        return html_str
        
    

def main():
    global is_task_running
    
    # 检查任务是否已在运行
    if is_task_running:
        api_logger.warning("上一个爬虫任务还在运行中，跳过本次执行")
        return
    
    # 获取锁并设置运行标志
    with task_lock:
        is_task_running = True
    
    try:
        api_logger.info(f"开始执行爬虫任务，时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        max_pages = 1000
        delay = 1.0
        timeout = 30

        # 获取所有有网址的学院
        colleges = UniversityCollege.get_all(db_session)
        api_logger.info(f"获取到 {len(colleges)} 个有网址的学院")
        # 遍历所有学院
        for college in colleges:
            if not college.website:
                api_logger.error(f"{college.university_name}:{college.name} 没有网址，跳过")
                continue
            if college.is_crawl:
                api_logger.info(f"{college.university_name}:{college.name} 已爬取过，跳过")
                continue
                
            api_logger.info(f"开始爬取: {college.university_name}:{college.name}, URL: {college.website}")
            
            # 创建爬虫实例
            crawler = CollegeWebCrawler(
                max_pages=max_pages,
                delay=delay,
                timeout=timeout
            )
            
            # 设置当前学院ID
            crawler.college = college
            
            # 开始爬取
            try:
                crawler.get_all_pages(college.website)
                api_logger.info(f"完成爬取: {college.university_name}:{college.name}")
                college.is_crawl = True
                UniversityCollege.save(db_session, college)
                
            except Exception as e:
                api_logger.error(f"爬取 {college.university_name}:{college.name} 出错: {e}")
            
            # 等待一段时间再爬取下一个学院，避免请求过于频繁
            time.sleep(5)
        
        api_logger.info("所有学院爬取完成")
        api_logger.info(f"爬虫任务完成，时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        api_logger.error(f"爬虫任务执行出错: {str(e)}")
    finally:
        # 无论任务是否成功完成，都要重置运行标志
        with task_lock:
            is_task_running = False

def testUrl():
    url = "https://cs.pku.edu.cn/info/1008/1090.htm"
    max_pages = 1000
    delay = 1.0
    timeout = 30
    crawler = CollegeWebCrawler(
        max_pages=max_pages,
        delay=delay,
        timeout=timeout
    )
    crawler.get_all_pages(url)

if __name__ == "__main__":
    # 立即执行一次
    main()
    
    # 设置每小时执行一次
    schedule.every().hour.do(main)
    
    api_logger.info("已设置每小时定时任务，程序将持续运行...")
    # 持续运行，等待定时任务
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次是否有待执行的任务


    