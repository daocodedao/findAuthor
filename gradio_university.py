# 在文件顶部导入部分添加更详细的日志记录
import gradio as gr
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from model.university import ChineseUniversity
from model.universityCollege import UniversityCollege
from model.universityTeacher import UniversityTeacher
from db_manager import DBManager
from utils.logger_settings import api_logger
# 导入所需模型
from model.paper import Paper
from model.paperAuthor import PaperAuthor
# 添加 desc 导入
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
        
# 设置更详细的日志格式
api_logger.info("启动大学信息管理系统")

db_manager = DBManager()
# db_session = db_manager._get_session()
api_logger.info("数据库会话已创建")

# 添加一个辅助函数来确保数据库会话的安全使用
def safe_db_operation(func):
    """装饰器，确保数据库操作安全执行，出错时自动回滚"""
    def wrapper(*args, **kwargs):
        session = db_manager._get_session()
        try:
            result = func(*args, **kwargs, session=session)
            return result
        except SQLAlchemyError as e:
            session.rollback()
            api_logger.error(f"数据库操作出错，已回滚: {str(e)}")
            return None
        except Exception as e:
            session.rollback()
            api_logger.error(f"操作出错，已回滚: {str(e)}")
            return None
        finally:
            session.close()
    return wrapper

def getUnivercityIdByName(uniName):
    """根据中文名称获取大学ID"""
    if uniName is None:
        api_logger.warning("getUnivercityIdByName 收到了None值大学名称")
        return None
    
    # 如果是字符串格式如 "123:北京大学"，提取ID部分
    if isinstance(uniName, str) and ":" in uniName:
        university_id = int(uniName.split(":")[0])
    elif isinstance(uniName, list):
        university_id = int(uniName[0].split(":")[0])
    else:
        university_id = int(uniName)
    
    return university_id

# 辅助函数
def get_all_universities() -> List[ChineseUniversity]:
    """获取所有大学"""
    universities = ChineseUniversity.get_all(db_manager._get_session())
    api_logger.info(f"获取到 {len(universities)} 所大学")
    uniNames = []
    for uni in universities:
        # api_logger.info(f"大学信息： {uni}")
        uniNames.append(f"{uni.id}:{uni.name_cn}")
        
    return universities, uniNames

# 初始化下拉框选项
allUniversities, allUniNames = get_all_universities()

def get_university_by_id(university_id: int) -> Optional[ChineseUniversity]:
    """根据ID获取大学"""
    for university in allUniversities:
        if university.id == university_id:
            api_logger.info(f"获取到大学： {university}")
            return university
    return None

def get_colleges_by_university(university_id: int) -> List[UniversityCollege]:
    """获取指定大学的所有学院"""
    return UniversityCollege.get_by_university(db_manager._get_session(), university_id)

def get_teachers_by_college(college_id: int) -> List[UniversityTeacher]:
    """获取指定学院的所有教师"""
    return UniversityTeacher.get_by_college(db_manager._get_session(), college_id)

def get_teachers_by_university(university_id: int) -> List[UniversityTeacher]:
    """获取指定学院的所有教师"""
    return UniversityTeacher.get_by_university(db_manager._get_session(), university_id)

def university_to_df(universities: List[ChineseUniversity]) -> pd.DataFrame:
    """将大学列表转换为DataFrame"""
    data = []
    # 添加对None值的处理
    for uni in universities:
        if uni is None:
            api_logger.warning("university_to_df 收到了None值大学对象")
            continue
        data.append({
            "ID": uni.id,
            "中文名称": uni.name_cn,
            "官网": uni.website,
            "城市": uni.city,
            "985": "是" if uni.is_985 else "否",
            "211": "是" if uni.is_211 else "否"
        })
    # 如果没有有效数据，返回空DataFrame
    if not data:
        api_logger.warning("university_to_df 没有有效数据，返回空DataFrame")
        return pd.DataFrame(columns=["ID", "中文名称", "官网", "城市", "985", "211"])
    return pd.DataFrame(data)

