import os
import pandas as pd
from sqlalchemy.orm import Session
from typing import List, Dict, Tuple

import time
import os
from openai import OpenAI
from model.university import ChineseUniversity
from model.universityCollege import UniversityCollege  # 添加导入
from model.universityTeacher import UniversityTeacher  # 添加导入
from utils.logger_settings import api_logger
from db_manager import DBManager


db_manager = DBManager()
openAiClient = OpenAI(base_url="http://39.105.194.16:6691/v1", api_key="key")
        

def extract_university_info(sheet_name: str) -> Tuple[str, bool, bool]:
    """
    从Excel表格名称中提取大学信息
    
    Args:
        sheet_name: Excel表格名称，如"北京大学(985,211)"
    
    Returns:
        Tuple[str, bool, bool]: 大学名称, 是否985, 是否211
    """
    # 分离大学名称和类型标记
    # 华中科技大学（985）
    if "(" in sheet_name and ")" in sheet_name:
        name = sheet_name.split("(")[0].strip()
        type_info = sheet_name.split("(")[1].split(")")[0].lower()
        
        is_985 = "985" in type_info
        is_211 = "211" in type_info
    elif "（" in sheet_name and "）" in sheet_name:
        name = sheet_name.split("（")[0].strip()
        type_info = sheet_name.split("（")[1].split("）")[0].lower()
        
        is_985 = "985" in type_info
        is_211 = "211" in type_info
    else:
        name = sheet_name.strip()
        is_985 = False
        is_211 = False
    
    return name, is_985, is_211

def process_excel_files(data_folder: str) -> List[Dict]:
    """
    处理data文件夹下所有Excel文件，提取大学信息
    
    Args:
        data_folder: 数据文件夹路径
    
    Returns:
        List[Dict]: 大学信息列表
    """
    university_info = []
    
    try:
        # 获取所有Excel文件
        excel_files = [f for f in os.listdir(data_folder) 
                      if f.endswith('.xlsx') or f.endswith('.xls')]
        
        for excel_file in excel_files:
            file_path = os.path.join(data_folder, excel_file)
            api_logger.info(f"处理Excel文件: {file_path}")
            
            # 读取Excel文件的所有表格名称
            try:
                xl = pd.ExcelFile(file_path)
                sheet_names = xl.sheet_names
                
                for sheet_name in sheet_names:
                    name, is_985, is_211 = extract_university_info(sheet_name)
                    
                    university_info.append({
                        "name_cn": name,
                        "is_985": is_985,
                        "is_211": is_211
                    })
                    
            except Exception as e:
                api_logger.error(f"处理Excel文件 {file_path} 失败: {e}")
                continue
    
    except Exception as e:
        api_logger.error(f"处理Excel文件夹失败: {e}")
    
    return university_info

def check_universities_in_database(universities: List[Dict]) -> Dict:
    """
    检查大学是否存在于数据库中
    
    Args:
        universities: 大学信息列表
    
    Returns:
        Dict: 检查结果统计
    """
    result = {
        "total": len(universities),
        "in_database": 0,
        "not_in_database": 0,
        "missing_universities": []
    }
    
    session = db_manager._get_session()
    
    try:
        # 获取数据库中所有大学
        db_universities = ChineseUniversity.get_all(session)
        db_university_names = {uni.name_cn for uni in db_universities}
        
        for uni_info in universities:
            uni_name = uni_info["name_cn"]
            
            if uni_name in db_university_names:
                result["in_database"] += 1
            else:
                result["not_in_database"] += 1
                result["missing_universities"].append(uni_info)
        
    except Exception as e:
        api_logger.error(f"检查大学数据库失败: {e}")
    finally:
        session.close()
    
    return result

