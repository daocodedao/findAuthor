from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, desc, Boolean, func
from sqlalchemy.orm import Session, relationship
from model.database import Base
from utils.logger_settings import api_logger

class PaperAuthor(Base):
    """论文作者模型类 - SQLAlchemy ORM"""
    __tablename__ = 'paper_authors'
    
    id = Column(Integer, primary_key=True)
    paper_id = Column(String(255), nullable=False)
    author_name = Column(String(255), nullable=False)
    position = Column(String(255))
    affiliation = Column(String(500), comment='单位')
    email = Column(String(255))
    country = Column(String(255))
    nsfc = Column(Boolean, default=False, comment='国家自然科学基金是否资助')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    
    def __init__(
        self,
        paper_id: str,
        author_name: str,
        position: str = "",
        affiliation: str = "",
        nsfc: bool = False,
        email: str = "",
        country: str = "",
        id: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.paper_id = paper_id
        self.author_name = author_name
        self.position = position
        self.affiliation = affiliation
        self.nsfc = nsfc
        self.email = email
        self.country = country
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaperAuthor':
        """从字典创建作者对象"""
        return cls(
            id=data.get("id"),
            paper_id=data.get("paper_id", ""),
            author_name=data.get("姓名", "") or data.get("author_name", ""),
            position=data.get("位置", "") or data.get("position", ""),
            affiliation=data.get("单位", "") or data.get("affiliation", ""),
            nsfc = data.get("国家自然科学基金(nsfc)是否资助", False) or data.get("nsfc", False),
            email=data.get("邮箱", "") or data.get("email", ""),
            country=data.get("国家", "") or data.get("country", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "paper_id": self.paper_id,
            "姓名": self.author_name,
            "位置": self.position,
            "单位": self.affiliation,
            "国家自然科学基金(nsfc)是否资助": self.nsfc,
            "邮箱": self.email,
            "国家": self.country,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def to_db_dict(self) -> Dict[str, Any]:
        """转换为数据库字典格式"""
        result = {
            "paper_id": self.paper_id,
            "author_name": self.author_name,
            "position": self.position,
            "affiliation": self.affiliation,
            "nsfc": self.nsfc,  # 确保这个字段被正确地转换为布尔值
            "email": self.email,
            "country": self.country
        }
        if self.id:
            result["id"] = self.id
        return result
    
    # 数据库操作方法
    @staticmethod
    def save(session: Session, author: 'PaperAuthor') -> bool:
        """将作者信息保存到数据库"""
        try:
            # 检查是否已存在
            existing_author = session.query(PaperAuthor).filter(
                PaperAuthor.paper_id == author.paper_id,
                PaperAuthor.author_name == author.author_name
            ).first()
            
            if existing_author:
                # 更新现有记录
                existing_author.position = author.position
                existing_author.affiliation = author.affiliation
                existing_author.nsfc = author.nsfc
                existing_author.email = author.email
                existing_author.country = author.country
                existing_author.updated_at = datetime.now()
            else:
                # 添加新记录
                session.add(author)
            
            session.commit()
            return True
            
        except Exception as e:
            api_logger.error(f"保存作者信息到数据库失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def get_by_paper_id(session: Session, paper_id: str) -> List['PaperAuthor']:
        """获取论文的所有作者"""
        try:
            # 查询作者
            authors = session.query(PaperAuthor).filter(PaperAuthor.paper_id == paper_id).all()
            return authors
            
        except Exception as e:
            api_logger.error(f"获取论文作者失败: {e}")
            return []
    
    @staticmethod
    def get_by_country(session: Session, country: str) -> List[Dict[str, Any]]:
        """根据国家获取作者"""
        try:
            from model.paper import Paper
            
            # 使用SQLAlchemy的like查询
            results = session.query(
                PaperAuthor, Paper.title, Paper.publish_date
            ).join(
                Paper, PaperAuthor.paper_id == Paper.paper_id
            ).filter(
                PaperAuthor.country.like(f"%{country}%")
            ).order_by(
                desc(Paper.publish_date)
            ).all()
            
            # 转换为字典列表
            author_list = []
            for author, title, publish_date in results:
                author_dict = {
                    "id": author.id,
                    "paper_id": author.paper_id,
                    "author_name": author.author_name,
                    "position": author.position,
                    "affiliation": author.affiliation,
                    "nsfc": author.nsfc,  # 确保这个字段被正确地转换为布尔值
                    "email": author.email,
                    "country": author.country,
                    "title": title,
                    "publish_date": publish_date
                }
                author_list.append(author_dict)
                
            return author_list
            
        except Exception as e:
            api_logger.error(f"根据国家获取作者失败: {e}")
            return []
    
    @staticmethod
    def save_multiple(session: Session, authors: List['PaperAuthor']) -> bool:
        """批量保存多个作者信息"""
        try:
            for author in authors:
                if not PaperAuthor.save(session, author):
                    return False
            return True
        except Exception as e:
            api_logger.error(f"批量保存作者信息失败: {e}")
            session.rollback()
            return False