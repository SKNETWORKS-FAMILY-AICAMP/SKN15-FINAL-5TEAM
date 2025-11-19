"""
Time Context Utilities

서버 시간을 기반으로 시간 컨텍스트를 생성하여 프롬프트에 주입합니다.
"""
from datetime import datetime
import pytz


def get_current_time_context(timezone: str = "Asia/Seoul") -> str:
    """
    현재 시간 컨텍스트를 생성합니다.

    Args:
        timezone: 타임존 (기본값: Asia/Seoul)

    Returns:
        시간 컨텍스트 문자열

    Example:
        >>> get_current_time_context()
        "2025년 1월 20일 오후 2시 30분 (겨울, 오후)"
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)

    # 년월일 요일
    date_str = now.strftime("%Y년 %m월 %d일 (%A)")
    weekday_kr = {
        "Monday": "월요일",
        "Tuesday": "화요일",
        "Wednesday": "수요일",
        "Thursday": "목요일",
        "Friday": "금요일",
        "Saturday": "토요일",
        "Sunday": "일요일"
    }
    date_str = date_str.replace(now.strftime("%A"), weekday_kr[now.strftime("%A")])

    # 시간
    hour = now.hour
    minute = now.minute

    # 오전/오후
    ampm = "오전" if hour < 12 else "오후"
    hour_12 = hour if hour <= 12 else hour - 12
    if hour_12 == 0:
        hour_12 = 12

    time_str = f"{ampm} {hour_12}시"
    if minute > 0:
        time_str += f" {minute}분"

    # 시간대 분류
    if 6 <= hour < 12:
        period = "아침"
    elif 12 <= hour < 18:
        period = "오후"
    elif 18 <= hour < 22:
        period = "저녁"
    else:
        period = "밤"

    # 계절 분류
    month = now.month
    if month in [3, 4, 5]:
        season = "봄"
    elif month in [6, 7, 8]:
        season = "여름"
    elif month in [9, 10, 11]:
        season = "가을"
    else:
        season = "겨울"

    return f"{date_str} {time_str} ({season}, {period})"


__all__ = ["get_current_time_context"]
