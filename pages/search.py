import html
import re
import unicodedata

import pandas as pd
import spacy
import streamlit as st
from kiwipiepy import Kiwi
from sudachipy import dictionary, tokenizer


TOKEN_CACHE_VERSION = "search004-pos-schema-v2"


# ------------------------------------------------------------
# 1. 페이지 기본 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="댓글 검색",
    page_icon="🔎",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --deep-green: #24331f;
        --forest: #355129;
        --olive: #7d8d4d;
        --olive-light: #e8ecd9;
        --orange: #e97811;
        --paper: #ffffff;
        --line: #d8ddcd;
        --gray: #666b61;
    }

    .stApp {
        background:
            radial-gradient(circle at 95% 5%, rgba(125, 141, 77, 0.12), transparent 24%),
            linear-gradient(180deg, #f7f8f2 0%, #ffffff 58%, #f1f4e8 100%);
    }

    [data-testid="stHeader"] {
        background: rgba(247, 248, 242, 0.88);
        backdrop-filter: blur(10px);
    }

    .block-container {
        max-width: 1180px;
        padding-top: 1.5rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        color: var(--deep-green);
        letter-spacing: -0.03em;
    }

    .page-hero {
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg, #ffffff 0%, #edf1e2 100%);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 1.35rem 1.55rem;
        margin-bottom: 1rem;
        box-shadow: 0 12px 30px rgba(36, 51, 31, 0.09);
    }

    .page-hero::after {
        content: "Aa  가나다  かな  🔎";
        position: absolute;
        right: 1.5rem;
        top: 0.8rem;
        color: rgba(125, 141, 77, 0.20);
        font-size: 1.8rem;
        font-weight: 900;
        letter-spacing: 0.12rem;
    }

    .page-kicker {
        color: var(--olive);
        font-size: 0.84rem;
        font-weight: 850;
        margin-bottom: 0.2rem;
    }

    .page-title {
        margin: 0;
        color: var(--deep-green);
        font-size: 2.15rem;
        font-weight: 900;
    }

    .page-copy {
        margin: 0.4rem 0 0;
        color: var(--gray);
        font-size: 0.96rem;
    }

    .section-label {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin: 1.15rem 0 0.7rem;
        color: var(--deep-green);
        font-size: 1.15rem;
        font-weight: 850;
    }

    .section-number {
        display: inline-flex;
        width: 32px;
        height: 32px;
        align-items: center;
        justify-content: center;
        border-radius: 10px;
        background: var(--olive);
        color: white;
        font-weight: 900;
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #edf1e2 100%);
        border: 1px solid #aab58d;
        border-radius: 17px;
        padding: 0.9rem 1rem;
        box-shadow: 0 8px 22px rgba(42, 58, 33, 0.08);
    }

    .comment-card {
        background: rgba(255, 255, 255, 0.97);
        border: 1px solid var(--line);
        border-left: 5px solid var(--olive);
        border-radius: 14px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.7rem;
        box-shadow: 0 6px 18px rgba(36, 51, 31, 0.06);
    }

    .comment-meta {
        color: var(--olive);
        font-size: 0.82rem;
        font-weight: 800;
        margin-bottom: 0.35rem;
    }

    .comment-text {
        color: var(--deep-green);
        line-height: 1.6;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
    }

    .highlight {
        background: rgba(233, 120, 17, 0.24);
        color: #7b3b00;
        border-radius: 4px;
        padding: 0 0.12rem;
        font-weight: 800;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="page-hero">
        <div class="page-kicker">COMMENT SEARCH</div>
        <h1 class="page-title">검색</h1>
        <p class="page-copy">
            수집한 댓글에서 원문 문자열이나 기본형을 검색하고 실제 사용 맥락을 확인합니다.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# 2. 메인 페이지의 댓글 데이터와 분석 언어 가져오기
# ------------------------------------------------------------
def get_comments_dataframe() -> pd.DataFrame | None:
    """메인 페이지에서 session_state에 저장한 댓글을 가져옵니다."""
    candidate_keys = [
        "comments_df",
        "youtube_comments_df",
        "comment_df",
    ]

    for key in candidate_keys:
        value = st.session_state.get(key)

        if isinstance(value, pd.DataFrame) and not value.empty:
            if "댓글" in value.columns:
                return value.copy()

    comments_list = st.session_state.get("comments")

    if isinstance(comments_list, list) and comments_list:
        dataframe = pd.DataFrame(comments_list)

        if "댓글" in dataframe.columns:
            return dataframe

    return None


# 이전 코드 버전에서 남은 잘못된 세부 품사 값은 새 스키마에서 정리합니다.
if st.session_state.get("_search_page_schema_version") != TOKEN_CACHE_VERSION:
    st.session_state.pop("lemma_search_major_pos", None)
    st.session_state.pop("lemma_search_detailed_pos", None)
    st.session_state.pop("_previous_lemma_search_major_pos", None)
    st.session_state["_search_page_schema_version"] = TOKEN_CACHE_VERSION


comments_df = get_comments_dataframe()

if comments_df is None:
    st.warning(
        "검색할 댓글 데이터가 없습니다. "
        "먼저 메인 페이지에서 분석 언어를 선택하고 유튜브 댓글을 불러와 주세요."
    )
    st.stop()

comments_df["댓글"] = comments_df["댓글"].fillna("").astype(str)

analysis_language = st.session_state.get("selected_analysis_language")

if analysis_language not in {"한국어", "일본어", "영어"}:
    st.warning(
        "분석 언어 정보가 없습니다. 메인 페이지에서 분석 언어를 선택한 뒤 "
        "댓글을 다시 불러와 주세요."
    )
    st.stop()

summary_col1, summary_col2, summary_col3 = st.columns(3)

with summary_col1:
    st.metric("검색 언어", analysis_language)

with summary_col2:
    st.metric("검색 대상 댓글", f"{len(comments_df):,}개")

with summary_col3:
    non_empty_count = comments_df["댓글"].str.strip().ne("").sum()
    st.metric("내용이 있는 댓글", f"{non_empty_count:,}개")


# ------------------------------------------------------------
# 3. 검색 조건 입력
# ------------------------------------------------------------
st.markdown(
    """
    <div class="section-label">
        <span class="section-number">1</span>
        검색 조건
    </div>
    """,
    unsafe_allow_html=True,
)

search_mode = st.radio(
    "검색 방식",
    options=["원문 문자열 검색", "기본형 검색"],
    horizontal=True,
    help=(
        "원문 문자열 검색은 댓글에 실제로 적힌 문자 배열을 찾습니다. "
        "기본형 검색은 형태소 분석 결과의 기본형이 같은 활용형·굴절형을 찾습니다."
    ),
)

placeholder_by_language = {
    "한국어": {
        "원문 문자열 검색": "예: 인공지능, ㅋㅋㅋ, 😂",
        "기본형 검색": "예: 보다, 좋다, 사람",
    },
    "일본어": {
        "원문 문자열 검색": "例: すごい, カワイイ, 😂",
        "기본형 검색": "例: 見る, 良い, 人",
    },
    "영어": {
        "원문 문자열 검색": "Example: amazing, AI, 😂",
        "기본형 검색": "Example: go, be, child",
    },
}

if search_mode == "원문 문자열 검색":
    search_col1, search_col2, search_col3 = st.columns([2, 1, 1])

    with search_col1:
        search_text = st.text_input(
            "찾을 문자열",
            placeholder=placeholder_by_language[analysis_language][search_mode],
            key="literal_search_text",
        )

    with search_col2:
        case_sensitive = st.checkbox(
            "영문 대소문자 구분",
            value=False,
            help=(
                "해제하면 영어의 대문자와 소문자를 같은 문자로 검색합니다. "
                "한국어와 일본어 문자열에는 영향을 주지 않습니다."
            ),
        )

    with search_col3:
        normalize_unicode = st.checkbox(
            "표기 폭 정규화",
            value=True,
            help=(
                "유니코드 NFKC 정규화를 적용합니다. 일본어의 전각·반각 가나와 "
                "영어의 전각·반각 알파벳처럼 폭만 다른 표기를 함께 검색합니다."
            ),
        )

    st.caption(
        "댓글 원문에 실제로 나타난 문자열을 검색합니다. "
        "활용형이나 굴절형은 서로 다른 문자열로 취급됩니다."
    )
else:
    search_text = st.text_input(
        "찾을 기본형",
        placeholder=placeholder_by_language[analysis_language][search_mode],
        key="lemma_search_text",
    )
    case_sensitive = False
    normalize_unicode = True

    analyzer_description = {
        "한국어": "Kiwi",
        "일본어": "SudachiPy",
        "영어": "spaCy",
    }[analysis_language]

    st.caption(
        f"{analyzer_description}로 검색어와 댓글을 분석하여 기본형이 같은 형태를 찾습니다. "
        "예를 들어 영어 go는 went·gone을, 일본어 見る는 見た·見て를 함께 찾을 수 있습니다."
    )


# ------------------------------------------------------------
# 4. 다국어 문자열 검색과 강조 표시
# ------------------------------------------------------------
def split_search_units(text: str) -> list[tuple[str, int, int]]:
    """
    원문을 정규화 가능한 단위로 나눕니다.

    결합 문자와 일본어 반각 탁점·반탁점은 앞 문자와 같은 단위로 묶어
    NFKC 정규화 후에도 원문의 위치를 추적할 수 있게 합니다.
    """
    units: list[tuple[str, int, int]] = []

    for index, character in enumerate(text):
        is_combining = unicodedata.combining(character) != 0
        is_halfwidth_mark = character in {"ﾞ", "ﾟ"}

        if units and (is_combining or is_halfwidth_mark):
            previous_text, start, _ = units[-1]
            units[-1] = (previous_text + character, start, index + 1)
        else:
            units.append((character, index, index + 1))

    return units


def transform_for_search(
    text: str,
    case_sensitive: bool,
    normalize_unicode: bool,
) -> tuple[str, list[tuple[int, int]]]:
    """
    검색용 문자열과 각 검색 문자가 가리키는 원문 범위를 반환합니다.
    """
    transformed_parts: list[str] = []
    source_ranges: list[tuple[int, int]] = []

    for unit, start, end in split_search_units(text):
        transformed = (
            unicodedata.normalize("NFKC", unit)
            if normalize_unicode
            else unit
        )

        if not case_sensitive:
            transformed = transformed.casefold()

        transformed_parts.append(transformed)
        source_ranges.extend([(start, end)] * len(transformed))

    return "".join(transformed_parts), source_ranges


def find_occurrence_spans(
    text: str,
    query: str,
    case_sensitive: bool,
    normalize_unicode: bool,
) -> list[tuple[int, int]]:
    """원문에서 검색 문자열의 비중첩 출현 범위를 찾습니다."""
    transformed_text, source_ranges = transform_for_search(
        text,
        case_sensitive,
        normalize_unicode,
    )
    transformed_query, _ = transform_for_search(
        query,
        case_sensitive,
        normalize_unicode,
    )

    if not transformed_query:
        return []

    normalized_spans: list[tuple[int, int]] = []
    search_start = 0

    while True:
        match_start = transformed_text.find(
            transformed_query,
            search_start,
        )

        if match_start == -1:
            break

        match_end = match_start + len(transformed_query)
        normalized_spans.append((match_start, match_end))
        search_start = match_end

    original_spans: list[tuple[int, int]] = []

    for match_start, match_end in normalized_spans:
        if match_start >= len(source_ranges) or match_end <= 0:
            continue

        original_start = source_ranges[match_start][0]
        original_end = source_ranges[match_end - 1][1]

        if original_spans and original_start < original_spans[-1][1]:
            original_start = original_spans[-1][1]

        if original_start < original_end:
            original_spans.append((original_start, original_end))

    return original_spans


def highlight_text(text: str, spans: list[tuple[int, int]]) -> str:
    """찾은 원문 범위를 HTML로 안전하게 강조합니다."""
    if not spans:
        return html.escape(text)

    output: list[str] = []
    cursor = 0

    for start, end in spans:
        output.append(html.escape(text[cursor:start]))
        output.append(
            '<span class="highlight">'
            + html.escape(text[start:end])
            + "</span>"
        )
        cursor = end

    output.append(html.escape(text[cursor:]))
    return "".join(output)



# ------------------------------------------------------------
# 기본형 검색에 사용할 언어별 품사 표시 체계
# ------------------------------------------------------------
KOREAN_POS_NAMES = {
    "NNG": "일반 명사", "NNP": "고유 명사", "NNB": "의존 명사",
    "NR": "수사", "NP": "대명사", "VV": "동사", "VA": "형용사",
    "VX": "보조 용언", "VCP": "긍정 지정사", "VCN": "부정 지정사",
    "MM": "관형사", "MAG": "일반 부사", "MAJ": "접속 부사",
    "IC": "감탄사", "JKS": "주격 조사", "JKC": "보격 조사",
    "JKG": "관형격 조사", "JKO": "목적격 조사", "JKB": "부사격 조사",
    "JKV": "호격 조사", "JKQ": "인용격 조사", "JX": "보조사",
    "JC": "접속 조사", "EP": "선어말 어미", "EF": "종결 어미",
    "EC": "연결 어미", "ETN": "명사형 전성 어미", "ETM": "관형형 전성 어미",
    "XPN": "접두사", "XSN": "명사 파생 접미사", "XSV": "동사 파생 접미사",
    "XSA": "형용사 파생 접미사", "XR": "어근",
    "SF": "마침표·물음표·느낌표", "SP": "쉼표·가운뎃점·콜론",
    "SS": "괄호·따옴표", "SSO": "여는 괄호·따옴표", "SSC": "닫는 괄호·따옴표",
    "SE": "줄임표", "SO": "붙임표", "SW": "기타 기호",
    "SL": "영문", "SH": "한자", "SN": "숫자",
    "W_URL": "URL", "W_EMAIL": "이메일", "W_HASHTAG": "해시태그",
    "W_MENTION": "멘션", "W_SERIAL": "일련번호", "Z_CODA": "덧붙은 받침",
    "USER0": "사용자 정의어",
}

KOREAN_POS_GROUPS = {
    "명사": {"NNG", "NNP", "NNB"},
    "대명사·수사": {"NP", "NR"},
    "동사": {"VV", "VX", "VCP", "VCN"},
    "형용사": {"VA"},
    "관형사": {"MM"},
    "부사": {"MAG", "MAJ"},
    "감탄사": {"IC"},
    "조사": {"JKS", "JKC", "JKG", "JKO", "JKB", "JKV", "JKQ", "JX", "JC"},
    "어미": {"EP", "EF", "EC", "ETN", "ETM"},
    "접사·어근": {"XPN", "XSN", "XSV", "XSA", "XR", "Z_CODA"},
    "영문": {"SL"},
    "한자": {"SH"},
    "숫자": {"SN"},
    "문장부호": {"SF", "SP", "SS", "SSO", "SSC", "SE", "SO"},
    "기타 기호": {"SW"},
    "웹 표현": {"W_URL", "W_EMAIL", "W_HASHTAG", "W_MENTION", "W_SERIAL"},
    "기타": {"USER0"},
}

KOREAN_POS_ORDER = [
    "명사", "대명사·수사", "동사", "형용사", "관형사", "부사", "감탄사",
    "접사·어근", "조사", "어미", "영문", "한자", "숫자", "이모지",
    "문장부호", "기타 기호", "웹 표현", "기타",
]

JAPANESE_POS_ORDER = [
    "名詞", "代名詞", "動詞", "形容詞", "形状詞", "連体詞", "副詞",
    "接続詞", "感動詞", "接頭辞", "接尾辞", "助詞", "助動詞",
    "絵文字", "記号", "補助記号", "空白", "未分類",
]

ENGLISH_POS_ORDER = [
    "NOUN", "PROPN", "VERB", "ADJ", "ADV", "PRON", "NUM", "INTJ",
    "AUX", "DET", "ADP", "PART", "CCONJ", "SCONJ", "PUNCT", "SYM", "X",
]


def korean_major_pos(tag: str) -> str:
    for group_name, tags in KOREAN_POS_GROUPS.items():
        if tag in tags:
            return group_name
    return "기타"


def japanese_detailed_pos(pos_tuple: tuple[str, ...]) -> str:
    meaningful = [item for item in pos_tuple[:3] if item and item != "*"]
    return "-".join(meaningful) if meaningful else "未分類"


def ordered_values(values: list[str], priority: list[str]) -> list[str]:
    unique_values = list(dict.fromkeys(str(value) for value in values))
    priority_index = {value: index for index, value in enumerate(priority)}
    return sorted(
        unique_values,
        key=lambda value: (
            priority_index.get(value, len(priority_index)),
            value,
        ),
    )


# ------------------------------------------------------------
# 5. 언어별 기본형 분석
# ------------------------------------------------------------
@st.cache_resource
def load_kiwi() -> Kiwi:
    return Kiwi()


@st.cache_resource
def load_sudachi():
    return dictionary.Dictionary().create()


@st.cache_resource
def load_spacy_english():
    return spacy.load("en_core_web_sm")


JAPANESE_LEMMA_ALIASES = {
    "みる": "見る",
    "見れる": "見る",
    "みれる": "見る",
}


def make_korean_base_form(form: str, tag: str) -> str:
    if tag.startswith(("VV", "VA", "VX", "VCP", "VCN")):
        return f"{form}다"
    if tag == "SL":
        return form.lower()
    return form


def normalize_japanese_lemma(
    dictionary_form: str,
    normalized_form: str,
    major_pos: str,
) -> str:
    candidate = normalized_form

    if not candidate or candidate == "*":
        candidate = dictionary_form

    if not candidate or candidate == "*":
        candidate = ""

    if major_pos in {"動詞", "形容詞", "形状詞", "助動詞"}:
        return JAPANESE_LEMMA_ALIASES.get(candidate, candidate)

    return candidate


def analyze_korean_tokens(text: str) -> list[dict]:
    tokens: list[dict] = []

    for token in load_kiwi().tokenize(text):
        form = token.form.strip()
        if not form:
            continue

        start = int(token.start)
        end = start + int(token.len)
        tokens.append(
            {
                "surface": text[start:end],
                "lemma": make_korean_base_form(form, token.tag),
                "pos": token.tag,
                "major_pos": korean_major_pos(token.tag),
                "detailed_pos": KOREAN_POS_NAMES.get(token.tag, token.tag),
                "start": start,
                "end": end,
            }
        )

    return tokens


def analyze_japanese_tokens(text: str) -> list[dict]:
    tokens: list[dict] = []
    sudachi = load_sudachi()

    for morpheme in sudachi.tokenize(text, tokenizer.Tokenizer.SplitMode.B):
        form = morpheme.surface()
        if not form.strip():
            continue

        pos_tuple = tuple(morpheme.part_of_speech())
        major_pos = pos_tuple[0] if pos_tuple else "未分類"
        if major_pos == "空白":
            continue

        dictionary_form = morpheme.dictionary_form()
        if not dictionary_form or dictionary_form == "*":
            dictionary_form = form

        normalized_form = morpheme.normalized_form()
        if not normalized_form or normalized_form == "*":
            normalized_form = dictionary_form

        lemma = normalize_japanese_lemma(
            dictionary_form,
            normalized_form,
            major_pos,
        )

        tokens.append(
            {
                "surface": form,
                "lemma": lemma,
                "pos": major_pos,
                "major_pos": major_pos,
                "detailed_pos": japanese_detailed_pos(pos_tuple),
                "start": int(morpheme.begin()),
                "end": int(morpheme.end()),
            }
        )

    return tokens


def analyze_english_tokens(text: str) -> list[dict]:
    tokens: list[dict] = []

    for token in load_spacy_english()(text):
        if token.is_space:
            continue

        lemma = token.lemma_.strip()
        if not lemma or lemma == "-PRON-":
            lemma = token.text

        tokens.append(
            {
                "surface": token.text,
                "lemma": lemma.lower(),
                "pos": token.pos_ or "X",
                "major_pos": token.pos_ or "X",
                "detailed_pos": token.tag_ or "X",
                "start": int(token.idx),
                "end": int(token.idx + len(token.text)),
            }
        )

    return tokens


def analyze_tokens(text: str, language: str) -> list[dict]:
    if language == "한국어":
        return analyze_korean_tokens(text)
    if language == "일본어":
        return analyze_japanese_tokens(text)
    return analyze_english_tokens(text)


@st.cache_data(show_spinner=False)
def cached_analyze_tokens(
    text: str,
    language: str,
    cache_version: str,
) -> list[dict]:
    """
    언어별 토큰 분석 결과를 캐시합니다.

    cache_version은 반환 데이터 구조가 바뀔 때 이전 캐시를 무효화하기 위한 값입니다.
    """
    _ = cache_version
    return analyze_tokens(text, language)


def validate_token_schema(tokens: list[dict]) -> list[dict]:
    """
    캐시된 토큰 결과가 현재 검색 페이지의 품사 스키마를 따르는지 검사합니다.
    """
    required_fields = {
        "surface",
        "lemma",
        "pos",
        "major_pos",
        "detailed_pos",
        "start",
        "end",
    }

    for token in tokens:
        if not required_fields.issubset(token.keys()):
            raise ValueError("구형 토큰 캐시 구조가 감지되었습니다.")

    return tokens


def normalize_lemma_for_comparison(lemma: str, language: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(lemma).strip())
    if language == "영어":
        return normalized.casefold()
    return normalized


def extract_query_lemmas(query: str, language: str) -> list[str]:
    """검색어에서 비교에 사용할 핵심 기본형을 추출합니다."""
    analyzed = analyze_tokens(query, language)

    ignored_pos = {
        "한국어": {
            "JKS", "JKC", "JKG", "JKO", "JKB", "JKV", "JKQ", "JX", "JC",
            "EP", "EF", "EC", "ETN", "ETM", "SF", "SP", "SS", "SSO", "SSC",
            "SE", "SO", "SW",
        },
        "일본어": {"助詞", "助動詞", "補助記号", "記号", "空白"},
        "영어": {"PUNCT", "SYM", "SPACE"},
    }[language]

    content_lemmas = [
        normalize_lemma_for_comparison(token["lemma"], language)
        for token in analyzed
        if token["pos"] not in ignored_pos and str(token["lemma"]).strip()
    ]

    if content_lemmas:
        return list(dict.fromkeys(content_lemmas))

    direct = normalize_lemma_for_comparison(query, language)
    return [direct] if direct else []


def find_lemma_matches(
    text: str,
    target_lemmas: set[str],
    language: str,
) -> list[dict]:
    """기본형이 일치하는 토큰과 원문 위치·품사 정보를 반환합니다."""
    matches: list[dict] = []

    cached_tokens = cached_analyze_tokens(
        text,
        language,
        TOKEN_CACHE_VERSION,
    )

    try:
        tokens = validate_token_schema(cached_tokens)
    except ValueError:
        # 구형 캐시 구조가 감지되면 현재 분석 함수를 직접 실행합니다.
        tokens = analyze_tokens(text, language)

    for token in tokens:
        token_lemma = normalize_lemma_for_comparison(token["lemma"], language)

        if token_lemma in target_lemmas:
            matches.append(
                {
                    "surface": str(token["surface"]),
                    "lemma": str(token["lemma"]),
                    "major_pos": str(token["major_pos"]),
                    "detailed_pos": str(token["detailed_pos"]),
                    "start": int(token["start"]),
                    "end": int(token["end"]),
                }
            )

    return matches


# ------------------------------------------------------------
# 6. 검색 결과
# ------------------------------------------------------------
clean_search_text = search_text.strip()

if clean_search_text:
    try:
        target_lemmas: list[str] = []
        selected_major_pos = "전체"
        selected_detailed_pos = "전체"
        pos_frequency_df = pd.DataFrame()

        if search_mode == "원문 문자열 검색":
            occurrence_spans = comments_df["댓글"].apply(
                lambda text: find_occurrence_spans(
                    text=str(text),
                    query=clean_search_text,
                    case_sensitive=case_sensitive,
                    normalize_unicode=normalize_unicode,
                )
            )
            matched_lemmas_series = pd.Series(
                [[] for _ in range(len(comments_df))],
                index=comments_df.index,
            )
            matched_pos_series = pd.Series(
                [[] for _ in range(len(comments_df))],
                index=comments_df.index,
            )

        else:
            with st.spinner("검색어와 댓글의 기본형·품사를 분석하는 중입니다..."):
                target_lemmas = extract_query_lemmas(
                    clean_search_text,
                    analysis_language,
                )
                target_lemma_set = set(target_lemmas)

                all_lemma_matches = comments_df["댓글"].apply(
                    lambda text: find_lemma_matches(
                        str(text),
                        target_lemma_set,
                        analysis_language,
                    )
                )

            all_match_rows = [
                match
                for matches in all_lemma_matches
                for match in matches
            ]

            if all_match_rows:
                all_match_df = pd.DataFrame(all_match_rows)

                if analysis_language == "한국어":
                    major_order = KOREAN_POS_ORDER
                elif analysis_language == "일본어":
                    major_order = JAPANESE_POS_ORDER
                else:
                    major_order = ENGLISH_POS_ORDER

                major_options = ["전체"] + ordered_values(
                    all_match_df["major_pos"].tolist(),
                    major_order,
                )

                filter_col1, filter_col2 = st.columns(2)

                previous_major_pos = st.session_state.get(
                    "_previous_lemma_search_major_pos"
                )

                with filter_col1:
                    selected_major_pos = st.selectbox(
                        "품사 범주",
                        options=major_options,
                        key="lemma_search_major_pos",
                    )

                if previous_major_pos != selected_major_pos:
                    st.session_state["lemma_search_detailed_pos"] = "전체"
                    st.session_state["_previous_lemma_search_major_pos"] = (
                        selected_major_pos
                    )

                if selected_major_pos == "전체":
                    detail_source = all_match_df
                else:
                    detail_source = all_match_df[
                        all_match_df["major_pos"] == selected_major_pos
                    ]

                detailed_values = (
                    detail_source["detailed_pos"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                detailed_options = ["전체"] + sorted(detailed_values)

                current_detail_value = st.session_state.get(
                    "lemma_search_detailed_pos",
                    "전체",
                )

                if current_detail_value not in detailed_options:
                    st.session_state["lemma_search_detailed_pos"] = "전체"

                with filter_col2:
                    selected_detailed_pos = st.selectbox(
                        "세부 품사",
                        options=detailed_options,
                        key="lemma_search_detailed_pos",
                    )

                def apply_pos_filter(matches: list[dict]) -> list[dict]:
                    filtered = matches

                    if selected_major_pos != "전체":
                        filtered = [
                            match
                            for match in filtered
                            if match["major_pos"] == selected_major_pos
                        ]

                    if selected_detailed_pos != "전체":
                        filtered = [
                            match
                            for match in filtered
                            if match["detailed_pos"] == selected_detailed_pos
                        ]

                    return filtered

                filtered_match_series = all_lemma_matches.apply(apply_pos_filter)

                occurrence_spans = filtered_match_series.apply(
                    lambda matches: [
                        (match["start"], match["end"])
                        for match in matches
                    ]
                )
                matched_lemmas_series = filtered_match_series.apply(
                    lambda matches: [match["lemma"] for match in matches]
                )
                matched_pos_series = filtered_match_series.apply(
                    lambda matches: [
                        f'{match["major_pos"]} / {match["detailed_pos"]}'
                        for match in matches
                    ]
                )

                pos_frequency_df = (
                    all_match_df.groupby(
                        ["major_pos", "detailed_pos"],
                        as_index=False,
                    )
                    .size()
                    .rename(
                        columns={
                            "major_pos": "품사 범주",
                            "detailed_pos": "세부 품사",
                            "size": "빈도수",
                        }
                    )
                    .sort_values(
                        ["빈도수", "품사 범주", "세부 품사"],
                        ascending=[False, True, True],
                    )
                )
            else:
                occurrence_spans = pd.Series(
                    [[] for _ in range(len(comments_df))],
                    index=comments_df.index,
                )
                matched_lemmas_series = pd.Series(
                    [[] for _ in range(len(comments_df))],
                    index=comments_df.index,
                )
                matched_pos_series = pd.Series(
                    [[] for _ in range(len(comments_df))],
                    index=comments_df.index,
                )

    except OSError:
        if analysis_language == "영어":
            st.error(
                "spaCy 영어 모델(en_core_web_sm)을 불러오지 못했습니다. "
                "requirements.txt와 Streamlit 설치 로그를 확인해 주세요."
            )
            st.stop()
        raise

    occurrence_counts = occurrence_spans.apply(len)
    matched_mask = occurrence_counts > 0
    matched_comments = comments_df.loc[matched_mask].copy()
    matched_comments["검색 항목 출현 횟수"] = occurrence_counts.loc[matched_mask].astype(int)
    matched_comments["_검색_범위"] = occurrence_spans.loc[matched_mask]
    matched_comments["_일치_기본형"] = matched_lemmas_series.loc[matched_mask]
    matched_comments["_일치_품사"] = matched_pos_series.loc[matched_mask]

    total_occurrences = int(matched_comments["검색 항목 출현 횟수"].sum())

    st.markdown(
        """
        <div class="section-label">
            <span class="section-number">2</span>
            검색 결과
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_col1, metric_col2, metric_col3 = st.columns(3)

    with metric_col1:
        metric_label = "검색 문자열" if search_mode == "원문 문자열 검색" else "검색 기본형"
        st.metric(metric_label, clean_search_text)

    with metric_col2:
        st.metric("전체 출현 빈도", f"{total_occurrences:,}회")

    with metric_col3:
        st.metric("포함된 댓글", f"{len(matched_comments):,}개")

    if search_mode == "기본형 검색":
        if target_lemmas:
            st.caption(
                "분석된 검색 기본형: "
                + ", ".join(html.escape(lemma) for lemma in target_lemmas)
            )
        else:
            st.warning("검색어에서 유효한 기본형을 추출하지 못했습니다.")

        if not pos_frequency_df.empty:
            st.markdown("#### 기본형의 품사별 빈도")

            display_pos_frequency = pos_frequency_df.copy()
            display_pos_frequency["선택 조건"] = ""

            condition_mask = pd.Series(True, index=display_pos_frequency.index)

            if selected_major_pos != "전체":
                condition_mask &= (
                    display_pos_frequency["품사 범주"] == selected_major_pos
                )

            if selected_detailed_pos != "전체":
                condition_mask &= (
                    display_pos_frequency["세부 품사"] == selected_detailed_pos
                )

            display_pos_frequency.loc[condition_mask, "선택 조건"] = "✓"

            st.dataframe(
                display_pos_frequency[
                    ["품사 범주", "세부 품사", "빈도수", "선택 조건"]
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "품사별 빈도표는 해당 기본형의 전체 품사 분포를 보여 줍니다. "
                "위 필터를 적용하면 검색 빈도와 댓글 목록에는 선택한 품사만 반영됩니다."
            )

    if matched_comments.empty:
        empty_message = (
            "입력한 문자열이 사용된 댓글이 없습니다."
            if search_mode == "원문 문자열 검색"
            else "선택한 기본형과 품사 조건에 맞는 형태가 사용된 댓글이 없습니다."
        )
        st.info(empty_message)
    else:
        if search_mode == "원문 문자열 검색":
            normalization_note = (
                " 표기 폭 정규화가 켜져 있으므로 전각·반각 차이는 같은 표기로 처리됩니다."
                if normalize_unicode
                else ""
            )
            st.caption(
                "한 댓글에서 같은 문자열이 여러 번 나오면 모두 출현 빈도에 포함됩니다."
                + normalization_note
            )
        else:
            selected_condition = "전체 품사"
            if selected_major_pos != "전체":
                selected_condition = selected_major_pos
            if selected_detailed_pos != "전체":
                selected_condition += f" / {selected_detailed_pos}"

            st.caption(
                f"현재 검색 조건: {selected_condition}. "
                "댓글에 실제로 나타난 활용형·굴절형을 강조합니다."
            )

        st.markdown(
            """
            <div class="section-label">
                <span class="section-number">3</span>
                검색 항목이 사용된 댓글
            </div>
            """,
            unsafe_allow_html=True,
        )

        matched_comments = matched_comments.sort_values(
            "검색 항목 출현 횟수",
            ascending=False,
            kind="stable",
        )

        for row_number, (_, row) in enumerate(matched_comments.iterrows(), start=1):
            author = row.get("작성자 ID", "작성자 정보 없음")
            published_at = row.get("작성 일시", "")
            likes = row.get("좋아요", row.get("좋아요 수", 0))
            occurrence_count = int(row.get("검색 항목 출현 횟수", 0))
            comment_text = str(row.get("댓글", ""))
            spans = row.get("_검색_범위", [])

            safe_author = html.escape(str(author))
            safe_date = html.escape(str(published_at))
            safe_likes = html.escape(str(likes))
            highlighted_comment = highlight_text(comment_text, spans)

            match_label = (
                "검색 문자열"
                if search_mode == "원문 문자열 검색"
                else "기본형·품사 일치"
            )

            lemma_note = ""
            if search_mode == "기본형 검색":
                matched_lemmas = list(dict.fromkeys(row.get("_일치_기본형", [])))
                matched_pos = list(dict.fromkeys(row.get("_일치_품사", [])))

                note_parts = []
                if matched_lemmas:
                    note_parts.append(
                        "기본형: "
                        + ", ".join(html.escape(value) for value in matched_lemmas)
                    )
                if matched_pos:
                    note_parts.append(
                        "품사: "
                        + ", ".join(html.escape(value) for value in matched_pos)
                    )

                if note_parts:
                    lemma_note = " · " + " · ".join(note_parts)

            card_html = (
                f'<article class="comment-card">'
                f'<div class="comment-meta">'
                f'{row_number}. {safe_author}'
                f' · {safe_date}'
                f' · 좋아요 {safe_likes}'
                f' · {match_label} {occurrence_count}회'
                f'{lemma_note}'
                f'</div>'
                f'<div class="comment-text">{highlighted_comment}</div>'
                f'</article>'
            )

            st.markdown(
                card_html,
                unsafe_allow_html=True,
            )
else:
    st.info("검색어를 입력하면 결과가 표시됩니다.")
