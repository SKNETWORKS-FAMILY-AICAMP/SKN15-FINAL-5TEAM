"""
[Core/Utils] 이메일 발송 유틸리티

이 모듈은 SMTP(Simple Mail Transfer Protocol)를 사용하여 이메일을 발송하는
`EmailSender` 클래스를 제공합니다.

주요 기능:
- 텍스트 및 HTML 형식의 이메일 발송
- 파일 첨부 기능
- 템플릿 기반의 동적 이메일 본문 생성
- 다수 수신자에게 대량 발송
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.logging import get_parent_logger

logger = get_parent_logger("EmailSender")


# ============================================================
# 이메일 발송 클라이언트 클래스
# ============================================================
class EmailSender:
    """
    SMTP를 통해 이메일을 발송하는 클라이언트 클래스입니다.

    NOTE: 이 클래스를 사용하기 전에, `app.core.config.py`의 Settings 클래스에
          아래와 같은 SMTP 관련 설정이 추가되어 있어야 합니다.
          - SMTP_SERVER: str
          - SMTP_PORT: int
          - SMTP_USERNAME: str
          - SMTP_PASSWORD: str
          - SMTP_FROM_EMAIL: str
          - SMTP_FROM_NAME: Optional[str]
          - SMTP_USE_TLS: bool = True

    Example:
        settings = get_settings()
        sender = EmailSender(settings)
        sender.send_email(
            to_email="user@example.com",
            subject="Welcome!",
            body="Hello, welcome to our service!"
        )
    """

    def __init__(self, settings: Settings):
        """
        EmailSender를 초기화합니다.

        Args:
            settings (Settings): `config.py`에서 로드된 애플리케이션 전역 설정 객체.
        """
        self.settings = settings
        logger.info("__init__", "EmailSender initialized",
                   smtp_server=settings.SMTP_SERVER,
                   smtp_port=settings.SMTP_PORT)

    def _connect_smtp(self) -> smtplib.SMTP:
        """
        설정 정보를 바탕으로 SMTP 서버에 연결하고 로그인합니다.

        Returns:
            smtplib.SMTP: 인증까지 완료된 SMTP 연결 객체.

        Raises:
            Exception: SMTP 서버 연결 또는 로그인 실패 시.
        """
        try:
            smtp = smtplib.SMTP(self.settings.SMTP_SERVER, self.settings.SMTP_PORT)
            smtp.ehlo()  # SMTP 서버와 통신 시작을 알림

            if self.settings.SMTP_USE_TLS:
                smtp.starttls()  # TLS 암호화 통신 시작
                smtp.ehlo()

            smtp.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
            logger.debug("_connect_smtp", "SMTP connection established")
            return smtp
        except Exception as e:
            logger.error("_connect_smtp", f"Failed to connect to SMTP server: {e}")
            raise

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """
        단일 이메일을 발송합니다.

        Args:
            to_email (str): 수신자 이메일 주소.
            subject (str): 이메일 제목.
            body (str): 이메일 본문 (텍스트 또는 HTML).
            is_html (bool): 본문이 HTML 형식인지 여부.
            cc (Optional[List[str]]): 참조 수신자 목록.
            bcc (Optional[List[str]]): 숨은 참조 수신자 목록.
            attachments (Optional[List[str]]): 첨부할 파일의 경로 목록.

        Returns:
            bool: 발송 성공 시 True, 실패 시 False.
        """
        try:
            msg = MIMEMultipart()
            from_name = self.settings.SMTP_FROM_NAME
            from_email = self.settings.SMTP_FROM_EMAIL
            msg['From'] = f"{from_name} <{from_email}>" if from_name else from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = ", ".join(cc)

            msg.attach(MIMEText(body, 'html' if is_html else 'plain'))

            if attachments:
                for file_path in attachments:
                    self._attach_file(msg, file_path)

            recipients = [to_email] + (cc or []) + (bcc or [])

            with self._connect_smtp() as smtp:
                smtp.sendmail(from_email, recipients, msg.as_string())

            logger.info("send_email", "Email sent successfully", to=to_email, subject=subject)
            return True
        except Exception as e:
            logger.error("send_email", f"Failed to send email: {e}", to=to_email, subject=subject)
            return False

    def send_html_email(self, to_email: str, subject: str, html_body: str, **kwargs) -> bool:
        """HTML 형식의 이메일을 발송하는 편의 메서드입니다."""
        return self.send_email(to_email=to_email, subject=subject, body=html_body, is_html=True, **kwargs)

    def send_template_email(self, to_email: str, subject: str, template: str, context: Dict[str, Any]) -> bool:
        """
        f-string 템플릿과 context를 결합하여 동적 HTML 이메일을 발송합니다.

        Args:
            template (str): `{variable}` 플레이스홀더를 포함한 HTML 템플릿 문자열.
            context (Dict[str, Any]): 템플릿에 전달할 변수 딕셔너리.

        Returns:
            bool: 발송 성공 여부.
        """
        try:
            body = template.format(**context)
            return self.send_html_email(to_email=to_email, subject=subject, html_body=body)
        except KeyError as e:
            logger.error("send_template_email", f"Missing template variable: {e}")
            return False
        except Exception as e:
            logger.error("send_template_email", f"Failed to render or send template email: {e}")
            return False

    def send_batch(self, recipients: List[str], subject: str, body: str, is_html: bool = False) -> Dict[str, int]:
        """
        여러 수신자에게 동일한 내용의 이메일을 개별적으로 발송합니다.

        Returns:
            Dict[str, int]: 성공 및 실패 횟수를 담은 딕셔너리.
        """
        success_count, failed_count = 0, 0
        for recipient in recipients:
            if self.send_email(to_email=recipient, subject=subject, body=body, is_html=is_html):
                success_count += 1
            else:
                failed_count += 1
        logger.info("send_batch", "Batch email sending complete", total=len(recipients), success=success_count, failed=failed_count)
        return {"success": success_count, "failed": failed_count}

    def _attach_file(self, msg: MIMEMultipart, file_path: str):
        """MIME 메시지에 파일을 첨부합니다."""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning("_attach_file", f"Attachment not found, skipping: {file_path}")
                return

            with open(path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{path.name}"')
            msg.attach(part)
            logger.debug("_attach_file", f"File attached: {path.name}")
        except Exception as e:
            logger.error("_attach_file", f"Failed to attach file: {e}", file_path=file_path)

    def test_connection(self) -> bool:
        """SMTP 서버와의 연결을 테스트합니다."""
        try:
            with self._connect_smtp() as smtp:
                pass
            logger.info("test_connection", "SMTP connection test successful")
            return True
        except Exception as e:
            logger.error("test_connection", f"SMTP connection test failed: {e}")
            return False

# ============================================================
# 전역 유틸리티 인스턴스
# ============================================================
# 이메일 발송 기능이 필요할 때 아래 함수를 통해 쉽게 사용할 수 있습니다.
_email_sender_instance: Optional[EmailSender] = None

def get_email_sender() -> EmailSender:
    """
    EmailSender의 싱글톤 인스턴스를 반환합니다.
    """
    global _email_sender_instance
    if _email_sender_instance is None:
        settings = get_settings()
        _email_sender_instance = EmailSender(settings)
    return _email_sender_instance