def college_to_df(colleges: List[UniversityCollege]) -> pd.DataFrame:
    """将学院列表转换为DataFrame"""
    data = []
    for college in colleges:
        data.append({
            "ID": college.id,
            "学院名称": college.name,
            "学院官网": college.website or "",
            "抓取过": college.is_crawl
        })
    return pd.DataFrame(data)

def teacher_to_df(teachers: List[UniversityTeacher]) -> pd.DataFrame:
    """将教师列表转换为DataFrame"""
    data = []
    for teacher in teachers:
        sex_map = {0: "未知", 1: "男", 2: "女"}
        data.append({
            "ID": teacher.id,
            "姓名": teacher.name,
            "性别": sex_map.get(teacher.sex, "未知"),
            "邮箱": teacher.email or "",
            "个人主页": teacher.homepage or "",
            "主持国家基金": "是" if teacher.is_national_fun else "否",
            "计算机相关": "是" if teacher.is_cs else "否",
            "出过专著": "是" if teacher.is_pub_book else "否",
            "科学出过专著": "是" if teacher.is_pub_book_sciencep else "否",
            "著作名": teacher.bookname or "",
            "科学出版的著作": teacher.sciencep_bookname or "",
            "职称": teacher.title or "",
            "职位": teacher.job_title or "",
            "电话": teacher.tel or "",
            "研究方向": teacher.research_direction or "",
        })
    return pd.DataFrame(data)

def search_university(search_text: str):
    """搜索大学"""
    api_logger.info(f"搜索大学，关键词: '{search_text}'")
    if search_text:
        filtered_universities = [uni for uni in allUniversities if search_text.lower() in uni.name_cn.lower()]
        api_logger.info(f"搜索结果: 找到 {len(filtered_universities)} 所大学")
    else:
        filtered_universities = allUniversities
        api_logger.info(f"搜索结果: 显示所有 {len(filtered_universities)} 所大学")
    
    # 使用简单的字典格式
    choices = []
    # values = []
    for uni in filtered_universities:
        choices.append(f"{uni.id}:{uni.name_cn}")
        # values.append(uni.id)
        # choices[f"{uni.id}: {uni.name_cn}"] = uni.id
    
    api_logger.info(f"生成选项: {choices}")
    return choices

def load_university_info(university_id: str):
    """加载大学信息"""
    api_logger.info(f"加载大学信息，ID: {university_id}")
    if not university_id:
        api_logger.warning("未提供大学ID，无法加载大学信息")
        return None, None
    
    # 尝试从字符串中提取ID
    try:
        university_id = getUnivercityIdByName(university_id)
    except (ValueError, TypeError) as e:
        api_logger.error(f"无法解析大学ID: {university_id}, 错误: {str(e)}")
        return None, None
    
    university = get_university_by_id(university_id)
    if not university:
        api_logger.warning(f"未找到ID为 {university_id} 的大学")
        return None, None
    
    # 获取大学详细信息
    uni_df = university_to_df([university])
    
    # 获取该大学的所有学院
    colleges = get_colleges_by_university(university_id)
    api_logger.info(f"获取到大学 {university.name_cn} 的 {len(colleges)} 个学院")
    college_df = college_to_df(colleges)
    
    # 获取教师
    teachers = get_teachers_by_university(university_id)
    api_logger.info(f"获取到学院 {university_id} 的 {len(teachers)} 名教师")
    teacher_df = teacher_to_df(teachers)
    
    return uni_df, college_df, teacher_df

def load_college_teachers(college_id: int) -> List[UniversityTeacher]:
    """加载学院教师"""
    api_logger.info(f"加载学院教师，学院ID: {college_id}")
    if not college_id:
        api_logger.warning("未提供学院ID，无法加载教师信息")
        return None
    
    teachers = get_teachers_by_college(college_id)
    api_logger.info(f"获取到学院ID {college_id} 的 {len(teachers)} 名教师")
    teacher_df = teacher_to_df(teachers)
    
    return teacher_df