def get_university_details_from_openai(university_name: str, is_985: bool, is_211: bool) -> Dict:
    """
    使用OpenAI API获取大学的详细信息
    
    Args:
        university_name: 大学中文名称
        is_985: 是否985大学
        is_211: 是否211大学
        
    Returns:
        Dict: 包含大学英文名、官网和城市的字典
    """
    try:
        prompt = f"""请提供以下中国大学的信息，格式为JSON:
        1. 大学中文名: {university_name}
        2. 大学英文名
        3. 大学官方网站
        4. 所在城市
        
        附加信息: {'985工程大学' if is_985 else ''}{'，' if is_985 and is_211 else ''}{'211工程大学' if is_211 else ''}
        
        请仅返回JSON格式数据，不要有其他文字说明，格式如下:
        {{
            "name_en": "英文名",
            "website": "官网网址",
            "city": "城市名"
        }}
        """
        
        response = openAiClient.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[
                {"role": "system", "content": "你是一个专业的中国大学信息助手，请提供准确的大学信息。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        # 提取返回的JSON内容
        content = response.choices[0].message.content.strip()
        
        # 处理可能的JSON格式问题
        import json
        import re
        
        # 尝试提取JSON部分
        json_match = re.search(r'({.*})', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        
        university_info = json.loads(content)
        
        # 确保返回所有必要字段
        return {
            "name_en": university_info.get("name_en", ""),
            "website": university_info.get("website", ""),
            "city": university_info.get("city", "")
        }
        
    except Exception as e:
        api_logger.error(f"从OpenAI获取大学信息失败: {e}")
        # 返回空信息
        return {
            "name_en": "",
            "website": "",
            "city": ""
        }

def save_missing_universities(missing_universities: List[Dict]) -> int:
    """
    使用OpenAI补充并保存缺失的大学信息到数据库
    
    Args:
        missing_universities: 缺失的大学信息列表
        
    Returns:
        int: 成功保存的大学数量
    """
    session = db_manager._get_session()
    saved_count = 0
    
    try:
        for uni_info in missing_universities:
            uni_name = uni_info["name_cn"]
            is_985 = uni_info["is_985"]
            is_211 = uni_info["is_211"]
            
            api_logger.info(f"正在从OpenAI获取大学信息: {uni_name}")
            
            # 从OpenAI获取详细信息
            details = get_university_details_from_openai(uni_name, is_985, is_211)
            
            # 创建大学对象
            university = ChineseUniversity(
                name_cn=uni_name,
                name_en=details["name_en"],
                website=details["website"],
                city=details["city"],
                is_985=is_985,
                is_211=is_211
            )
            
            # 保存到数据库
            if ChineseUniversity.save(session, university):
                saved_count += 1
                api_logger.info(f"成功保存大学信息: {uni_name}")
            else:
                api_logger.error(f"保存大学信息失败: {uni_name}")
            
            # 避免API请求过于频繁
            time.sleep(1)
            
    except Exception as e:
        api_logger.error(f"保存大学信息过程中发生错误: {e}")
    finally:
        session.close()
    
    return saved_count

def process_college_data(data_folder: str) -> Dict[str, List[str]]:
    """
    处理Excel文件中的学院数据
    
    Args:
        data_folder: 数据文件夹路径
        
    Returns:
        Dict[str, List[str]]: 大学名称到学院列表的映射
    """
    university_colleges = {}
    
    try:
        # 获取所有Excel文件
        excel_files = [f for f in os.listdir(data_folder) 
                      if f.endswith('.xlsx') or f.endswith('.xls')]
        
        for excel_file in excel_files:
            file_path = os.path.join(data_folder, excel_file)
            api_logger.info(f"处理Excel文件中的学院数据: {file_path}")
            
            try:
                xl = pd.ExcelFile(file_path)
                sheet_names = xl.sheet_names
                
                for sheet_name in sheet_names:
                    # 提取大学名称
                    uni_name, _, _ = extract_university_info(sheet_name)
                    
                    # 读取表格数据
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    # 查找学院列
                    college_column = None
                    for col in df.columns:
                        if '学院' in col or '系' in col:
                            college_column = col
                            break
                    
                    if college_column is None:
                        api_logger.warning(f"在表格 {sheet_name} 中未找到学院列")
                        continue
                    
                    # 提取学院名称并去重
                    colleges = df[college_column].dropna().unique().tolist()
                    
                    # 添加到结果字典
                    if uni_name not in university_colleges:
                        university_colleges[uni_name] = []
                    
                    university_colleges[uni_name].extend(colleges)
                    
                    # 去重
                    university_colleges[uni_name] = list(set(university_colleges[uni_name]))
                    
            except Exception as e:
                api_logger.error(f"处理Excel文件 {file_path} 中的学院数据失败: {e}")
                continue
    
    except Exception as e:
        api_logger.error(f"处理学院数据失败: {e}")
    
    return university_colleges

def save_colleges_to_database(university_colleges: Dict[str, List[str]]) -> Dict:
    """
    将学院信息保存到数据库
    
    Args:
        university_colleges: 大学名称到学院列表的映射
        
    Returns:
        Dict: 保存结果统计
    """
    result = {
        "total_colleges": 0,
        "saved_colleges": 0,
        "failed_colleges": 0,
        "universities_not_found": []
    }
    
    session = db_manager._get_session()
    
    try:
        # 获取所有大学
        universities = ChineseUniversity.get_all(session)
        university_map = {uni.name_cn: uni for uni in universities}
        
        for uni_name, colleges in university_colleges.items():
            # 检查大学是否存在
            if uni_name not in university_map:
                result["universities_not_found"].append(uni_name)
                api_logger.warning(f"数据库中未找到大学: {uni_name}")
                continue
            
            university = university_map[uni_name]
            
            for name in colleges:
                result["total_colleges"] += 1
                
                # 创建学院对象
                college = UniversityCollege(
                    university_id=university.id,
                    name=name,
                    website="1"  # 暂时设置为1
                )
                
                # 检查学院是否已存在
                existing_college = session.query(UniversityCollege).filter(
                    UniversityCollege.university_id == university.id,
                    UniversityCollege.name == name
                ).first()
                
                if existing_college:
                    api_logger.info(f"学院已存在: {uni_name} - {name}")
                    result["saved_colleges"] += 1
                    continue
                
                # 保存到数据库
                try:
                    session.add(college)
                    session.commit()
                    result["saved_colleges"] += 1
                    api_logger.info(f"成功保存学院: {uni_name} - {name}")
                except Exception as e:
                    session.rollback()
                    result["failed_colleges"] += 1
                    api_logger.error(f"保存学院失败: {uni_name} - {name}, 错误: {e}")
    
    except Exception as e:
        api_logger.error(f"保存学院信息过程中发生错误: {e}")
    finally:
        session.close()
    
    return result

def process_teacher_data(data_folder: str) -> Dict:
    """
    处理Excel文件中的教师数据并保存到数据库
    
    Args:
        data_folder: 数据文件夹路径
        
    Returns:
        Dict: 处理结果统计
    """
    result = {
        "total_teachers": 0,
        "saved_teachers": 0,
        "failed_teachers": 0,
        "universities_not_found": [],
        "colleges_not_found": [],
        "failed_teacher_records": []  # 添加一个列表来存储未保存成功的教师记录
    }
    
    session = db_manager._get_session()
    
    try:
        # 获取所有大学
        universities = ChineseUniversity.get_all(session)
        university_map = {uni.name_cn: uni for uni in universities}
        
        # 获取所有Excel文件
        excel_files = [f for f in os.listdir(data_folder) 
                      if f.endswith('.xlsx') or f.endswith('.xls')]
        
        for excel_file in excel_files:
            file_path = os.path.join(data_folder, excel_file)
            api_logger.info(f"处理Excel文件中的教师数据: {file_path}")
            
            try:
                xl = pd.ExcelFile(file_path)
                sheet_names = xl.sheet_names
                
                for sheet_name in sheet_names:
                    # 提取大学名称
                    uni_name, _, _ = extract_university_info(sheet_name)
                    
                    # 检查大学是否存在
                    if uni_name not in university_map:
                        if uni_name not in result["universities_not_found"]:
                            result["universities_not_found"].append(uni_name)
                        api_logger.warning(f"数据库中未找到大学: {uni_name}")
                        continue
                    
                    university = university_map[uni_name]
                    
                    # 读取表格数据
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    # 检查必要的列是否存在
                    required_columns = ["姓名", "学院"]
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    if missing_columns:
                        api_logger.warning(f"在表格 {sheet_name} 中缺少必要的列: {', '.join(missing_columns)}")
                        continue
                    
                    # 获取所有学院
                    colleges = session.query(UniversityCollege).filter(
                        UniversityCollege.university_id == university.id
                    ).all()
                    college_map = {college.name: college for college in colleges}
                    
                    # 处理每一行数据（每个教师）
                    for _, row in df.iterrows():
                        # 跳过没有姓名的行
                        if pd.isna(row["姓名"]):
                            continue
                        
                        result["total_teachers"] += 1
                        
                        # 获取学院
                        college_name = row["学院"] if not pd.isna(row["学院"]) else ""
                        college_id = None
                        
                        if college_name:
                            if college_name in college_map:
                                college_id = college_map[college_name].id
                            else:
                                # 学院不存在，创建新学院
                                try:
                                    new_college = UniversityCollege(
                                        university_id=university.id,
                                        name=college_name,
                                        website="1"  # 暂时设置为1
                                    )
                                    session.add(new_college)
                                    session.commit()
                                    college_id = new_college.id
                                    college_map[college_name] = new_college
                                    api_logger.info(f"创建新学院: {uni_name} - {college_name}")
                                except Exception as e:
                                    session.rollback()
                                    if college_name not in result["colleges_not_found"]:
                                        result["colleges_not_found"].append(college_name)
                                    api_logger.error(f"创建学院失败: {uni_name} - {college_name}, 错误: {e}")
                        
                        # 提取教师信息
                        name = row["姓名"]
                        title = row["职称"] if "职称" in df.columns and not pd.isna(row["职称"]) else ""
                        research_direction = row["研究方向"] if "研究方向" in df.columns and not pd.isna(row["研究方向"]) else ""
                        email = row["电子邮箱"] if "电子邮箱" in df.columns and not pd.isna(row["电子邮箱"]) else ""
                        tel = row["电话"] if "电话" in df.columns and not pd.isna(row["电话"]) else ""
                        
                        # 处理复选框字段
                        is_pub_book = 1 if "出版专著" in df.columns and not pd.isna(row["出版专著"]) and row["出版专著"] else 0
                        is_pub_book_sciencep = 1 if "本社专著" in df.columns and not pd.isna(row["本社专著"]) and row["本社专著"] else 0
                        
                        # 处理专著信息
                        bookname = ""
                        if "外设出版专著主要信息" in df.columns and not pd.isna(row["外设出版专著主要信息"]):
                            bookname = row["外设出版专著主要信息"]
                        
                        if "本社专著信息" in df.columns and not pd.isna(row["本社专著信息"]):
                            sciencep_bookname = row["本社专著信息"]
                        
                        # 检查教师是否已存在
                        existing_teacher = session.query(UniversityTeacher).filter(
                            UniversityTeacher.university_id == university.id,
                            UniversityTeacher.name == name,
                            UniversityTeacher.college_id == college_id if college_id else None
                        ).first()
                        
                        if existing_teacher:
                            api_logger.info(f"教师已存在: {uni_name} - {name}")
                            existing_teacher.sciencep_bookname = sciencep_bookname
                            try:
                                session.commit()
                                api_logger.info(f"已更新教师本社专著信息: {uni_name} - {name}")
                            except Exception as e:
                                session.rollback()
                                api_logger.error(f"更新教师本社专著信息失败: {uni_name} - {name}, 错误: {e}")
                        
                            result["saved_teachers"] += 1
                            continue
                        
                        # 创建教师对象
                        teacher = UniversityTeacher(
                            university_id=university.id,
                            college_id=college_id,
                            name=name,
                            title=title,
                            research_direction=research_direction,
                            email=email,
                            tel=tel,
                            is_pub_book=is_pub_book,
                            is_pub_book_sciencep=is_pub_book_sciencep,
                            bookname=bookname,
                            sciencep_bookname=sciencep_bookname
                        )
                        
                        # 保存到数据库
                        try:
                            session.add(teacher)
                            session.commit()
                            result["saved_teachers"] += 1
                            api_logger.info(f"成功保存教师: {uni_name} - {name}")
                        except Exception as e:
                            session.rollback()
                            result["failed_teachers"] += 1
                            api_logger.error(f"保存教师失败: {uni_name} - {name}, 错误: {e}")
                            
                            # 将未保存成功的教师信息添加到列表中
                            failed_record = {
                                "university_name": uni_name,
                                "college_name": college_name,
                                "name": name,
                                "title": title,
                                "research_direction": research_direction,
                                "email": email,
                                "tel": tel,
                                "is_pub_book": is_pub_book,
                                "is_pub_book_sciencep": is_pub_book_sciencep,
                                "bookname": bookname,
                                "error": str(e)
                            }
                            result["failed_teacher_records"].append(failed_record)
                
            except Exception as e:
                api_logger.error(f"处理Excel文件 {file_path} 中的教师数据失败: {e}")
                continue
    
    except Exception as e:
        api_logger.error(f"处理教师数据失败: {e}")
    finally:
        session.close()
    
    return result

def export_failed_teachers_to_csv(failed_records: List[Dict], output_path: str) -> bool:
    """
    将未保存成功的教师信息导出到CSV文件
    
    Args:
        failed_records: 未保存成功的教师记录列表
        output_path: 输出CSV文件路径
        
    Returns:
        bool: 是否成功导出
    """
    try:
        if not failed_records:
            api_logger.info("没有未保存成功的教师记录，无需导出CSV")
            return True
        
        # 创建DataFrame
        df = pd.DataFrame(failed_records)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 导出到CSV
        df.to_csv(output_path, index=False, encoding='utf-8-sig')  # 使用utf-8-sig以支持中文
        
        api_logger.info(f"成功导出 {len(failed_records)} 条未保存成功的教师记录到 {output_path}")
        return True
        
    except Exception as e:
        api_logger.error(f"导出未保存成功的教师记录失败: {e}")
        return False

def processTeachers():
    """处理教师数据并保存到数据库"""
    data_folder = os.path.join(os.path.dirname(__file__), "data")
    
    # 处理Excel文件中的教师数据
    api_logger.info("开始处理Excel文件中的教师数据...")
    result = process_teacher_data(data_folder)
    
    # 输出结果
    api_logger.info(f"处理完成，共发现 {result['total_teachers']} 名教师")
    api_logger.info(f"成功保存: {result['saved_teachers']} 名")
    api_logger.info(f"保存失败: {result['failed_teachers']} 名")
    
    if result["universities_not_found"]:
        api_logger.warning("以下大学在数据库中未找到:")
        for uni_name in result["universities_not_found"]:
            api_logger.warning(f"- {uni_name}")
    
    if result["colleges_not_found"]:
        api_logger.warning("以下学院创建失败:")
        for college_name in result["colleges_not_found"]:
            api_logger.warning(f"- {college_name}")
    
    # 导出未保存成功的教师记录到CSV
    if result["failed_teachers"] > 0:
        output_path = os.path.join(os.path.dirname(__file__), "failed_teachers.csv")
        if export_failed_teachers_to_csv(result["failed_teacher_records"], output_path):
            api_logger.info(f"未保存成功的教师记录已导出到: {output_path}")
        else:
            api_logger.error("导出未保存成功的教师记录失败")

if __name__ == "__main__":
    # processUniversities()
    # processColleges()
    processTeachers()