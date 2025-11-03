"""
이메일 전송 유틸리티 (SMTP)
"""

import os
import asyncio
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

# SMTP 설정
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@kimechat.com")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "KIME Chat")


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    """
    이메일 전송

    Args:
        to_email: 수신자 이메일
        subject: 이메일 제목
        html_content: HTML 내용
        text_content: 텍스트 내용 (선택사항, HTML을 지원하지 않는 클라이언트용)

    Returns:
        bool: 전송 성공 여부
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("⚠️ SMTP credentials not configured")
        return False

    try:
        # 이메일 메시지 생성
        message = MIMEMultipart("alternative")
        message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        message["To"] = to_email
        message["Subject"] = subject

        # 텍스트 버전 추가
        if text_content:
            part1 = MIMEText(text_content, "plain")
            message.attach(part1)

        # HTML 버전 추가
        part2 = MIMEText(html_content, "html")
        message.attach(part2)

        # SMTP 서버 연결 및 전송
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            start_tls=True,
        )

        print(f"✅ Email sent to {to_email}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return False


def generate_password_reset_email(reset_link: str, user_name: str = "사용자") -> tuple[str, str]:
    """
    비밀번호 재설정 이메일 HTML 생성

    Args:
        reset_link: 비밀번호 재설정 링크
        user_name: 사용자 이름

    Returns:
        tuple[str, str]: (HTML 내용, 텍스트 내용)
    """
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .content {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #9333ea;
            margin: 0;
        }}
        .button {{
            display: inline-block;
            padding: 15px 30px;
            background-color: #9333ea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }}
        .warning {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <div class="header">
                <h1>🗡️ KIME Chat</h1>
            </div>

            <p>안녕하세요, {user_name}님!</p>

            <p>비밀번호 재설정 요청을 받았습니다. 아래 버튼을 클릭하여 새로운 비밀번호를 설정해주세요.</p>

            <div style="text-align: center;">
                <a href="{reset_link}" class="button">비밀번호 재설정</a>
            </div>

            <p>또는 아래 링크를 복사하여 브라우저에 붙여넣으세요:</p>
            <p style="word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 5px;">
                {reset_link}
            </p>

            <div class="warning">
                <strong>⚠️ 보안 안내</strong>
                <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                    <li>이 링크는 <strong>1시간 동안</strong>만 유효합니다.</li>
                    <li>비밀번호 재설정을 요청하지 않으셨다면 이 이메일을 무시해주세요.</li>
                    <li>이 링크는 한 번만 사용할 수 있습니다.</li>
                </ul>
            </div>

            <div class="footer">
                <p>이 이메일은 KIME Chat 시스템에서 자동으로 발송되었습니다.</p>
                <p>문의사항이 있으시면 support@kimechat.com으로 연락해주세요.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    text_content = f"""
KIME Chat 비밀번호 재설정

안녕하세요, {user_name}님!

비밀번호 재설정 요청을 받았습니다.
아래 링크를 클릭하여 새로운 비밀번호를 설정해주세요:

{reset_link}

⚠️ 보안 안내:
- 이 링크는 1시간 동안만 유효합니다.
- 비밀번호 재설정을 요청하지 않으셨다면 이 이메일을 무시해주세요.
- 이 링크는 한 번만 사용할 수 있습니다.

---
이 이메일은 KIME Chat 시스템에서 자동으로 발송되었습니다.
"""

    return html_content, text_content
