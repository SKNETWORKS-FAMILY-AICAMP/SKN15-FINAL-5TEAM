"""
Email Sending Utility
SMTP 이메일 발송

Features:
- SMTP 서버 연결
- HTML/텍스트 이메일 발송
- 첨부 파일 지원
- 템플릿 기반 이메일
- 대량 발송
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from app.core.logging import get_parent_logger

logger = get_parent_logger("EmailSender")


@dataclass
class EmailConfig:
    """이메일 설정"""
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    from_email: str
    from_name: Optional[str] = None
    use_tls: bool = True


class EmailSender:
    """
    SMTP 이메일 발송 시스템

    Features:
    - 텍스트/HTML 이메일
    - 첨부 파일
    - 대량 발송
    - 템플릿 기반

    Example:
        # 환경 변수에서 설정 로드
        sender = EmailSender.from_env()

        # 이메일 발송
        sender.send_email(
            to_email="user@example.com",
            subject="Welcome!",
            body="Hello, welcome to our service!",
            is_html=False
        )

        # HTML 이메일
        sender.send_html_email(
            to_email="user@example.com",
            subject="Welcome!",
            html_body="<h1>Hello!</h1><p>Welcome to our service</p>"
        )
    """

    def __init__(self, config: EmailConfig):
        """
        Args:
            config: EmailConfig 인스턴스
        """
        self.config = config

        logger.info("__init__", "EmailSender initialized",
                   smtp_server=config.smtp_server,
                   smtp_port=config.smtp_port)

    @classmethod
    def from_env(cls) -> "EmailSender":
        """
        환경 변수에서 설정 로드

        Required env vars:
        - SMTP_SERVER
        - SMTP_PORT
        - SMTP_USERNAME
        - SMTP_PASSWORD
        - FROM_EMAIL

        Returns:
            EmailSender 인스턴스
        """
        config = EmailConfig(
            smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            from_email=os.getenv("FROM_EMAIL", ""),
            from_name=os.getenv("FROM_NAME"),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        )

        if not config.smtp_username or not config.smtp_password:
            logger.warning("from_env", "SMTP credentials not configured")

        return cls(config)

    def _connect_smtp(self) -> smtplib.SMTP:
        """
        SMTP 서버 연결

        Returns:
            SMTP 연결 객체
        """
        try:
            smtp = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            smtp.ehlo()

            if self.config.use_tls:
                smtp.starttls()
                smtp.ehlo()

            smtp.login(self.config.smtp_username, self.config.smtp_password)

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
        이메일 발송

        Args:
            to_email: 수신자 이메일
            subject: 제목
            body: 본문
            is_html: HTML 여부
            cc: 참조 (선택)
            bcc: 숨은 참조 (선택)
            attachments: 첨부 파일 경로 리스트 (선택)

        Returns:
            발송 성공 여부
        """
        try:
            # 메시지 생성
            msg = MIMEMultipart()
            msg['From'] = f"{self.config.from_name} <{self.config.from_email}>" if self.config.from_name else self.config.from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = ", ".join(cc)

            # 본문 추가
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            # 첨부 파일 추가
            if attachments:
                for file_path in attachments:
                    self._attach_file(msg, file_path)

            # 수신자 목록
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # SMTP 연결 및 발송
            smtp = self._connect_smtp()
            smtp.sendmail(self.config.from_email, recipients, msg.as_string())
            smtp.quit()

            logger.info("send_email", "Email sent successfully",
                       to=to_email,
                       subject=subject)

            return True

        except Exception as e:
            logger.error("send_email", f"Failed to send email: {e}",
                        to=to_email,
                        subject=subject)
            return False

    def send_html_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        HTML 이메일 발송

        Args:
            to_email: 수신자 이메일
            subject: 제목
            html_body: HTML 본문
            cc: 참조 (선택)
            bcc: 숨은 참조 (선택)

        Returns:
            발송 성공 여부
        """
        return self.send_email(
            to_email=to_email,
            subject=subject,
            body=html_body,
            is_html=True,
            cc=cc,
            bcc=bcc
        )

    def send_template_email(
        self,
        to_email: str,
        subject: str,
        template: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        템플릿 기반 이메일 발송

        Args:
            to_email: 수신자 이메일
            subject: 제목
            template: 템플릿 문자열 (Python f-string format)
            context: 템플릿 변수 dict

        Returns:
            발송 성공 여부
        """
        try:
            # 템플릿 렌더링
            body = template.format(**context)

            return self.send_email(
                to_email=to_email,
                subject=subject,
                body=body,
                is_html=True
            )

        except Exception as e:
            logger.error("send_template_email", f"Failed to render template: {e}")
            return False

    def send_batch(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        is_html: bool = False
    ) -> Dict[str, int]:
        """
        대량 이메일 발송

        Args:
            recipients: 수신자 이메일 리스트
            subject: 제목
            body: 본문
            is_html: HTML 여부

        Returns:
            {"success": int, "failed": int}
        """
        success_count = 0
        failed_count = 0

        for recipient in recipients:
            result = self.send_email(
                to_email=recipient,
                subject=subject,
                body=body,
                is_html=is_html
            )

            if result:
                success_count += 1
            else:
                failed_count += 1

        logger.info("send_batch", "Batch email complete",
                   total=len(recipients),
                   success=success_count,
                   failed=failed_count)

        return {"success": success_count, "failed": failed_count}

    def _attach_file(self, msg: MIMEMultipart, file_path: str) -> None:
        """
        첨부 파일 추가

        Args:
            msg: MIME 메시지 객체
            file_path: 첨부 파일 경로
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning("_attach_file", f"Attachment not found: {file_path}")
                return

            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {path.name}'
            )

            msg.attach(part)

            logger.debug("_attach_file", f"File attached: {path.name}")

        except Exception as e:
            logger.error("_attach_file", f"Failed to attach file: {e}")

    def test_connection(self) -> bool:
        """
        SMTP 연결 테스트

        Returns:
            연결 성공 여부
        """
        try:
            smtp = self._connect_smtp()
            smtp.quit()
            logger.info("test_connection", "SMTP connection test successful")
            return True

        except Exception as e:
            logger.error("test_connection", f"SMTP connection test failed: {e}")
            return False