def edit_teacher(teacher_id: int, name: str, sex: int, email: str, is_national_fun: bool, 
                is_cs: bool, bookname: str, title: str, job_title: str, tel: str, 
                research_direction: str, papers: str):
    """编辑教师信息"""
    if not teacher_id:
        return "请先选择教师", None
    
    session = None
    try:
        session = db_manager._get_session()
        teacher = session.query(UniversityTeacher).filter(UniversityTeacher.id == teacher_id).first()
        if not teacher:
            return "未找到该教师", None
        
        # 更新教师信息
        teacher.name = name
        teacher.sex = sex
        teacher.email = email
        teacher.is_national_fun = is_national_fun
        teacher.is_cs = is_cs
        teacher.bookname = bookname
        teacher.title = title
        teacher.job_title = job_title
        teacher.tel = tel
        teacher.research_direction = research_direction
        teacher.papers = papers
        
        session.commit()
        return "教师信息更新成功", teacher_to_df([teacher])
    except SQLAlchemyError as e:
        if session:
            session.rollback()
        api_logger.error(f"数据库更新出错，已回滚: {str(e)}")
        return f"更新失败: {str(e)}", None
    except Exception as e:
        if session:
            session.rollback()
        api_logger.error(f"更新教师信息时出错，已回滚: {str(e)}")
        return f"更新失败: {str(e)}", None
    finally:
        if session:
            session.close()

def delete_teacher(teacher_id: int):
    """删除教师"""
    if not teacher_id:
        return "请先选择教师", None
    
    session = None
    try:
        session = db_manager._get_session()
        teacher = session.query(UniversityTeacher).filter(UniversityTeacher.id == teacher_id).first()
        if teacher:
            session.delete(teacher)
            session.commit()
            return "教师删除成功", None
        else:
            return "未找到该教师", None
    except SQLAlchemyError as e:
        if session:
            session.rollback()
        api_logger.error(f"数据库删除出错，已回滚: {str(e)}")
        return f"删除失败: {str(e)}", None
    except Exception as e:
        if session:
            session.rollback()
        api_logger.error(f"删除教师时出错，已回滚: {str(e)}")
        return f"删除失败: {str(e)}", None

def add_college(university_id: int, name: str, website: str, add_college_info:pd.DataFrame):
    """添加或更新学院"""
    if not university_id:
        return "请先选择大学", name, website, add_college_info
    
    if not name:
        return "学院名称不能为空", name, website, add_college_info
    
    if not website:
        return "学院官网不能为空", name, website, add_college_info
    
    session = None
    try:
        session = db_manager._get_session()
        university_id = getUnivercityIdByName(university_id)
        
        # 检查是否是更新现有学院
        existing_college = None
        for _, row in add_college_info.iterrows():
            if row["学院名称"] == name:
                existing_college = session.query(UniversityCollege).filter(UniversityCollege.id == row["ID"]).first()
                break
        
        if existing_college:
            # 更新现有学院
            api_logger.info(f"更新学院: ID={existing_college.id}, 名称={name}, 网站={website}")
            existing_college.name = name
            existing_college.website = website
            retMgs = f"学院 '{name}' 更新成功"
        else:
            # 创建新学院
            api_logger.info(f"创建新学院: 大学ID={university_id}, 名称={name}, 网站={website}")
            new_college = UniversityCollege(
                university_id=university_id,
                name=name,
                website=website
            )
            session.add(new_college)
            retMgs = f"学院 '{name}' 添加成功"
        
        # 保存到数据库
        session.commit()
        api_logger.info("数据库事务已提交")
        
        # 重新获取学院列表以确保显示最新数据
        colleges = get_colleges_by_university(university_id)
        api_logger.info(f"获取到 {len(colleges)} 个学院")
        college_df = college_to_df(colleges)
        
        # 确保返回的DataFrame是新的对象，而不是原来的引用
        return retMgs, "", "", college_df
    except SQLAlchemyError as e:
        if session:
            session.rollback()
        api_logger.error(f"数据库操作出错，已回滚: {str(e)}")
        return f"学院操作失败: {str(e)}", name, website, add_college_info
    except Exception as e:
        if session:
            session.rollback()
        api_logger.error(f"操作学院时出错，已回滚: {str(e)}")
        return f"学院操作失败: {str(e)}", name, website, add_college_info
    finally:
        if session:
            session.close()

