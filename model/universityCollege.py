from datetime import datetime
from typing import Optional, Dict, Any, List, ClassVar
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Session, relationship, Mapped
from model.database import Base
from utils.logger_settings import api_logger
from model.university import ChineseUniversity

class UniversityCollege(Base):
    """大学院系模型类 - SQLAlchemy ORM"""
    __tablename__ = 'universities_college'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    university_id = Column(Integer, ForeignKey('chinese_universities.id'), nullable=False, comment='chinese_universities id')
    college_name = Column(String(100), nullable=False, comment='学院名')
    college_url = Column(String(255), comment='学院官网')
    is_crawl = Column(Integer, default=0, comment='是否爬取过')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 使用 ClassVar 明确标注这不是数据库字段
    university_name: ClassVar[Optional[str]] = None
    
    # 关系
    university = relationship("ChineseUniversity", backref="colleges")
    
    def __init__(
        self,
        university_id: int,
        college_name: str,
        college_url: str = None,
        id: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.university_id = university_id
        self.college_name = college_name
        self.college_url = college_url
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.is_crawl = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UniversityCollege':
        """从字典创建院系对象"""
        return cls(
            id=data.get("id"),
            university_id=data.get("university_id"),
            college_name=data.get("college_name"),
            college_url=data.get("college_url"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "university_id": self.university_id,
            "college_name": self.college_name,
            "college_url": self.college_url,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    # 数据库操作方法
    @staticmethod
    def save(session: Session, college: 'UniversityCollege') -> bool:
        """将院系信息保存到数据库"""
        try:
            # 检查是否已存在
            existing_college = None
            if college.id:
                existing_college = session.query(UniversityCollege).filter(
                    UniversityCollege.id == college.id
                ).first()
            
            if not existing_college and college.university_id and college.college_name:
                existing_college = session.query(UniversityCollege).filter(
                    UniversityCollege.university_id == college.university_id,
                    UniversityCollege.college_name == college.college_name
                ).first()
            
            if existing_college:
                # 更新现有记录
                existing_college.college_url = college.college_url
                existing_college.updated_at = datetime.now()
            else:
                # 添加新记录
                session.add(college)
            
            session.commit()
            return True
            
        except Exception as e:
            api_logger.error(f"保存院系信息到数据库失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def save_multiple(session: Session, colleges: List['UniversityCollege']) -> bool:
        """批量保存多个院系信息"""
        try:
            for college in colleges:
                if not UniversityCollege.save(session, college):
                    return False
            return True
        except Exception as e:
            api_logger.error(f"批量保存院系信息失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def get_by_university(session: Session, university_id: int) -> List['UniversityCollege']:
        """获取指定大学的所有院系"""
        try:
            # 使用join连表查询，同时获取学院和大学信息
            colleges = session.query(UniversityCollege, ChineseUniversity.name_cn)\
                .join(ChineseUniversity, UniversityCollege.university_id == ChineseUniversity.id)\
                .filter(UniversityCollege.university_id == university_id)\
                .all()
            
            # 处理查询结果，设置university_name属性
            result_colleges = []
            for college_tuple in colleges:
                college = college_tuple[0]  # 学院对象
                university_name = college_tuple[1]  # 大学名称
                college.university_name = university_name
                result_colleges.append(college)
            
            return result_colleges
            
        except Exception as e:
            api_logger.error(f"获取大学院系信息失败: {e}")
            return []
    
    @staticmethod
    def get_by_id(session: Session, college_id: int) -> Optional['UniversityCollege']:
        """根据ID获取院系信息"""
        try:
            # 使用连表查询获取学院和对应大学信息
            result = session.query(UniversityCollege, ChineseUniversity.name_cn)\
                .join(ChineseUniversity, UniversityCollege.university_id == ChineseUniversity.id)\
                .filter(UniversityCollege.id == college_id)\
                .first()
            
            if result:
                college, university_name = result
                college.university_name = university_name
                return college
            return None
            
        except Exception as e:
            api_logger.error(f"根据ID获取院系信息失败: {e}")
            return None

    @staticmethod
    def search_by_name(session: Session, name: str) -> List['UniversityCollege']:
        """根据名称搜索院系"""
        try:
            # 使用连表查询获取学院和对应大学信息
            results = session.query(UniversityCollege, ChineseUniversity.name_cn)\
                .join(ChineseUniversity, UniversityCollege.university_id == ChineseUniversity.id)\
                .filter(UniversityCollege.college_name.like(f"%{name}%"))\
                .all()
            
            colleges = []
            for college, university_name in results:
                college.university_name = university_name
                colleges.append(college)
            
            return colleges
            
        except Exception as e:
            api_logger.error(f"根据名称搜索院系失败: {e}")
            return []
        
    @staticmethod
    def get_all(session: Session) -> List['UniversityCollege']:
        """获取所有院系信息"""
        try:
            # 使用连表查询获取所有学院和对应大学信息
            results = session.query(UniversityCollege, ChineseUniversity.name_cn)\
                .join(ChineseUniversity, UniversityCollege.university_id == ChineseUniversity.id)\
                .all()
            
            colleges = []
            for college, university_name in results:
                college.university_name = university_name
                colleges.append(college)
                
            return colleges
            
        except Exception as e:
            api_logger.error(f"获取所有学院信息失败: {e}")
            return []