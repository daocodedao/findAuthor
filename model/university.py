
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import Session
from model.database import Base
from utils.logger_settings import api_logger

class ChineseUniversity(Base):
    """中国大学模型类 - SQLAlchemy ORM"""
    __tablename__ = 'chinese_universities'
    
    id = Column(Integer, primary_key=True)
    name_cn = Column(String(255), nullable=False, unique=True)
    name_en = Column(String(255))
    website = Column(String(255))
    city = Column(String(100))
    is_985 = Column(Boolean, default=False)
    is_211 = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __init__(
        self,
        name_cn: str,
        name_en: str = "",
        website: str = "",
        city: str = "",
        is_985: bool = False,
        is_211: bool = False,
        id: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.name_cn = name_cn
        self.name_en = name_en
        self.website = website
        self.city = city
        self.is_985 = is_985
        self.is_211 = is_211
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChineseUniversity':
        """从字典创建大学对象"""
        return cls(
            id=data.get("id"),
            name_cn=data.get("name_cn", ""),
            name_en=data.get("name_en", ""),
            website=data.get("website", ""),
            city=data.get("city", ""),
            is_985=data.get("is_985", False),
            is_211=data.get("is_211", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name_cn": self.name_cn,
            "name_en": self.name_en,
            "website": self.website,
            "city": self.city,
            "is_985": self.is_985,
            "is_211": self.is_211,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    # 数据库操作方法
    @staticmethod
    def save(session: Session, university: 'ChineseUniversity') -> bool:
        """将大学信息保存到数据库"""
        try:
            # 检查是否已存在
            existing_university = session.query(ChineseUniversity).filter(
                ChineseUniversity.name_cn == university.name_cn
            ).first()
            
            if existing_university:
                # 更新现有记录
                existing_university.name_en = university.name_en
                existing_university.website = university.website
                existing_university.city = university.city
                existing_university.is_985 = university.is_985
                existing_university.is_211 = university.is_211
                existing_university.updated_at = datetime.now()
            else:
                # 添加新记录
                session.add(university)
            
            session.commit()
            return True
            
        except Exception as e:
            api_logger.error(f"保存大学信息到数据库失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def save_multiple(session: Session, universities: List['ChineseUniversity']) -> bool:
        """批量保存多个大学信息"""
        try:
            for university in universities:
                if not ChineseUniversity.save(session, university):
                    return False
            return True
        except Exception as e:
            api_logger.error(f"批量保存大学信息失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def get_all(session: Session) -> List['ChineseUniversity']:
        """获取所有大学信息"""
        try:
            # 查询所有大学
            universities = session.query(ChineseUniversity).all()
            return universities
            
        except Exception as e:
            api_logger.error(f"获取大学信息失败: {e}")
            return []