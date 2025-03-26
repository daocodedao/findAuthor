# 在文件顶部导入 SQLAlchemy 相关模块
from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker, scoped_session
import json
from datetime import datetime
from model.paper import Paper
from model.paperAuthor import PaperAuthor
from model.university import ChineseUniversity
from utils.logger_settings import api_logger

class DBManager:
    def __init__(self, db_config=None):
        # # 默认数据库配置
        # self.db_config = db_config or {
        #     'host': 'localhost',
        #     'user': 'root',
        #     'password': 'iShehui2021!',
        #     'database': 'author_marketing'
        # }
        
        self.db_config = db_config or {
            'host': '192.168.21.88',
            'user': 'root',
            'password': 'iShehui2021!',
            'database': 'author_marketing'
        }
        
        # 创建数据库连接URL
        db_url = f"mysql+mysqlconnector://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}/{self.db_config['database']}"
        
        # 创建引擎
        self.engine = create_engine(db_url)
        
        # 创建会话工厂
        self.Session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=self.engine))
    
    def _get_session(self):
        """获取数据库会话"""
        return self.Session()
    
    def load_processed_papers(self, date_key="发布日期"):
        """从数据库加载已处理的论文记录"""
        processed_papers = {}
        session = self._get_session()
        
        try:
            # 使用Paper模型的静态方法获取所有论文
            papers = Paper.get_all(session)
            
            for paper in papers:
                processed_papers[paper.paper_id] = {
                    'title': paper.title,
                    date_key: paper.publish_date,
                    'processed_date': paper.processed_date.strftime('%Y-%m-%d %H:%M:%S') if paper.processed_date else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            api_logger.info(f"从数据库加载了 {len(processed_papers)} 条已处理论文记录")
        except Exception as e:
            api_logger.error(f"加载已处理论文记录失败: {e}")
        finally:
            session.close()
        
        return processed_papers
    
    def save_paper(self, paper: Paper):
        """将论文保存到数据库（不包含作者信息）"""
        session = self._get_session()
        
        try:
            # 使用Paper模型的静态方法保存论文
            result = Paper.save(session, paper)
            return result
        finally:
            session.close()
    
    def get_paper(self, paper_id: str) -> Paper:
        """根据ID从数据库获取论文（包含作者信息）"""
        session = self._get_session()
        
        try:
            # 使用Paper模型的静态方法获取论文
            paper = Paper.get_by_id(session, paper_id)
            
            if not paper:
                return None
                
            # 使用PaperAuthor模型的静态方法获取作者信息
            authors = PaperAuthor.get_by_paper_id(session, paper_id)
            
            # 设置作者信息
            paper.authors = authors
            
            return paper
            
        finally:
            session.close()
    
    def get_all_papers(self, limit=100, offset=0) -> list:
        """获取所有论文"""
        session = self._get_session()
        
        try:
            # 使用Paper模型的静态方法获取所有论文
            papers = Paper.get_all(session, limit, offset)
            
            # 为每篇论文获取作者信息
            for paper in papers:
                authors = PaperAuthor.get_by_paper_id(session, paper.paper_id)
                
            return papers
            
        finally:
            session.close()
    
    def get_last_publish_date(self):
        """从数据库中获取最后发布的日期"""
        session = self._get_session()
        
        try:
            # 使用Paper模型的静态方法获取最后发布日期
            return Paper.get_last_publish_date(session)
        finally:
            session.close()
    
    def insert_author(self, author: PaperAuthor):
        """将作者信息插入到作者表中"""
        session = self._get_session()
        
        try:
            # 使用PaperAuthor模型的静态方法保存作者
            return PaperAuthor.save(session, author)
        finally:
            session.close()
    
    def save_paper_with_authors(self, paper: Paper):
        """将论文和作者信息保存到数据库"""
        session = self._get_session()
        
        try:
            # 先保存论文基本信息
            if not Paper.save(session, paper):
                return False
                
            # 然后保存每个作者信息
            # authors = []
            # for author_data in paper.author_info:
            #     # 创建 PaperAuthor 对象
            #     author = PaperAuthor.from_dict({
            #         "paper_id": paper.paper_id,
            #         **author_data
            #     })
            #     authors.append(author)
            
            # 批量保存作者信息
            return PaperAuthor.save_multiple(session, paper.authors)
        finally:
            session.close()
    
    def get_paper_authors(self, paper_id):
        """获取论文的所有作者"""
        session = self._get_session()
        
        try:
            # 使用PaperAuthor模型的静态方法获取作者
            authors = PaperAuthor.get_by_paper_id(session, paper_id)
            return authors
        finally:
            session.close()
    
    def get_authors_by_country(self, country):
        """根据国家获取作者"""
        session = self._get_session()
        
        try:
            # 使用PaperAuthor模型的静态方法获取作者
            return PaperAuthor.get_by_country(session, country)
        finally:
            session.close()
    
    def insert_universities_to_db(self, universities):
        """将大学信息插入到数据库"""
        session = self._get_session()
        
        try:
            # 将字典列表转换为ChineseUniversity对象列表
            university_objects = [ChineseUniversity.from_dict(uni) for uni in universities]
            
            # 使用ChineseUniversity模型的静态方法批量保存
            result = ChineseUniversity.save_multiple(session, university_objects, self.engine)
            return result
        finally:
            session.close()
    
    def get_universities(self):
        """获取所有大学信息"""
        session = self._get_session()
        
        try:
            # 使用ChineseUniversity模型的静态方法获取所有大学
            universities = ChineseUniversity.get_all(session, self.engine)
            return [uni.to_dict() for uni in universities]
        finally:
            session.close()
    
    def close(self):
        """关闭数据库连接"""
        self.Session.remove()