# 创建Gradio界面
# 在现有的函数下添加新的搜索教师函数
# 修改搜索教师函数
def search_teachers(is_national_fun=None, university_name=None, city=None, is_pub_book=None, is_pub_book_sciencep=None):
    """根据条件搜索教师"""
    api_logger.info(f"搜索教师，条件: 国家基金项目:{is_national_fun}, 大学:{university_name}, 城市:{city}, "
                   f"出过专著:{is_pub_book}, 科学出过专著:{is_pub_book_sciencep}")
    
    # 获取新的会话
    session = None
    try:
        session = db_manager._get_session()
        
        # 修改查询，同时获取大学和学院信息
        query = session.query(
            UniversityTeacher,
            ChineseUniversity.name_cn.label('university_name'),
            ChineseUniversity.website.label('university_website'),
            ChineseUniversity.city.label('city'),
            UniversityCollege.name.label('name')
        ).join(
            ChineseUniversity, UniversityTeacher.university_id == ChineseUniversity.id
        ).outerjoin(
            # 修改连接条件，使用外键列而不是关系属性
            UniversityCollege, UniversityTeacher.college_id == UniversityCollege.id
        )
        
        # 应用筛选条件
        if is_national_fun is not None and is_national_fun != "全部":
            is_national_fun_bool = (is_national_fun == "是")
            query = query.filter(UniversityTeacher.is_national_fun == is_national_fun_bool)
        
        # 添加新的筛选条件：出过专著
        if is_pub_book is not None and is_pub_book != "全部":
            is_pub_book_bool = (is_pub_book == "是")
            query = query.filter(UniversityTeacher.is_pub_book == is_pub_book_bool)
            
        # 添加新的筛选条件：科学出过专著
        if is_pub_book_sciencep is not None and is_pub_book_sciencep != "全部":
            is_pub_book_sciencep_bool = (is_pub_book_sciencep == "是")
            query = query.filter(UniversityTeacher.is_pub_book_sciencep == is_pub_book_sciencep_bool)
        
        # 如果指定了大学名称，需要先获取大学ID
        if university_name and university_name != "全部":
            try:
                # 处理格式为 "123:北京大学" 的情况
                if ":" in university_name:
                    university_id = int(university_name.split(":")[0])
                else:
                    # 通过名称查找大学
                    university = next((u for u in allUniversities if university_name.lower() in u.name_cn.lower()), None)
                    university_id = university.id if university else None
                
                if university_id:
                    query = query.filter(UniversityTeacher.university_id == university_id)
            except Exception as e:
                api_logger.error(f"处理大学名称时出错: {str(e)}")
        
        # 如果指定了城市，需要通过大学表关联查询
        if city:
            query = query.filter(ChineseUniversity.city.like(f"%{city}%"))
        
        # 执行查询
        results = query.all()
        api_logger.info(f"搜索结果: 找到 {len(results)} 名教师")
        
        # 转换为DataFrame，添加额外信息
        data = []
        sex_map = {0: "未知", 1: "男", 2: "女"}
        for result in results:
            teacher = result[0]  # 教师对象
            university_name = result[1]  # 大学名称
            university_website = result[2]  # 大学网址
            city = result[3]  # 城市
            name = result[4] or "未知"  # 学院名称，可能为None
            
            data.append({
                "ID": teacher.id,
                "姓名": teacher.name,
                "性别": sex_map.get(teacher.sex, "未知"),
                "城市": city,
                "大学名称": university_name,
                "出过专著": "是" if teacher.is_pub_book else "否",
                "科学出过专著": "是" if teacher.is_pub_book_sciencep else "否",
                "科学出版的著作": teacher.sciencep_bookname or "",
                "大学网址": university_website,
                "学院名称": name,
                "邮箱": teacher.email or "",
                "个人主页": teacher.homepage or "",
                "主持国家基金": "是" if teacher.is_national_fun else "否",
                "计算机相关": "是" if teacher.is_cs else "否",
                "著作名": teacher.bookname or "",
                "职称": teacher.title or "",
                "职位": teacher.job_title or "",
                "电话": teacher.tel or "",
                "研究方向": teacher.research_direction or "",
            })
        
        # 关闭会话
        session.close()
        
        return pd.DataFrame(data)
    
    except SQLAlchemyError as e:
        if session:
            session.rollback()
        api_logger.error(f"数据库查询出错，已回滚: {str(e)}")
        return pd.DataFrame(columns=["ID", "姓名", "性别", "城市", "大学名称", "大学网址", "学院名称", 
                                    "邮箱", "个人主页", "主持国家基金", "计算机相关", 
                                    "著作名", "职称", "职位", "电话", "研究方向"])
    except Exception as e:
        if session:
            session.rollback()
        api_logger.error(f"搜索教师时出错，已回滚: {str(e)}")
        return pd.DataFrame(columns=["ID", "姓名", "性别", "城市", "大学名称", "大学网址", "学院名称", 
                                    "邮箱", "个人主页", "主持国家基金", "计算机相关", 
                                    "著作名", "职称", "职位", "电话", "研究方向"])
    finally:
        if session:
            session.close()

