#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量邮件发送工具
使用SMTP发送邮件，可选使用POP3验证邮件发送状态
"""

import smtplib
import poplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import time
import os
from typing import List, Dict
from utils.logger_settings import api_logger
import csv
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class BatchEmailSender:
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        email: str,
        password: str,
        pop3_server: str = None,
        pop3_port: int = 110,
        use_ssl: bool = True,
    ):
        """
        初始化邮件发送器

        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            email: 发送者邮箱
            password: 邮箱密码或授权码
            pop3_server: POP3服务器地址（可选）
            pop3_port: POP3端口（可选）
            use_ssl: 是否使用SSL连接
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email = email
        self.password = password
        self.pop3_server = pop3_server
        self.pop3_port = pop3_port
        self.use_ssl = use_ssl

    def connect_smtp(self):
        """连接到SMTP服务器"""
        try:
            if self.use_ssl:
                # 使用SSL连接
                self.smtp = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                # 使用普通连接，然后启动TLS
                self.smtp = smtplib.SMTP()
                self.smtp.connect(self.smtp_server, self.smtp_port)
                self.smtp.starttls()  # 启用加密

            self.smtp.login(self.email, self.password)
            api_logger.info("成功连接到SMTP服务器")
            return True
        except Exception as e:
            api_logger.error(f"连接SMTP服务器失败: {e}")
            return False

    def disconnect_smtp(self):
        """断开SMTP连接"""
        try:
            if hasattr(self, "smtp"):
                self.smtp.quit()
                api_logger.info("已断开SMTP连接")
        except Exception as e:
            api_logger.error(f"断开SMTP连接时出错: {e}")

    def connect_pop3(self):
        """连接到POP3服务器"""
        if not self.pop3_server:
            api_logger.warning("未设置POP3服务器，无法验证邮件发送状态")
            return False

        try:
            if self.use_ssl:
                # 使用SSL连接POP3
                self.pop3 = poplib.POP3_SSL(self.pop3_server, self.pop3_port)
            else:
                self.pop3 = poplib.POP3_SSL(self.pop3_server, self.pop3_port)

            self.pop3.user(self.email)
            self.pop3.pass_(self.password)
            api_logger.info("成功连接到POP3服务器")
            return True
        except Exception as e:
            api_logger.error(f"连接POP3服务器失败: {e}")
            return False

    def disconnect_pop3(self):
        """断开POP3连接"""
        try:
            if hasattr(self, "pop3"):
                self.pop3.quit()
                api_logger.info("已断开POP3连接")
        except Exception as e:
            api_logger.error(f"断开POP3连接时出错: {e}")

    def send_single_email(
        self, recipient: str, subject: str, body: str, is_html: bool = False
    ) -> bool:
        """
        发送单封邮件

        Args:
            recipient: 收件人邮箱
            subject: 邮件主题
            body: 邮件正文
            is_html: 是否为HTML格式

        Returns:
            bool: 发送是否成功
        """
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg["From"] = Header(self.email)
            msg["To"] = Header(recipient)
            msg["Subject"] = Header(subject, "utf-8")

            # 添加邮件正文
            content_type = "html" if is_html else "plain"
            msg.attach(MIMEText(body, content_type, "utf-8"))

            # 发送邮件
            text = msg.as_string()
            self.smtp.sendmail(self.email, recipient, text)
            api_logger.info(f"邮件成功发送至: {recipient}")
            return True

        except Exception as e:
            api_logger.error(f"发送邮件至 {recipient} 失败: {e}")
            return False

    def send_batch_emails(self, recipients: List[Dict], delay: float = 1.0) -> Dict:
        """
        批量发送邮件

        Args:
            recipients: 收件人列表，每个元素包含'email', 'subject', 'body'等信息
            delay: 每封邮件发送间隔（秒）

        Returns:
            Dict: 发送统计结果
        """
        if not self.connect_smtp():
            return {"success": 0, "failed": len(recipients), "total": len(recipients)}

        success_count = 0
        failed_count = 0
        failed_recipients = []

        try:
            for recipient_info in recipients:
                recipient = recipient_info.get("email", "")
                subject = recipient_info.get("subject", "")
                body = recipient_info.get("body", "")
                is_html = recipient_info.get("is_html", False)

                if not recipient:
                    api_logger.warning("收件人邮箱为空，跳过")
                    failed_count += 1
                    continue

                if self.send_single_email(recipient, subject, body, is_html):
                    success_count += 1
                else:
                    failed_count += 1
                    failed_recipients.append(recipient)

                # 延迟发送，避免被识别为垃圾邮件
                time.sleep(delay)

        finally:
            self.disconnect_smtp()

        result = {
            "success": success_count,
            "failed": failed_count,
            "total": len(recipients),
            "failed_recipients": failed_recipients,
        }

        api_logger.info(f"批量发送完成 - 成功: {success_count}, 失败: {failed_count}")
        return result

    def read_recipients_from_csv(self, csv_file: str) -> List[Dict]:
        """
        从CSV文件读取收件人信息

        Args:
            csv_file: CSV文件路径

        Returns:
            List[Dict]: 收件人信息列表
        """
        recipients = []
        try:
            with open(csv_file, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    recipients.append(
                        {
                            "email": row.get("email", ""),
                            "subject": row.get("subject", ""),
                            "body": row.get("body", ""),
                            "is_html": row.get("is_html", "false").lower() == "true",
                        }
                    )
            api_logger.info(f"从CSV文件读取了 {len(recipients)} 个收件人")
        except Exception as e:
            api_logger.error(f"读取CSV文件失败: {e}")

        return recipients

    def check_unread_emails(self) -> int:
        """
        检查未读邮件数量（使用POP3）

        Returns:
            int: 未读邮件数量
        """
        if not self.connect_pop3():
            return -1

        try:
            num_messages = len(self.pop3.list()[1])
            self.disconnect_pop3()
            return num_messages
        except Exception as e:
            api_logger.error(f"检查未读邮件失败: {e}")
            self.disconnect_pop3()
            return -1


def main():
    """主函数 - 示例用法"""
    # 从环境变量获取邮件配置
    # base_url = os.getenv("OPENAI_BASE_URL")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    smtp_use_ssl = os.getenv("SMTP_USE_SSL")
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    pop3_server = os.getenv("POP3_SERVER", None)  # POP3服务器是可选的

    # 检查必要的环境变量
    if not sender_email or not sender_password:
        print("错误: 请设置 SENDER_EMAIL 和 SENDER_PASSWORD 环境变量")
        return

    # 创建邮件发送器实例
    email_sender = BatchEmailSender(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        email=sender_email,
        password=sender_password,
        pop3_server=pop3_server,
        use_ssl=smtp_use_ssl,
    )

    # 示例：定义收件人列表
    recipients = [
        {
            "email": "daocodedao@gmail.com",
            "subject": "批量邮件测试",
            "body": "这是一封通过Python批量发送的测试邮件。",
        },
        {
            "email": "35150143@qq.com",
            "subject": "批量邮件测试",
            "body": "这是一封通过Python批量发送的测试邮件。",
        },
    ]

    # 也可以从CSV文件读取收件人信息
    # recipients = email_sender.read_recipients_from_csv('recipients.csv')

    # 批量发送邮件
    result = email_sender.send_batch_emails(recipients, delay=2.0)

    print(
        f"发送完成 - 总数: {result['total']}, 成功: {result['success']}, 失败: {result['failed']}"
    )

    # # 检查未读邮件数量
    # if pop3_server:
    #     unread_count = email_sender.check_unread_emails()
    #     if unread_count >= 0:
    #         print(f"当前邮箱有 {unread_count} 封未读邮件")

    print(f"done")


if __name__ == "__main__":
    main()
