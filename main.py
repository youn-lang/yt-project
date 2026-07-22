import re
from urllib.parse import urlparse, parse_qs

import pandas as pd
import requests
import streamlit as st


# ------------------------------------------------------------
# 1. 페이지 기본 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="유튜브 댓글 분석기",
    page_icon="💬",
    layout="wide",
)

st.title("💬 유튜브 댓글 분석기")
st.caption("1단계: 유튜브 영상 링크에서 댓글을 최대 100개 불러옵니다.")


# ------------------------------------------------------------
# 2. 예시 영상 링크
# ------------------------------------------------------------
EXAMPLE_1_URL = "https://youtu.be/d95J8yzvjbQ?si=LfL5DLwCL8Pk077r"
EXAMPLE_2_URL = "https://youtu.be/I9vK5EVTt0U?si=NEZ8L7MRuNvrzINa"


# session_state를 사용하면 버튼을 눌렀을 때 입력창 값을 바꿀 수 있습니다.
if "youtube_url" not in st.session_state:
    st.session_state.youtube_url = EXAMPLE_1_URL


# 입력창 위에 예시 버튼 두 개를 나란히 배치합니다.
example_col1, example_col2 = st.columns(2)

with example_col1:
    if st.button(
        "예시 1 · 딥마인드 다큐(영어 댓글)",
        use_container_width=True,
    ):
        st.session_state.youtube_url = EXAMPLE_1_URL

with example_col2:
    if st.button(
        "예시 2 · 2002 월드컵 추억(한국어 댓글)",
        use_container_width=True,
    ):
        st.session_state.youtube_url = EXAMPLE_2_URL


# ------------------------------------------------------------
# 3. 유튜브 링크 입력창
# ------------------------------------------------------------
youtube_url = st.text_input(
    "유튜브 영상 링크",
    key="youtube_url",
    placeholder="https://www.youtube.com/watch?v=영상ID",
)

load_button = st.button(
    "댓글 불러오기",
    type="primary",
    use_container_width=True,
)


# ------------------------------------------------------------
# 4. 유튜브 링크에서 영상 ID를 추출하는 함수
# ------------------------------------------------------------
def extract_video_id(url: str) -> str | None:
    """
    유튜브 주소에서 11자리 영상 ID를 추출합니다.

    처리 가능한 대표 주소:
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtube.com/shorts/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID

    ?si=... 같은 추가 값은 영상 ID 추출에 영향을 주지 않습니다.
    """
    if not url:
        return None

    url = url.strip()

    # 사용자가 주소 대신 영상 ID만 직접 입력한 경우도 처리합니다.
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url

    try:
        parsed_url = urlparse(url)

        # 주소 앞에 https://가 없는 경우를 보완합니다.
        if not parsed_url.netloc:
            parsed_url = urlparse("https://" + url)

        host = parsed_url.netloc.lower()
        path = parsed_url.path.strip("/")

        # youtu.be/VIDEO_ID 형식
        if host in {"youtu.be", "www.youtu.be"}:
            video_id = path.split("/")[0]
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                return video_id

        # youtube.com 계열 주소
        if host in {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com",
        }:
            # youtube.com/watch?v=VIDEO_ID 형식
            if path == "watch":
                query_values = parse_qs(parsed_url.query)
                video_id = query_values.get("v", [None])[0]

                if video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                    return video_id

            # youtube.com/shorts/VIDEO_ID
            # youtube.com/embed/VIDEO_ID
            # youtube.com/live/VIDEO_ID
            path_parts = path.split("/")

            if len(path_parts) >= 2 and path_parts[0] in {
                "shorts",
                "embed",
                "live",
            }:
                video_id = path_parts[1]

                if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                    return video_id

    except Exception:
        return None

    return None