def search_paper_authors(is_china=True, author_positions=None, has_email=False, 
                         affiliation=None, paper_title=None, research_direction=None):
    """搜索论文作者"""
    api_logger.info(f"搜索论文作者，条件: 中国作者:{is_china}, 作者类型:{author_positions}, "
                   f"有邮箱:{has_email}, 机构:{affiliation}, 标题:{paper_title}, 研究方向:{research_direction}")
    
    # 获取新的会话
    session = None
    try:
        session = db_manager._get_session()
        
        # 构建基本查询
        query = session.query(
            PaperAuthor,
            Paper.title,
            Paper.chinese_title,
            Paper.research_direction,
            Paper.publish_date
        ).join(
            Paper, PaperAuthor.paper_id == Paper.paper_id
        )
        
        # 应用筛选条件
        # 1. 中国作者
        if is_china:
            query = query.filter(
                (PaperAuthor.country.like('%中国%')) | 
                (PaperAuthor.country.like('%China%')) |
                (PaperAuthor.country.like('%CN%'))
            )
        
        # 2. 作者类型
        if author_positions and len(author_positions) > 0:
            position_filters = []
            if "通讯作者" in author_positions:
                position_filters.append(PaperAuthor.position.like('%通讯%'))
                position_filters.append(PaperAuthor.position.like('%corresponding%'))
            if "第一作者" in author_positions:
                position_filters.append(PaperAuthor.position.like('%第一%'))
                position_filters.append(PaperAuthor.position.like('%first%'))
            if "其他作者" in author_positions and len(author_positions) < 3:
                # 如果选择了"其他作者"但没有选择全部类型
                position_filters.append(~PaperAuthor.position.like('%通讯%'))
                position_filters.append(~PaperAuthor.position.like('%corresponding%'))
                position_filters.append(~PaperAuthor.position.like('%第一%'))
                position_filters.append(~PaperAuthor.position.like('%first%'))
            
            if position_filters:
                from sqlalchemy import or_
                query = query.filter(or_(*position_filters))
        
        # 3. 有邮箱
        if has_email:
            query = query.filter(PaperAuthor.email != None)
            query = query.filter(PaperAuthor.email != '')
        
        # 4. 所属机构
        if affiliation and affiliation.strip():
            query = query.filter(PaperAuthor.affiliation.like(f'%{affiliation.strip()}%'))
        
        # 5. 论文标题
        if paper_title and paper_title.strip():
            query = query.filter(
                (Paper.title.like(f'%{paper_title.strip()}%')) |
                (Paper.title_cn.like(f'%{paper_title.strip()}%'))
            )
        
        # 6. 研究方向
        if research_direction and research_direction.strip():
            query = query.filter(Paper.research_direction.like(f'%{research_direction.strip()}%'))
        
        # 执行查询
        results = query.order_by(desc(Paper.publish_date)).all()
        api_logger.info(f"搜索结果: 找到 {len(results)} 名论文作者")
        
        # 转换为DataFrame
        data = []
        for author, title, title_cn, research_dir, publish_date in results:
            data.append({
                "ID": author.id,
                "论文ID": author.paper_id,
                "作者姓名": author.author_name,
                "作者类型": author.position or "未知",
                "所属机构": author.affiliation or "未知",
                "邮箱": author.email or "未提供",
                "国家": author.country or "未知",
                "论文标题": title_cn or title,
                "研究方向": research_dir or "未知",
                "发布日期": publish_date.strftime("%Y-%m-%d") if publish_date else "未知"
            })
        
        # 关闭会话
        session.close()
        
        return pd.DataFrame(data)
    
    except Exception as e:
        api_logger.error(f"搜索论文作者时出错: {str(e)}")
        session.close()
        # 返回空DataFrame
        return pd.DataFrame(columns=["ID", "论文ID", "作者姓名", "作者类型", "所属机构", 
                                    "邮箱", "国家", "论文标题", "研究方向", "发布日期"])

