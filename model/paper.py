
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, DateTime, Boolean, func, desc, Text
from sqlalchemy.orm import Session
from model.database import Base
import json
from utils.logger_settings import api_logger
from model.paperAuthor import PaperAuthor

class Paper(Base):
    """论文模型类 - SQLAlchemy ORM"""
    __tablename__ = 'arxiv_papers'
    
    paper_id = Column(String(255), primary_key=True)
    title = Column(String(500), nullable=False)
    chinese_title = Column(String(500))
    publish_date = Column(DateTime)
    pdf_link = Column(String(500))
    web_link = Column(String(500))
    # Store categories as JSON string instead of ARRAY
    categories = Column(Text)
    research_direction = Column(String(500))
    main_content = Column(Text)
    has_chinese_author = Column(Boolean, default=False)
    has_chinese_email = Column(Boolean, default=False)
    nsfc = Column(Boolean, default=False, comment='国家自然科学基金是否资助')
    processed_date = Column(DateTime, default=datetime.now)
    
    authors:List[PaperAuthor] = []
    
    def __init__(
        self,
        paper_id: str,
        title: str,
        chinese_title: str = "",
        publish_date: str = "",
        pdf_link: str = "",
        web_link: str = "",
        categories: List[str] = None,
        research_direction: str = "",
        main_content: str = "",
        has_chinese_author: bool = False,
        has_chinese_email: bool = False,
        nsfc: bool = False,
        processed_date: Optional[datetime] = None
    ):
        self.paper_id = paper_id
        self.title = title
        self.chinese_title = chinese_title
        
        # 处理日期格式
        if isinstance(publish_date, str) and publish_date:
            try:
                self.publish_date = datetime.strptime(publish_date, "%Y-%m-%d")
            except ValueError:
                self.publish_date = datetime.now()
        elif isinstance(publish_date, datetime):
            self.publish_date = publish_date
        else:
            self.publish_date = datetime.now()
            
        self.pdf_link = pdf_link
        self.web_link = web_link
        # Store categories as JSON string
        self.set_categories(categories or [])
        self.research_direction = research_direction
        self.main_content = main_content
        self.has_chinese_author = has_chinese_author
        self.has_chinese_email = has_chinese_email
        self.nsfc = nsfc
        self.processed_date = processed_date or datetime.now()
    
    def set_categories(self, categories_list: List[str]):
        """Convert categories list to JSON string for storage"""
        self.categories = json.dumps(categories_list)
    
    def get_categories(self) -> List[str]:
        """Get categories as a list from stored JSON string"""
        if not self.categories:
            return []
        try:
            return json.loads(self.categories)
        except:
            return []
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Paper':
        """从字典创建论文对象"""
        paper = cls(
            paper_id=data.get("paper_id", ""),
            title=data.get("标题", "") or data.get("title", ""),
            chinese_title=data.get("中文标题", "") or data.get("chinese_title", ""),
            publish_date=data.get("发布日期", "") or data.get("publish_date", ""),
            pdf_link=data.get("PDF链接", "") or data.get("pdf_link", ""),
            web_link=data.get("网页链接", "") or data.get("web_link", ""),
            categories=data.get("分类", []) or data.get("categories", []),
            research_direction=data.get("研究方向", "") or data.get("research_direction", ""),
            main_content=data.get("主要内容", "") or data.get("main_content", ""),
            has_chinese_author=data.get("是否有中国作者", False) or data.get("has_chinese_author", False),
            has_chinese_email=data.get("是否有中国作者邮箱", False) or data.get("has_chinese_email", False),
            nsfc=data.get("国家自然科学基金(nsfc)是否资助", False) or data.get("nsfc", False),
            processed_date=data.get("processed_date")
        )
        
        # 检查是否有中国作者和中国作者邮箱
        author_info = data.get("作者信息", []) or data.get("author_info", [])
        for author in author_info:
            if "中国" in author.get("国家", "") or "China" in author.get("国家", ""):
                paper.has_chinese_author = True
                if "@" in author.get("邮箱", ""):
                    paper.has_chinese_email = True
                    break
        authors = []
        for author in author_info:
            author["paper_id"] = paper.paper_id
            authors.append(PaperAuthor.from_dict(author))
        paper.authors = authors
        return paper
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "paper_id": self.paper_id,
            "标题": self.title,
            "中文标题": self.chinese_title,
            "发布日期": self.publish_date.strftime('%Y-%m-%d') if self.publish_date else "",
            "PDF链接": self.pdf_link,
            "网页链接": self.web_link,
            "分类": self.get_categories(),
            "研究方向": self.research_direction,
            "主要内容": self.main_content,
            "是否有中国作者": self.has_chinese_author,
            "是否有中国作者邮箱": self.has_chinese_email,
            "国家自然科学基金(nsfc)是否资助": self.nsfc,
            "processed_date": self.processed_date
        }
    
    # 数据库操作方法
    @staticmethod
    def save(session: Session, paper: 'Paper') -> bool:
        """将论文保存到数据库"""
        try:
            # 检查是否已存在
            existing_paper = session.query(Paper).filter(Paper.paper_id == paper.paper_id).first()
            
            if existing_paper:
                # 更新现有记录
                existing_paper.title = paper.title
                existing_paper.chinese_title = paper.chinese_title
                existing_paper.publish_date = paper.publish_date
                existing_paper.pdf_link = paper.pdf_link
                existing_paper.web_link = paper.web_link
                existing_paper.categories = paper.categories
                existing_paper.research_direction = paper.research_direction
                existing_paper.main_content = paper.main_content
                existing_paper.has_chinese_author = paper.has_chinese_author
                existing_paper.has_chinese_email = paper.has_chinese_email
                existing_paper.nsfc = paper.nsfc
                existing_paper.processed_date = datetime.now()
            else:
                # 添加新记录
                session.add(paper)
            
            session.commit()
            return True
            
        except Exception as e:
            api_logger.error(f"保存论文到数据库失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def get_by_id(session: Session, paper_id: str) -> Optional['Paper']:
        """根据ID从数据库获取论文"""
        try:
            # 查询论文
            paper = session.query(Paper).filter(Paper.paper_id == paper_id).first()
            return paper
            
        except Exception as e:
            api_logger.error(f"获取论文失败: {e}")
            return None
    
    @staticmethod
    def get_all(session: Session, limit=100, offset=0) -> List['Paper']:
        """获取所有论文"""
        try:
            # 查询论文，按发布日期降序排序
            papers = session.query(Paper).order_by(desc(Paper.publish_date)).limit(limit).offset(offset).all()
            return papers
            
        except Exception as e:
            api_logger.error(f"获取论文列表失败: {e}")
            return []
    
    @staticmethod
    def get_last_publish_date(session: Session) -> Optional[datetime]:
        """获取最后发布日期"""
        try:
            # 使用SQLAlchemy的func.max获取最大日期
            last_date = session.query(func.max(Paper.publish_date)).scalar()
            return last_date
            
        except Exception as e:
            api_logger.error(f"获取最后发布日期失败: {e}")
            return None