# ------------------------------------------------------------
# 5. YouTube Data API에서 댓글을 가져오는 함수
# ------------------------------------------------------------
def fetch_youtube_comments(video_id: str, api_key: str) -> list[dict]:
    """
    YouTube Data API v3의 commentThreads 엔드포인트에서
    댓글을 최대 100개 가져옵니다.

    order='relevance'를 사용해 관련도 기준으로 요청한 뒤,
    앱 내부에서 좋아요 수 기준으로 다시 정렬합니다.
    """
    api_url = "https://www.googleapis.com/youtube/v3/commentThreads"

    params = {
        "part": "snippet",
        "videoId": video_id,
        "key": api_key,
        "maxResults": 100,
        "order": "relevance",
        "textFormat": "plainText",
    }

    # 응답이 늦어지는 상황을 막기 위해 timeout을 설정합니다.
    response = requests.get(api_url, params=params, timeout=20)

    # 4xx, 5xx 오류가 발생하면 예외를 발생시킵니다.
    response.raise_for_status()

    data = response.json()
    comments = []

    for item in data.get("items", []):
        top_comment = (
            item.get("snippet", {})
            .get("topLevelComment", {})
            .get("snippet", {})
        )

        comments.append(
            {
                "댓글": top_comment.get("textOriginal", ""),
                "좋아요 수": top_comment.get("likeCount", 0),
            }
        )

    # 좋아요 수가 많은 댓글부터 정렬합니다.
    comments.sort(
        key=lambda comment: comment["좋아요 수"],
        reverse=True,
    )

    return comments


# ------------------------------------------------------------
# 6. 댓글 불러오기 버튼을 눌렀을 때 실행
# ------------------------------------------------------------
if load_button:
    video_id = extract_video_id(youtube_url)

    # 잘못된 링크 또는 영상 ID를 찾을 수 없는 경우
    if not video_id:
        st.error(
            "유튜브 영상 ID를 찾지 못했습니다. "
            "youtu.be 주소 또는 youtube.com/watch 주소인지 확인해 주세요."
        )
        st.stop()

    # Streamlit Cloud의 비밀 금고에서 API 키를 불러옵니다.
    try:
        youtube_api_key = st.secrets["YOUTUBE_API_KEY"]
    except KeyError:
        st.error(
            "YouTube API 키가 설정되지 않았습니다. "
            "Streamlit Cloud의 Secrets에 "
            '`YOUTUBE_API_KEY = "발급받은_API_키"` 형식으로 등록해 주세요.'
        )
        st.stop()

    with st.spinner("댓글을 불러오는 중입니다..."):
        try:
            comments = fetch_youtube_comments(
                video_id=video_id,
                api_key=youtube_api_key,
            )

            # API 호출은 성공했지만 댓글이 없는 경우
            if not comments:
                st.warning(
                    "가져올 수 있는 댓글이 없습니다. "
                    "댓글이 없는 영상이거나 댓글 작성이 제한된 영상일 수 있습니다."
                )
                st.stop()

            comments_df = pd.DataFrame(comments)

            # 가져온 댓글 개수를 지표 카드로 표시합니다.
            st.metric(
                label="가져온 댓글 수",
                value=f"{len(comments_df):,}개",
            )

            st.subheader("댓글 목록")
            st.dataframe(
                comments_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "댓글": st.column_config.TextColumn(
                        "댓글",
                        width="large",
                    ),
                    "좋아요 수": st.column_config.NumberColumn(
                        "좋아요 수",
                        format="%d",
                    ),
                },
            )

        except requests.exceptions.Timeout:
            st.error(
                "YouTube 서버의 응답이 지연되고 있습니다. "
                "잠시 후 다시 시도해 주세요."
            )

        except requests.exceptions.HTTPError as error:
            status_code = error.response.status_code

            try:
                error_data = error.response.json()
                api_message = (
                    error_data.get("error", {})
                    .get("message", "")
                )
            except ValueError:
                api_message = ""

            if status_code == 403:
                st.error(
                    "댓글을 가져오지 못했습니다. "
                    "댓글이 비활성화된 영상이거나, API 키 권한·할당량에 문제가 있을 수 있습니다."
                )
            elif status_code == 404:
                st.error(
                    "영상을 찾지 못했습니다. "
                    "삭제되었거나 비공개 영상인지 확인해 주세요."
                )
            elif status_code == 400:
                st.error(
                    "요청한 영상 정보를 처리할 수 없습니다. "
                    "유튜브 링크가 올바른지 확인해 주세요."
                )
            else:
                message = (
                    f"댓글을 가져오는 중 오류가 발생했습니다. "
                    f"HTTP 상태 코드: {status_code}"
                )

                if api_message:
                    message += f"\n\nYouTube API 메시지: {api_message}"

                st.error(message)

        except requests.exceptions.RequestException:
            st.error(
                "네트워크 연결 문제로 댓글을 가져오지 못했습니다. "
                "인터넷 연결 상태를 확인한 뒤 다시 시도해 주세요."
            )

        except Exception as error:
            st.error(
                "예상하지 못한 오류가 발생했습니다. "
                "링크와 API 키 설정을 확인해 주세요."
            )
            st.exception(error)