with gr.Blocks(title="大学信息管理系统") as demo:
    gr.Markdown("# 大学信息管理系统")
    
    with gr.Tabs():
        # 第一个标签页：展示学校、学院、教师
        with gr.TabItem("信息展示"):
            # 大学选择部分
            with gr.Row():
                with gr.Column(scale=3):
                    # 将搜索框和下拉框合并为一个组件
                    university_dropdown = gr.Dropdown(label="搜索/选择大学", 
                                                      choices=allUniNames, 
                                                      interactive=True, 
                                                      allow_custom_value=True,
                                                      filterable=True,
                                                      value=allUniNames[0] if allUniNames else None)
            
            with gr.Row():
                university_info = gr.DataFrame(label="大学信息", interactive=True)
            
            # 学院展示部分
            with gr.Row():
                college_info = gr.DataFrame(label="学院信息", interactive=True)
            
            # 教师展示部分
            with gr.Row():
                teacher_info = gr.DataFrame(label="教师信息", interactive=True)
            
            # 加载大学信息和学院信息
            university_dropdown.change(
                fn=load_university_info, 
                inputs=university_dropdown, 
                outputs=[university_info, college_info, teacher_info]
            )
            
            # 添加一个自动触发按钮，用于初始化加载
            auto_trigger = gr.Button("加载数据", visible=False)
            auto_trigger.click(
                fn=load_university_info,
                inputs=university_dropdown,
                outputs=[university_info, college_info, teacher_info]
            )
            
            # 事件处理
            # 点击学院行，加载教师信息
            college_info.select(
                fn=lambda df, evt: (api_logger.info(f"选择学院行: {evt.index[0] if evt and hasattr(evt, 'index') and evt.index else 'None'}"), 
                                  load_college_teachers(int(df.loc[evt.index[0], "ID"])) if evt and hasattr(evt, 'index') and evt.index else None)[1],
                inputs=[college_info],
                outputs=[teacher_info]
            )
            
            # 编辑大学
            def prepare_edit_university(df, evt):
                api_logger.info(f"准备编辑大学，事件索引: {evt.index if evt and hasattr(evt, 'index') else 'None'}")
                if not evt or not hasattr(evt, 'index') or not evt.index:
                    api_logger.warning("未选择大学行，无法编辑")
                    return {"visible": False}, None, "", "", "", "", False, False
                
                try:
                    row = df.loc[evt.index[0]]
                    api_logger.info(f"选择编辑大学: {row['中文名称']} (ID: {row['ID']})")
                    return (
                        {"visible": True},
                        int(row["ID"]),
                        row["中文名称"],
                        row["官网"],
                        row["城市"],
                        row["985"] == "是",
                        row["211"] == "是"
                    )
                except Exception as e:
                    api_logger.error(f"准备编辑大学时出错: {str(e)}")
                    return {"visible": False}, None, "", "", "", "", False, False
            

        # 第二个标签页：新增学院
        with gr.TabItem("新增学院"):
            with gr.Row():
                with gr.Column():
                    add_university_dropdown = gr.Dropdown(label="搜索/选择大学", 
                                                          choices=allUniNames, 
                                                          interactive=True, 
                                                          allow_custom_value=True,
                                                          filterable=True,
                                                          value=allUniNames[0] if allUniNames else None)  # 添加默认值
                    
                    add_name = gr.Textbox(label="学院名称")
                    add_website = gr.Textbox(label="学院官网")
                    add_college_button = gr.Button("保存")  # 将"添加学院"改为"保存"
                    add_college_message = gr.Textbox(label="消息")
                    
                with gr.Column():
                    add_university_info = gr.DataFrame(label="大学信息", interactive=True)
                    # 修改这里，确保学院信息表格是可交互的
                    add_college_info = gr.DataFrame(label="学院信息", interactive=True)
                    add_university_dropdown.change(
                        fn=lambda uni_id: (api_logger.info(f"选择大学ID: {uni_id}"), 
                                         process_university_selection(uni_id))[1],
                        inputs=add_university_dropdown,
                        outputs=[add_university_info, add_college_info]
                    )
                    
                    # 添加一个辅助函数来处理学院选择
                    def handle_college_selection(df: pd.DataFrame, evt: gr.SelectData):
                        """处理学院选择事件，返回学院名称和官网"""
                        try:
                            if evt is None:
                                api_logger.warning("学院选择事件为None")
                                return "", ""
                            
                            # 尝试不同的事件数据结构
                            if isinstance(evt, list) and len(evt) > 0:
                                # 新版Gradio的事件格式
                                row_idx = evt[0]
                                api_logger.info(f"使用列表索引方式获取行: {row_idx}")
                                return df.loc[row_idx, "学院名称"], df.loc[row_idx, "学院官网"]
                            elif hasattr(evt, 'index') and evt.index:
                                # 旧版Gradio的事件格式
                                row_idx = evt.index[0]
                                api_logger.info(f"使用evt.index方式获取行: {row_idx}")
                                return df.loc[row_idx, "学院名称"], df.loc[row_idx, "学院官网"]
                            elif isinstance(evt, dict) and 'index' in evt:
                                # 另一种可能的事件格式
                                row_idx = evt['index'][0] if isinstance(evt['index'], list) else evt['index']
                                api_logger.info(f"使用字典索引方式获取行: {row_idx}")
                                return df.loc[row_idx, "学院名称"], df.loc[row_idx, "学院官网"]
                            else:
                                api_logger.warning(f"未知的事件格式: {evt}")
                                return "", ""
                        except Exception as e:
                            api_logger.error(f"处理学院选择时出错: {str(e)}")
                            return "", ""
                
                
                                    # 添加学院信息选择事件处理
                    
                    add_college_info.select(
                        fn=handle_college_selection,
                        inputs=[add_college_info],
                        outputs=[add_name, add_website]
                    )
                    # 添加一个新的辅助函数来处理大学选择
                def process_university_selection(university_name):
                    university_df = None
                    college_df = None
                    while True:
                        if not university_name:
                            api_logger.warning("未选择大学ID")
                            break
                        
                        try:
                            university_id = getUnivercityIdByName(university_name)
                        except (ValueError, TypeError) as e:
                            api_logger.error(f"无法解析大学ID: {university_name}, 错误: {str(e)}")
                            break
                        
                        university = get_university_by_id(university_id)
                        if university:
                            university_df = university_to_df([university])
                        else:
                            api_logger.warning(f"未找到ID为 {university_name} 的大学")
                            break
                        
                        colleges = get_colleges_by_university(university_id)
                        api_logger.info(f"获取到大学 {university.name_cn} 的 {len(colleges)} 个学院")
                        college_df = college_to_df(colleges)
                        break
                    
                    return university_df, college_df                          

                add_college_button.click(
                    fn=add_college,
                    inputs=[add_university_dropdown, add_name, add_website, add_college_info],
                    outputs=[add_college_message, add_name, add_website, add_college_info]
                )
                

        # 添加第三个标签页：教师搜索
        with gr.TabItem("教师搜索"):
            with gr.Row():
                # 搜索条件
                is_national_fun_dropdown = gr.Dropdown(
                    label="主持国家基金", 
                    choices=["全部", "是", "否"], 
                    value="全部"
                )
                university_search = gr.Dropdown(
                    label="大学名称", 
                    choices=["全部"] + allUniNames, 
                    value="全部",
                    allow_custom_value=True,
                    filterable=True
                )
                city_search = gr.Textbox(label="城市")
                
                # 添加新的搜索条件
                is_pub_book_dropdown = gr.Dropdown(
                    label="出过专著", 
                    choices=["全部", "是", "否"], 
                    value="全部"
                )
                is_pub_book_sciencep_dropdown = gr.Dropdown(
                    label="科学出过专著", 
                    choices=["全部", "是", "否"], 
                    value="全部"
                )
                
                search_button = gr.Button("搜索")
            
            with gr.Row():
                # 搜索结果
                all_teachers_info = gr.DataFrame(label="教师信息", interactive=True)
            
            # 搜索按钮点击事件
            search_button.click(
                fn=search_teachers,
                inputs=[
                    is_national_fun_dropdown,
                    university_search,
                    city_search,
                    is_pub_book_dropdown,
                    is_pub_book_sciencep_dropdown
                ],
                outputs=all_teachers_info
            )
            
            # 初始加载所有教师
            def load_all_teachers():
                return search_teachers()

        # 添加第四个标签页：论文作者搜索
        with gr.TabItem("论文作者搜索"):
            with gr.Row():
                # 搜索条件
                with gr.Column(scale=1):
                    is_china_checkbox = gr.Checkbox(
                        label="中国作者", 
                        value=True
                    )
                    author_position = gr.CheckboxGroup(
                        label="作者类型",
                        choices=["通讯作者", "第一作者", "其他作者"],
                        value=["通讯作者", "第一作者", "其他作者"]
                    )
                    has_email_checkbox = gr.Checkbox(
                        label="有邮箱", 
                        value=False
                    )
                    affiliation_search = gr.Textbox(
                        label="所属机构",
                        placeholder="输入机构名称关键词"
                    )
                    paper_title_search = gr.Textbox(
                        label="论文标题",
                        placeholder="输入论文标题关键词"
                    )
                    research_direction_search = gr.Textbox(
                        label="研究方向",
                        placeholder="输入研究方向关键词"
                    )
                    author_search_button = gr.Button("搜索")
            
            with gr.Row():
                # 搜索结果
                authors_info = gr.DataFrame(label="论文作者信息", interactive=True)
            
            # 搜索按钮点击事件
            author_search_button.click(
                fn=search_paper_authors,
                inputs=[
                    is_china_checkbox,
                    author_position,
                    has_email_checkbox,
                    affiliation_search,
                    paper_title_search,
                    research_direction_search
                ],
                outputs=authors_info
            )

    # 创建初始化函数，在界面加载时执行
    def init_interface():
        if allUniNames:
            default_uni = allUniNames[0]
            default_uni_info, default_college_info, default_teacher_info = load_university_info(default_uni)
            default_uni_info_for_add, default_colleage_info_for_add = process_university_selection(default_uni)
            all_teachers = load_all_teachers()
            return default_uni, default_uni_info, default_college_info, default_teacher_info, default_uni, default_uni_info_for_add, default_colleage_info_for_add, all_teachers
        return None, None, None, None, None, None, None, None
    
    # 更新加载事件的输出
    demo.load(
        fn=init_interface,
        outputs=[
            university_dropdown, 
            university_info, 
            college_info, 
            teacher_info, 
            add_university_dropdown, 
            add_university_info,
            add_college_info,
            all_teachers_info
        ]
    )

# 启动应用
if __name__ == "__main__":
    # 更新下拉框选项
    demo.queue()
    api_logger.info("Gradio界面已启动，等待用户访问...")
    demo.launch(share=False, server_port=6610)

# 在现有的 with gr.Tabs() 结构中添加新的标签页

        