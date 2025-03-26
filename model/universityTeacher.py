from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Session, relationship
from model.database import Base
from utils.logger_settings import api_logger

class UniversityTeacher(Base):
    """大学教师模型类 - SQLAlchemy ORM"""
    __tablename__ = 'universities_teacher'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='ID')
    university_id = Column(Integer, ForeignKey('chinese_universities.id'), nullable=False, comment='chinese_universities id')
    universities_college_id = Column(Integer, ForeignKey('universities_college.id'), nullable=False, comment='universities_college id')
    name = Column(String(255), nullable=False, comment='教师姓名')
    sex = Column(Integer, default=0, comment='性别, 0: 未知, 1: 男, 2: 女')
    email = Column(String(255), comment='电子邮箱')
    is_national_fun = Column(Boolean, default=False, comment='是否主持过国家基金项目')
    is_cs = Column(Boolean, default=False, comment='教师是否与计算机相关')
    bookname = Column(String(255), comment='著作名')
    title = Column(String(255), comment='职称')
    job_title = Column(String(255), comment='职位')
    tel = Column(String(255), comment='电话')
    research_direction = Column(Text, comment='研究方向')
    papers = Column(Text, comment='论文')
    homepage = Column(String(255), comment='个人主页')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 关系
    university = relationship("ChineseUniversity", backref="teachers")
    college = relationship("UniversityCollege", backref="teachers")
    
    def __init__(
        self,
        name: str,
        university_id: int,
        universities_college_id: int,
        sex: int = 0,
        email: str = None,
        is_national_fun: bool = False,
        is_cs: bool = False,
        bookname: str = None,
        title: str = None,
        job_title: str = None,
        tel: str = None,
        research_direction: str = None,
        papers: str = None,
        id: Optional[int] = None,
        homepage: str = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.university_id = university_id
        self.universities_college_id = universities_college_id
        self.name = name
        self.sex = sex
        self.email = email
        self.is_national_fun = is_national_fun
        self.is_cs = is_cs
        self.bookname = bookname
        self.title = title
        self.job_title = job_title
        self.tel = tel
        self.research_direction = research_direction
        self.papers = papers
        self.homepage = homepage
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UniversityTeacher':
        """从字典创建教师对象"""
        return cls(
            id=data.get("id"),
            university_id=data.get("university_id"),
            universities_college_id=data.get("universities_college_id"),
            name=data.get("name"),
            sex=data.get("sex", 0),
            email=data.get("email"),
            is_national_fun=data.get("is_national_fun", False),
            is_cs=data.get("is_cs", False),
            bookname=data.get("bookname"),
            title=data.get("title"),
            job_title=data.get("job_title"),
            tel=data.get("tel"),
            research_direction=data.get("research_direction"),
            papers=data.get("papers"),
            homepage=data.get("homepage"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "university_id": self.university_id,
            "universities_college_id": self.universities_college_id,
            "name": self.name,
            "sex": self.sex,
            "email": self.email,
            "is_national_fun": self.is_national_fun,
            "is_cs": self.is_cs,
            "bookname": self.bookname,
            "title": self.title,
            "job_title": self.job_title,
            "tel": self.tel,
            "research_direction": self.research_direction,
            "papers": self.papers,
            "homepage":self.homepage,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    # 数据库操作方法
    @staticmethod
    def save(session: Session, teacher: 'UniversityTeacher') -> bool:
        """将教师信息保存到数据库"""
        try:
            # 检查是否已存在
            existing_teacher = None
            if teacher.id:
                existing_teacher = session.query(UniversityTeacher).filter(UniversityTeacher.id == teacher.id).first()
            
            if not existing_teacher and teacher.universities_college_id and teacher.name and teacher.email:
                existing_teacher = session.query(UniversityTeacher).filter(
                    UniversityTeacher.universities_college_id == teacher.universities_college_id,
                    UniversityTeacher.name == teacher.name,
                    UniversityTeacher.email == teacher.email
                ).first()
            
            if existing_teacher:
                # 更新现有记录
                existing_teacher.university_id = teacher.university_id
                existing_teacher.sex = teacher.sex
                existing_teacher.is_national_fun = teacher.is_national_fun
                existing_teacher.is_cs = teacher.is_cs
                existing_teacher.bookname = teacher.bookname
                existing_teacher.title = teacher.title
                existing_teacher.job_title = teacher.job_title
                existing_teacher.tel = teacher.tel
                existing_teacher.research_direction = teacher.research_direction
                existing_teacher.papers = teacher.papers
                existing_teacher.homepage = teacher.homepage
                existing_teacher.updated_at = datetime.now()
            else:
                # 添加新记录
                session.add(teacher)
            
            session.commit()
            return True
            
        except Exception as e:
            api_logger.error(f"保存教师信息到数据库失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def save_multiple(session: Session, teachers: List['UniversityTeacher']) -> bool:
        """批量保存多个教师信息"""
        try:
            for teacher in teachers:
                if not UniversityTeacher.save(session, teacher):
                    return False
            return True
        except Exception as e:
            api_logger.error(f"批量保存教师信息失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def get_by_university(session: Session, university_id: int) -> List['UniversityTeacher']:
        """获取指定大学的所有教师"""
        try:
            teachers = session.query(UniversityTeacher).filter(
                UniversityTeacher.university_id == university_id
            ).all()
            return teachers
            
        except Exception as e:
            api_logger.error(f"获取大学教师信息失败: {e}")
            return []
    
    @staticmethod
    def get_by_college(session: Session, college_id: int) -> List['UniversityTeacher']:
        """获取指定学院的所有教师"""
        try:
            teachers = session.query(UniversityTeacher).filter(
                UniversityTeacher.universities_college_id == college_id
            ).all()
            return teachers
            
        except Exception as e:
            api_logger.error(f"获取学院教师信息失败: {e}")
            return []
    
    @staticmethod
    def get_cs_teachers(session: Session) -> List['UniversityTeacher']:
        """获取所有计算机相关教师"""
        try:
            teachers = session.query(UniversityTeacher).filter(
                UniversityTeacher.is_cs == True
            ).all()
            return teachers
            
        except Exception as e:
            api_logger.error(f"获取计算机相关教师信息失败: {e}")
            return []
    
    @staticmethod
    def search_by_research(session: Session, keyword: str) -> List['UniversityTeacher']:
        """根据研究方向关键词搜索教师"""
        try:
            teachers = session.query(UniversityTeacher).filter(
                UniversityTeacher.research_direction.like(f"%{keyword}%")
            ).all()
            return teachers
            
        except Exception as e:
            api_logger.error(f"根据研究方向搜索教师失败: {e}")
            return []
        
    @staticmethod
    def search_by_homepage(session: Session, keyword: str) -> List['UniversityTeacher']:
        """根据主页关键词搜索教师"""
        try:
            teachers = session.query(UniversityTeacher).filter(
                UniversityTeacher.homepage.like(f"%{keyword}%")
            ).all()
            return teachers

        except Exception as e:
            api_logger.error(f"根据主页搜索教师失败: {e}")