import streamlit as st
import requests
import re
import json
import pandas as pd
from datetime import date, timedelta, time as dtime
from groq import Groq

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
    try:
        from folium.plugins import AntPath
        ANTPATH_AVAILABLE = True
    except Exception:
        ANTPATH_AVAILABLE = False
except ImportError:
    FOLIUM_AVAILABLE = False
    ANTPATH_AVAILABLE = False

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI 여행 플래너", page_icon="✈️", layout="wide")

# ── Session state init ────────────────────────────────────────────────────────
for _k, _v in [
    ("acc_list", []), ("acc_search_results", []), ("place_details_cache", {}),
    ("arr_selected", None), ("arr_results", []),
    ("dep_selected", None), ("dep_results", []),
    ("poi_shopping_list", []), ("poi_food_list", []), ("poi_sight_list", []),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── API keys ──────────────────────────────────────────────────────────────────
def get_groq_key() -> str:
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    import os
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        st.error("GROQ_API_KEY를 찾을 수 없습니다. .streamlit/secrets.toml에 추가해주세요.")
        st.stop()
    return key


def get_google_key() -> str:
    try:
        return st.secrets.get("GOOGLE_MAPS_API_KEY", "")
    except Exception:
        import os
        return os.getenv("GOOGLE_MAPS_API_KEY", "")


# ── Geocoding ─────────────────────────────────────────────────────────────────
def get_coordinates(place: str, google_key: str = "") -> dict | None:
    if not place.strip():
        return None
    if google_key:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        try:
            resp = requests.get(url, params={"address": place, "key": google_key}, timeout=10)
            data = resp.json()
            if data.get("status") == "OK":
                loc = data["results"][0]["geometry"]["location"]
                return {"name": place, "lat": loc["lat"], "lng": loc["lng"]}
        except Exception as e:
            st.warning(f"Google 지오코딩 실패 '{place}': {e}. Nominatim으로 전환합니다.")
    url = "https://nominatim.openstreetmap.org/search"
    try:
        resp = requests.get(url, params={"q": place, "format": "json", "limit": 1},
                            headers={"User-Agent": "AI-Travel-Planner/1.0"}, timeout=10)
        results = resp.json()
        if results:
            return {"name": place, "lat": float(results[0]["lat"]), "lng": float(results[0]["lon"])}
    except Exception as e:
        st.warning(f"Nominatim 지오코딩 실패 '{place}': {e}")
    return None


def geocode_places(places: list[str], google_key: str) -> dict:
    coords = {}
    for place in places:
        if place.strip():
            coords[place] = get_coordinates(place, google_key)
    return coords


# ── Place Details ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_place_details(place_name: str, dest_hint: str, google_key: str) -> dict | None:
    """Find Place + Place Details API. Returns result dict or None."""
    if not google_key:
        return None
    try:
        find_resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/findplacefromtext/json",
            params={"input": f"{place_name} {dest_hint}", "inputtype": "textquery",
                    "fields": "place_id", "key": google_key}, timeout=8)
        candidates = find_resp.json().get("candidates", [])
        if not candidates:
            return None
        place_id = candidates[0]["place_id"]
        det_resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params={"place_id": place_id,
                    "fields": "name,rating,user_ratings_total,opening_hours,photos,formatted_address",
                    "key": google_key, "language": "ko"}, timeout=8)
        return det_resp.json().get("result") or None
    except Exception:
        return None


def get_place_photo_url(photo_reference: str, google_key: str, max_width: int = 400) -> str:
    return (f"https://maps.googleapis.com/maps/api/place/photo"
            f"?maxwidth={max_width}&photo_reference={photo_reference}&key={google_key}")


def render_place_card(place_name: str, dest_hint: str, google_key: str):
    """Render a compact info card for the selected place."""
    if not place_name:
        return
    if not google_key:
        with st.container(border=True):
            st.markdown(f"**📍 {place_name}**")
            # Nominatim으로 기본 주소 조회
            cache = st.session_state["place_details_cache"]
            _key = f"nom_{place_name}"
            if _key not in cache:
                try:
                    _r = requests.get(
                        "https://nominatim.openstreetmap.org/search",
                        params={"q": f"{place_name} {dest_hint}".strip(),
                                "format": "json", "limit": 1},
                        headers={"User-Agent": "AI-Travel-Planner/1.0"},
                        timeout=5,
                    )
                    _hits = _r.json()
                    cache[_key] = _hits[0].get("display_name", "") if _hits else ""
                except Exception:
                    cache[_key] = ""
                st.session_state["place_details_cache"] = cache
            addr = cache.get(_key, "")
            if addr:
                st.caption(addr[:120])
            else:
                st.caption("주소 정보 없음 — Google Maps API 키 등록 시 사진·평점·영업시간 표시")
        return

    cache = st.session_state["place_details_cache"]
    if place_name not in cache:
        with st.spinner(f"'{place_name}' 정보 조회 중..."):
            cache[place_name] = get_place_details(place_name, dest_hint, google_key)
        st.session_state["place_details_cache"] = cache

    details = cache.get(place_name)
    if not details:
        st.info(f"📍 선택됨: **{place_name}** — Google 상세 정보 없음")
        return

    with st.container(border=True):
        photos = details.get("photos", [])
        if photos:
            col_photo, col_info = st.columns([1, 2])
            with col_photo:
                try:
                    st.image(get_place_photo_url(photos[0]["photo_reference"], google_key),
                             use_container_width=True)
                except Exception:
                    pass
        else:
            col_info = st.container()

        with col_info:
            st.markdown(f"**{details.get('name', place_name)}**")
            rating = details.get("rating")
            reviews = details.get("user_ratings_total")
            if rating:
                st.write(f"⭐ {rating}" + (f" ({reviews:,}개 리뷰)" if reviews else ""))
            addr = details.get("formatted_address", "")
            if addr:
                st.caption(addr)
            hours = details.get("opening_hours", {})
            if hours.get("open_now") is not None:
                st.write("🟢 영업 중" if hours["open_now"] else "🔴 영업 종료")
            if hours.get("weekday_text"):
                with st.expander("영업시간"):
                    for line in hours["weekday_text"]:
                        st.write(line)


# ── Nominatim: Accommodation Search (free, no API key) ───────────────────────
def search_accommodations_nominatim(query: str) -> list[dict]:
    """Search real accommodations via OpenStreetMap Nominatim — free, no key needed."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 5,
                    "addressdetails": 1, "extratags": 1},
            headers={"User-Agent": "AI-Travel-Planner/1.0"},
            timeout=10,
        )
        results = []
        for r in resp.json():
            name = r.get("display_name", "").split(",")[0].strip()
            address = r.get("display_name", "")
            results.append({
                "name": name,
                "address": address,
                "place_id": str(r.get("place_id", "")),
                "lat": float(r["lat"]),
                "lng": float(r["lon"]),
                "rating": 0,
            })
        return results
    except Exception as e:
        st.warning(f"숙소 검색 실패: {e}")
        return []


# ── Google Places: Accommodation Search ──────────────────────────────────────
def search_accommodations(query: str, google_key: str) -> list[dict]:
    if not query.strip():
        return []
    # Google Places (정확도 높음) — API 키 있을 때
    if google_key:
        try:
            resp = requests.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params={"query": query, "type": "lodging", "key": google_key},
                timeout=10,
            )
            data = resp.json()
            results = []
            for p in data.get("results", [])[:5]:
                results.append({
                    "name": p["name"],
                    "address": p.get("formatted_address", ""),
                    "place_id": p.get("place_id", ""),
                    "lat": p["geometry"]["location"]["lat"],
                    "lng": p["geometry"]["location"]["lng"],
                    "rating": p.get("rating", 0),
                })
            if results:
                return results
        except Exception:
            pass
    # Nominatim fallback (무료, API 키 불필요)
    return search_accommodations_nominatim(query)


# ── Google Places: Top Restaurants ───────────────────────────────────────────
def get_top_restaurants(destination: str, google_key: str, count: int = 8) -> list[dict]:
    if not google_key:
        return []
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    try:
        resp = requests.get(url, params={"query": f"best restaurant {destination}",
                                         "type": "restaurant", "key": google_key}, timeout=10)
        data = resp.json()
        results = [
            {"name": p["name"], "rating": p.get("rating", 0),
             "reviews": p.get("user_ratings_total", 0),
             "address": p.get("formatted_address", ""),
             "lat": p["geometry"]["location"]["lat"],
             "lng": p["geometry"]["location"]["lng"]}
            for p in data.get("results", [])
            if p.get("rating", 0) >= 4.5 and p.get("user_ratings_total", 0) >= 100
        ]
        results.sort(key=lambda x: (-x["rating"], -x["reviews"]))
        return results[:count]
    except Exception as e:
        st.warning(f"레스토랑 정보 조회 실패: {e}")
        return []


# ── Google Distance Matrix: Transit hints ────────────────────────────────────
def get_transit_hints(coords: dict, google_key: str) -> str:
    if not google_key:
        return ""
    valid = [(name, info) for name, info in coords.items() if info]
    if len(valid) < 2:
        return ""
    hints = []
    for i in range(min(len(valid) - 1, 10)):
        o_name, o = valid[i]
        d_name, d = valid[i + 1]
        try:
            url = "https://maps.googleapis.com/maps/api/distancematrix/json"
            params = {"origins": f"{o['lat']},{o['lng']}",
                      "destinations": f"{d['lat']},{d['lng']}",
                      "mode": "transit", "key": google_key}
            resp = requests.get(url, params=params, timeout=10)
            elem = resp.json().get("rows", [{}])[0].get("elements", [{}])[0]
            if elem.get("status") == "OK":
                hints.append(
                    f"  - {o_name} → {d_name}: 대중교통 약 {elem['duration']['text']} ({elem['distance']['text']})"
                )
        except Exception:
            pass
    if hints:
        return "\n## 이동 시간 참고 (Google Maps)\n" + "\n".join(hints)
    return ""


# ── Accommodation per day ─────────────────────────────────────────────────────
def get_acc_for_date(target: date, acc_list: list[dict]) -> str:
    for acc in acc_list:
        name = str(acc.get("name") or acc.get("숙소명", "")).strip()
        ci = acc.get("checkin") or acc.get("체크인")
        co = acc.get("checkout") or acc.get("체크아웃")
        if not name or not ci or not co:
            continue
        if isinstance(ci, str):
            try: ci = date.fromisoformat(str(ci))
            except: continue
        if isinstance(co, str):
            try: co = date.fromisoformat(str(co))
            except: continue
        if ci <= target < co:
            return name
    if acc_list:
        return str(acc_list[0].get("name") or acc_list[0].get("숙소명", "미정"))
    return "미정"


# ── Switzerland / Dongshin constants ─────────────────────────────────────────
DONGSHIN_JUNGFRAU_INFO = """
## 🇰🇷 스위스 교통 패스 완전 가이드 (한국인 기준)

### ⚠️ 핵심 원칙
스위스 교통 패스는 **적용 구역이 다르므로 반드시 두 가지를 조합**해야 합니다.
- **전국 이동** (취리히·루체른·베른·인터라켄 등 SBB 열차): Swiss Travel Pass 또는 Half Fare Card
- **융프라우 지역 산악 구간** (융프라우요흐·피르스트·쉬니게플라테 등): 동신항운 VIP패스 (한국인 전용 특가)

---

### 1️⃣ 전국 이동 패스 비교

| 패스명 | 기간 | 2등석 | 1등석 | 포함 내용 | 비고 |
|--------|------|------|------|---------|------|
| Swiss Travel Pass | 3일 | CHF 244 | CHF 390 | SBB 전국 열차+트램+버스+유람선 무제한 | 뮤지엄 500곳 무료 |
| Swiss Travel Pass | 4일 | CHF 275 | CHF 440 | 동일 | |
| Swiss Travel Pass | 6일 | CHF 321 | CHF 513 | 동일 | |
| Swiss Travel Pass | 8일 | CHF 365 | CHF 584 | 동일 | |
| Half Fare Card | 1개월 | CHF 120 | — | 전국 모든 교통 50% 할인 | 개별 구매 시 유리 |

> **Swiss Travel Pass 주의**: 융프라우요흐는 25% 할인만 적용 (무료 아님).

---

### 2️⃣ 융프라우 지역 패스 비교

| 패스명 | 구매처 | 유효기간 | 가격 | 포함 구간 |
|--------|--------|---------|------|---------|
| **동신항운 겨울 VIP패스** 🇰🇷 | jungfrau.co.kr | 2025-11-29~2026-04-06 | 800→**240 CHF** | 융프라우요흐 왕복 포함 **5개 구간** 탑승+특별 탑승 |
| **동신항운 여름 VIP패스** 🇰🇷 | jungfrau.co.kr | 2026-04-03~2026-11-29 | 800→**245 CHF** | 융프라우요흐 왕복 포함 **7개 구간** 탑승+특별 탑승 |
| 융프라우요흐 단일 왕복 | 현지 | — | CHF 224~261 | 융프라우요흐 1회 왕복만 |
| Harder Kulm | 현지 | 2026-04-03~11-29 | CHF 38~44 | 하더쿨름 왕복 |
| Schynige Platte | 현지 | 2026-06-13~10-25 | CHF 75.60 | 쉬니게플라테 왕복 |
| First (피르스트) | 현지 | 2025-11-29~2026-10-25 | CHF 72~76 | 피르스트 곤돌라 왕복 |

> 🇰🇷 **동신항운 VIP패스**: 한국인만 구매 가능, 현지 구매 불가 → 한국 출발 전 반드시 사전 구매.

---

### 3️⃣ 일정별 최적 조합 추천

| 여행 패턴 | 추천 조합 | 예상 절약 |
|----------|---------|---------|
| 취리히·루체른+융프라우 6일 | Swiss Travel Pass 6일 + 동신항운 VIP패스 | 개별 구매 대비 약 200 CHF 절약 |
| 융프라우 지역만 집중 3일 | Half Fare Card + 동신항운 VIP패스 | Swiss Travel Pass보다 약 100 CHF 절약 |
| 전국 일주 8일 이상 | Swiss Travel Pass 8일 + 동신항운 VIP패스 | 편의성+비용 최적 |

- 동신항운 구매: https://www.jungfrau.co.kr (온라인 사전 구매 필수)
- Swiss Travel Pass 구매: 한국 내 여행사 또는 SBB 공식 사이트
"""

SWITZERLAND_KEYWORDS = ["스위스", "switzerland", "swiss", "융프라우", "jungfrau",
                        "인터라켄", "interlaken", "취리히", "zurich", "제네바", "geneva",
                        "루체른", "lucerne", "베른", "bern", "체르마트", "zermatt"]


def get_destination_extra_info(destination: str) -> str:
    if any(kw in destination.lower() for kw in SWITZERLAND_KEYWORDS):
        return DONGSHIN_JUNGFRAU_INFO
    return ""


# ── Airport Database ──────────────────────────────────────────────────────────
AIRPORT_DB = [
    # 한국
    {"iata": "ICN", "name": "인천국제공항", "city": "인천/서울", "country": "한국", "dest": "한국 서울"},
    {"iata": "GMP", "name": "김포국제공항", "city": "서울", "country": "한국", "dest": "한국 서울"},
    {"iata": "PUS", "name": "김해국제공항", "city": "부산", "country": "한국", "dest": "한국 부산"},
    {"iata": "CJU", "name": "제주국제공항", "city": "제주", "country": "한국", "dest": "한국 제주"},
    # 일본
    {"iata": "NRT", "name": "나리타국제공항", "city": "도쿄", "country": "일본", "dest": "일본 도쿄"},
    {"iata": "HND", "name": "하네다공항", "city": "도쿄", "country": "일본", "dest": "일본 도쿄"},
    {"iata": "KIX", "name": "간사이국제공항", "city": "오사카", "country": "일본", "dest": "일본 오사카"},
    {"iata": "ITM", "name": "이타미공항", "city": "오사카", "country": "일본", "dest": "일본 오사카"},
    {"iata": "NGO", "name": "주부센트레아국제공항", "city": "나고야", "country": "일본", "dest": "일본 나고야"},
    {"iata": "FUK", "name": "후쿠오카공항", "city": "후쿠오카", "country": "일본", "dest": "일본 후쿠오카"},
    {"iata": "CTS", "name": "신치토세공항", "city": "삿포로", "country": "일본", "dest": "일본 삿포로"},
    {"iata": "OKA", "name": "나하공항", "city": "오키나와", "country": "일본", "dest": "일본 오키나와"},
    {"iata": "HIJ", "name": "히로시마공항", "city": "히로시마", "country": "일본", "dest": "일본 히로시마"},
    # 중국 / 홍콩 / 마카오
    {"iata": "PEK", "name": "베이징 수도국제공항", "city": "베이징", "country": "중국", "dest": "중국 베이징"},
    {"iata": "PKX", "name": "베이징 다싱국제공항", "city": "베이징", "country": "중국", "dest": "중국 베이징"},
    {"iata": "PVG", "name": "상하이 푸동국제공항", "city": "상하이", "country": "중국", "dest": "중국 상하이"},
    {"iata": "SHA", "name": "상하이 훙차오국제공항", "city": "상하이", "country": "중국", "dest": "중국 상하이"},
    {"iata": "CAN", "name": "광저우 바이윈국제공항", "city": "광저우", "country": "중국", "dest": "중국 광저우"},
    {"iata": "SZX", "name": "선전 바오안국제공항", "city": "선전", "country": "중국", "dest": "중국 선전"},
    {"iata": "CTU", "name": "청두 솽류국제공항", "city": "청두", "country": "중국", "dest": "중국 청두"},
    {"iata": "XIY", "name": "시안 셴양국제공항", "city": "시안", "country": "중국", "dest": "중국 시안"},
    {"iata": "HKG", "name": "홍콩국제공항", "city": "홍콩", "country": "홍콩", "dest": "홍콩"},
    {"iata": "MFM", "name": "마카오국제공항", "city": "마카오", "country": "마카오", "dest": "마카오"},
    # 동남아
    {"iata": "BKK", "name": "수완나품국제공항", "city": "방콕", "country": "태국", "dest": "태국 방콕"},
    {"iata": "DMK", "name": "돈므앙국제공항", "city": "방콕", "country": "태국", "dest": "태국 방콕"},
    {"iata": "HKT", "name": "푸껫국제공항", "city": "푸껫", "country": "태국", "dest": "태국 푸껫"},
    {"iata": "CNX", "name": "치앙마이국제공항", "city": "치앙마이", "country": "태국", "dest": "태국 치앙마이"},
    {"iata": "SIN", "name": "창이국제공항", "city": "싱가포르", "country": "싱가포르", "dest": "싱가포르"},
    {"iata": "KUL", "name": "쿠알라룸푸르국제공항", "city": "쿠알라룸푸르", "country": "말레이시아", "dest": "말레이시아 쿠알라룸푸르"},
    {"iata": "HAN", "name": "노이바이국제공항", "city": "하노이", "country": "베트남", "dest": "베트남 하노이"},
    {"iata": "SGN", "name": "떤선녓국제공항", "city": "호치민", "country": "베트남", "dest": "베트남 호치민"},
    {"iata": "DAD", "name": "다낭국제공항", "city": "다낭", "country": "베트남", "dest": "베트남 다낭"},
    {"iata": "MNL", "name": "니노이아키노국제공항", "city": "마닐라", "country": "필리핀", "dest": "필리핀 마닐라"},
    {"iata": "CEB", "name": "막탄세부국제공항", "city": "세부", "country": "필리핀", "dest": "필리핀 세부"},
    {"iata": "DPS", "name": "응우라라이국제공항", "city": "발리", "country": "인도네시아", "dest": "인도네시아 발리"},
    {"iata": "CGK", "name": "수카르노하타국제공항", "city": "자카르타", "country": "인도네시아", "dest": "인도네시아 자카르타"},
    # 유럽
    {"iata": "CDG", "name": "파리 샤를드골국제공항", "city": "파리", "country": "프랑스", "dest": "프랑스 파리"},
    {"iata": "LHR", "name": "런던 히드로공항", "city": "런던", "country": "영국", "dest": "영국 런던"},
    {"iata": "LGW", "name": "런던 게트윅공항", "city": "런던", "country": "영국", "dest": "영국 런던"},
    {"iata": "FRA", "name": "프랑크푸르트국제공항", "city": "프랑크푸르트", "country": "독일", "dest": "독일 프랑크푸르트"},
    {"iata": "MUC", "name": "뮌헨국제공항", "city": "뮌헨", "country": "독일", "dest": "독일 뮌헨"},
    {"iata": "AMS", "name": "암스테르담 스히폴공항", "city": "암스테르담", "country": "네덜란드", "dest": "네덜란드 암스테르담"},
    {"iata": "FCO", "name": "로마 피우미치노공항", "city": "로마", "country": "이탈리아", "dest": "이탈리아 로마"},
    {"iata": "MXP", "name": "밀라노 말펜사공항", "city": "밀라노", "country": "이탈리아", "dest": "이탈리아 밀라노"},
    {"iata": "BCN", "name": "바르셀로나국제공항", "city": "바르셀로나", "country": "스페인", "dest": "스페인 바르셀로나"},
    {"iata": "MAD", "name": "마드리드 바라하스공항", "city": "마드리드", "country": "스페인", "dest": "스페인 마드리드"},
    {"iata": "VIE", "name": "빈 슈베하트국제공항", "city": "빈", "country": "오스트리아", "dest": "오스트리아 빈"},
    {"iata": "ZRH", "name": "취리히공항", "city": "취리히", "country": "스위스", "dest": "스위스 취리히"},
    {"iata": "GVA", "name": "제네바 코앵트랭국제공항", "city": "제네바", "country": "스위스", "dest": "스위스 제네바"},
    {"iata": "IST", "name": "이스탄불국제공항", "city": "이스탄불", "country": "튀르키예", "dest": "튀르키예 이스탄불"},
    {"iata": "ATH", "name": "아테네 엘레프테리오스 베니젤로스공항", "city": "아테네", "country": "그리스", "dest": "그리스 아테네"},
    {"iata": "PRG", "name": "프라하 바클라프 하벨공항", "city": "프라하", "country": "체코", "dest": "체코 프라하"},
    {"iata": "BUD", "name": "부다페스트 페렌츠 리스트공항", "city": "부다페스트", "country": "헝가리", "dest": "헝가리 부다페스트"},
    # 북미
    {"iata": "LAX", "name": "로스앤젤레스국제공항", "city": "로스앤젤레스", "country": "미국", "dest": "미국 로스앤젤레스"},
    {"iata": "JFK", "name": "존F케네디국제공항", "city": "뉴욕", "country": "미국", "dest": "미국 뉴욕"},
    {"iata": "SFO", "name": "샌프란시스코국제공항", "city": "샌프란시스코", "country": "미국", "dest": "미국 샌프란시스코"},
    {"iata": "ORD", "name": "시카고 오헤어국제공항", "city": "시카고", "country": "미국", "dest": "미국 시카고"},
    {"iata": "SEA", "name": "시애틀 터코마국제공항", "city": "시애틀", "country": "미국", "dest": "미국 시애틀"},
    {"iata": "LAS", "name": "해리리드국제공항", "city": "라스베이거스", "country": "미국", "dest": "미국 라스베이거스"},
    {"iata": "HNL", "name": "호놀룰루국제공항", "city": "호놀룰루 (하와이)", "country": "미국", "dest": "미국 하와이"},
    {"iata": "YVR", "name": "밴쿠버국제공항", "city": "밴쿠버", "country": "캐나다", "dest": "캐나다 밴쿠버"},
    {"iata": "YYZ", "name": "토론토 피어슨국제공항", "city": "토론토", "country": "캐나다", "dest": "캐나다 토론토"},
    # 오세아니아
    {"iata": "SYD", "name": "시드니 킹스포드스미스공항", "city": "시드니", "country": "호주", "dest": "호주 시드니"},
    {"iata": "MEL", "name": "멜버른공항", "city": "멜버른", "country": "호주", "dest": "호주 멜버른"},
    {"iata": "AKL", "name": "오클랜드국제공항", "city": "오클랜드", "country": "뉴질랜드", "dest": "뉴질랜드 오클랜드"},
    # 중동
    {"iata": "DXB", "name": "두바이국제공항", "city": "두바이", "country": "UAE", "dest": "UAE 두바이"},
    {"iata": "DOH", "name": "하마드국제공항", "city": "도하", "country": "카타르", "dest": "카타르 도하"},
    {"iata": "AUH", "name": "아부다비국제공항", "city": "아부다비", "country": "UAE", "dest": "UAE 아부다비"},
]


def search_airports_local(query: str) -> list[dict]:
    q = query.lower().strip()
    if not q:
        return []
    scored = []
    for ap in AIRPORT_DB:
        s = 0
        if q == ap["iata"].lower():
            s += 5
        elif q in ap["iata"].lower():
            s += 3
        if q in ap["name"].lower():
            s += 2
        if q in ap["city"].lower():
            s += 2
        if q in ap["country"].lower():
            s += 1
        if s > 0:
            scored.append((s, ap))
    scored.sort(key=lambda x: -x[0])
    return [r[1] for r in scored[:6]]


def search_airports(query: str, google_key: str) -> list[dict]:
    """Search local DB first; fallback to Google Places if empty."""
    results = search_airports_local(query)
    if results:
        return results
    if not google_key:
        return []
    try:
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={"query": f"{query} airport", "type": "airport",
                    "key": google_key, "language": "ko"},
            timeout=10,
        )
        data = resp.json()
        out = []
        for p in data.get("results", [])[:5]:
            out.append({
                "name": p["name"],
                "address": p.get("formatted_address", ""),
                "lat": p["geometry"]["location"]["lat"],
                "lng": p["geometry"]["location"]["lng"],
                "iata": "",
                "city": "",
                "country": "",
                "dest": "",
            })
        return out
    except Exception:
        return []


# ── LLM Itinerary Generation ──────────────────────────────────────────────────
def generate_itinerary(
    destination: str,
    start_date: date,
    end_date: date,
    acc_list: list[dict],
    poi_shopping: list[str],
    poi_food: list[str],
    poi_sightseeing: list[str],
    theme: str,
    coords: dict,
    top_restaurants: list[dict],
    transit_hints: str,
    api_key: str,
    arr_airport: str = "",
    arr_date: date | None = None,
    arr_time: dtime | None = None,
    dep_airport: str = "",
    dep_date: date | None = None,
    dep_time: dtime | None = None,
    day_start: dtime | None = None,
    day_end: dtime | None = None,
) -> str:
    num_days = (end_date - start_date).days + 1

    acc_schedule = "\n".join(
        f"  - {(start_date + timedelta(days=i)).strftime('%Y-%m-%d')} (Day {i+1}): "
        f"{get_acc_for_date(start_date + timedelta(days=i), acc_list)}"
        for i in range(num_days)
    )

    coord_text = "\n".join(
        f"  - {p}: lat={v['lat']:.5f}, lng={v['lng']:.5f}" if v else f"  - {p}: 좌표 없음"
        for p, v in coords.items()
    ) or "  (없음)"

    restaurant_block = ""
    if top_restaurants:
        restaurant_block = "\n## Google Maps 고평점 맛집 (4.5+★, 일정에 적극 반영)\n" + "\n".join(
            f"  - {r['name']} ★{r['rating']} ({r['reviews']:,}개 리뷰) | {r['address']}"
            for r in top_restaurants
        )

    all_pois = poi_shopping + poi_food + poi_sightseeing
    poi_text = ", ".join(all_pois) if all_pois else "없음"

    # ── Flight block ──────────────────────────────────────────────────────────
    flight_block = ""
    if arr_airport or dep_airport:
        flight_block = "\n## ✈️ 항공편 정보 (일정에 반드시 반영)\n"
        if arr_airport and arr_date and arr_time:
            flight_block += (
                f"- **도착편**: {arr_airport} | "
                f"도착일 {arr_date.strftime('%Y-%m-%d')} {arr_time.strftime('%H:%M')}\n"
                f"  → **Day 1 일정은 공항 도착({arr_time.strftime('%H:%M')}) 이후부터 시작**하며, "
                f"첫 번째 장소는 반드시 도착 공항({arr_airport})으로 설정하세요.\n"
                f"  → 입국 심사·수하물 수취·공항 이동 시간(최소 1시간) 포함하여 일정 구성하세요.\n"
            )
        if dep_airport and dep_date and dep_time:
            from datetime import datetime, timedelta as td
            dep_dt = datetime.combine(dep_date, dep_time)
            cutoff = (dep_dt - td(hours=3)).strftime('%H:%M')
            flight_block += (
                f"- **출발편**: {dep_airport} | "
                f"출발일 {dep_date.strftime('%Y-%m-%d')} {dep_time.strftime('%H:%M')}\n"
                f"  → **마지막 날(Day {num_days}) 일정은 {cutoff}까지 공항({dep_airport}) 도착**으로 마무리하세요.\n"
                f"  → 공항까지 이동 시간을 역산하여 마지막 관광지 출발 시간을 계산하고 명시하세요.\n"
                f"  → 마지막 날 마지막 행은 반드시 '{dep_airport} 도착 (탑승 수속)'으로 끝내세요.\n"
            )

    # ── Active hours block ────────────────────────────────────────────────────
    ds = day_start.strftime('%H:%M') if day_start else "09:00"
    de = day_end.strftime('%H:%M') if day_end else "22:00"
    active_hours_block = (
        f"\n## ⏰ 일일 활동 가능 시간\n"
        f"- 하루 시작: **{ds}** / 하루 종료: **{de}**\n"
        f"- 모든 일정은 반드시 이 시간대 안에서만 구성하세요.\n"
        f"- 식당·명소 영업시간이 이 범위를 벗어나면 해당 장소는 제외하세요.\n"
    )

    # Truncate large optional blocks to save tokens
    _restaurants = restaurant_block[:800] if restaurant_block else ""
    _transit = transit_hints[:400] if transit_hints else ""

    prompt = f"""[규칙] 모든 출력은 한국어만 사용. 한자 금지.
당신은 전문 여행 플래너입니다. 아래 조건으로 실용적인 여행 일정을 작성하세요.

## 여행 정보
- 여행지: {destination} | {start_date} ~ {end_date} ({num_days}일) | 테마: {theme}
- 쇼핑: {", ".join(poi_shopping) or "없음"} | 맛집: {", ".join(poi_food) or "없음"} | 관광: {", ".join(poi_sightseeing) or "없음"}
{flight_block}{active_hours_block}## 날짜별 숙소
{acc_schedule}
## 좌표 (동선 최적화)
{coord_text}
{_restaurants}{_transit}{get_destination_extra_info(destination)}---

## 출력 형식 (각 Day 반드시 준수)

### Day N — YYYY-MM-DD — [소제목]

**숙소**: [숙소명]

| 시간 | 장소 | 활동 | 교통 (수단·소요·비용) | 팁/비용 |
|------|------|------|---------------------|---------|

🚇 **동선**: A ➔ [수단·분] ➔ B ➔ [수단·분] ➔ C

💡 **오늘의 팁**: tip1 / tip2 / tip3

<!-- ROUTE_JSON: ["장소명1", "장소명2"] -->

---

(전체 Day 완료 후)

## 🎫 교통 패스 추천
[추천 패스명, 가격, 절약액 — 2줄 이내]

## ⚠️ 예약 필수
- [장소: 방법]

---
## 작성 규칙
1. Day 1~{num_days} 전부 작성 ({ds}~{de} 시간대만)
2. 실제 존재하는 장소명·교통 노선명 사용
3. 각 Day는 해당 날짜 숙소 출발·귀착 (Day1·마지막날 공항 예외)
4. 식당은 이동 경로 인근·해당 시간 영업 중인 곳만 배치
5. 교통 패스는 절약 시에만 추천, 절약액 수치 명시
6. Day1: 도착+1시간 후 시작 / 마지막날: 출발 3시간 전 공항 도착
7. 각 Day 마지막에 ROUTE_JSON 태그 필수 (장소명은 위 좌표 목록과 동일하게)
"""

    client = Groq(api_key=api_key)
    with st.spinner("AI가 여행 일정을 생성 중입니다..."):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
    return response.choices[0].message.content


# ── Demo itinerary (UI test without LLM) ─────────────────────────────────────
def generate_demo_itinerary(destination: str, start_date: date,
                             end_date: date, acc_list: list) -> str:
    """Returns a template itinerary for UI/UX testing (no LLM call)."""
    num_days = (end_date - start_date).days + 1
    hotel = acc_list[0]["name"] if acc_list else "샘플 호텔"
    days_text = []
    places = [
        f"{destination} 중앙 광장",
        f"{destination} 전통 시장",
        f"{destination} 박물관",
        f"{destination} 공원",
        f"{destination} 쇼핑몰",
    ]
    for i in range(min(num_days, 5)):
        d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        p1, p2, p3 = places[i % 5], places[(i + 1) % 5], places[(i + 2) % 5]
        days_text.append(f"""### Day {i + 1} — {d} — 샘플 일정 {i + 1}

**숙소**: {hotel}

| 시간 | 장소 | 활동 | 교통 (수단·소요·비용) | 팁/비용 |
|------|------|------|---------------------|---------|
| 09:00 | {hotel} | 조식 후 출발 | - | 체크아웃 전 짐 맡기기 |
| 09:30 | {p1} | 오전 관광 | 지하철 15분, ₩500 | 오전 일찍 한산 |
| 11:30 | {p2} | 점심·쇼핑 | 도보 10분 | 현금 ₩30,000 준비 |
| 14:00 | {p3} | 오후 탐방 | 버스 10분, ₩500 | 입장료 ₩3,000 |
| 16:30 | {p1} 근처 카페 | 휴식 | 도보 5분 | 현지 특산 음료 |
| 19:00 | {hotel} 인근 식당 | 저녁식사 | 도보 10분 | 예약 권장 ₩25,000 |

🚇 **동선**: {hotel} ➔ [지하철·15분] ➔ {p1} ➔ [도보·10분] ➔ {p2} ➔ [버스·10분] ➔ {p3}

💡 **오늘의 팁**: 이른 아침 방문 추천 / 현금 준비 / 편한 신발 착용

<!-- ROUTE_JSON: ["{p1}", "{p2}", "{p3}"] -->

---""")
    result = "\n\n".join(days_text)
    result += f"""

## 🎫 교통 패스 추천
**1일 대중교통 패스** (₩8,000) — 일 교통비 ₩10,000 이상 예상 시 유리. 당일 현장 구매 가능.

## ⚠️ 예약 필수
- 인기 레스토랑: 방문 2일 전 앱/전화 예약

> 🧪 **데모 모드**: UI 테스트용 샘플입니다. 실제 AI 일정을 받으려면 사이드바에서 데모 모드를 해제하세요.
"""
    return result


# ── Parsing ───────────────────────────────────────────────────────────────────
def parse_days(itinerary: str) -> dict[str, str]:
    parts = re.split(r'(?=### Day \d+)', itinerary)
    days = {}
    for part in parts:
        m = re.match(r'### Day (\d+)', part)
        if m:
            days[f"Day {m.group(1)}"] = part.strip()
    return days


def extract_route_json(day_text: str) -> list[str]:
    m = re.search(r'<!--\s*ROUTE_JSON:\s*(\[.*?\])\s*-->', day_text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return []


def clean_route_tags(text: str) -> str:
    return re.sub(r'<!--\s*ROUTE_JSON:.*?-->', '', text, flags=re.DOTALL).strip()


# ── Schedule table parser ─────────────────────────────────────────────────────
def parse_schedule_table(day_text: str) -> pd.DataFrame:
    lines = [l.strip() for l in day_text.split('\n')]
    start = next((i for i, l in enumerate(lines)
                  if l.startswith('|') and ('시간' in l or '장소' in l)), -1)
    if start == -1:
        return pd.DataFrame()
    table_lines = []
    for line in lines[start:]:
        if line.startswith('|'):
            table_lines.append(line)
        elif table_lines:
            break
    if len(table_lines) < 3:
        return pd.DataFrame()

    def parse_row(line):
        return [c.strip() for c in line.split('|')[1:-1]]

    headers = parse_row(table_lines[0])
    rows = []
    for line in table_lines[2:]:
        row = parse_row(line)
        while len(row) < len(headers):
            row.append('')
        rows.append(row[:len(headers)])
    valid = [r for r in rows if any(r)]
    return pd.DataFrame(valid, columns=headers) if valid else pd.DataFrame()


def find_coord(place_name: str, coords: dict) -> dict | None:
    if not place_name:
        return None
    if place_name in coords and coords[place_name]:
        return coords[place_name]
    pl = place_name.lower()
    for key, val in coords.items():
        if val and (pl in key.lower() or key.lower() in pl):
            return val
    return None


def extract_day_section(day_text: str, keyword: str) -> str:
    """Extract text from a keyword marker to the next section or ROUTE_JSON."""
    lines = day_text.split('\n')
    start = next((i for i, l in enumerate(lines) if keyword in l), -1)
    if start == -1:
        return ""
    result = []
    for line in lines[start + 1:]:
        if re.match(r'^#{2,4}\s', line) or '<!-- ROUTE_JSON' in line or line.strip() == '---':
            break
        result.append(line)
    return '\n'.join(result).strip()


# ── Folium map ────────────────────────────────────────────────────────────────
PULSE_CSS = (
    "<style>"
    "@keyframes mkPulse{"
    "0%{transform:scale(1);box-shadow:0 0 0 0 rgba(255,200,0,0.7)}"
    "70%{transform:scale(1.35);box-shadow:0 0 0 10px rgba(255,200,0,0)}"
    "100%{transform:scale(1);box-shadow:0 0 0 0 rgba(255,200,0,0)}}"
    ".mk-pulse{animation:mkPulse 1.2s infinite ease-in-out;}"
    "</style>"
)


def build_day_map(route_places: list[str], coords: dict,
                  highlighted_place: str | None = None,
                  hotel_names: set | None = None,
                  airport_names: set | None = None):
    if not FOLIUM_AVAILABLE or not route_places:
        return None
    points = []
    for place in route_places:
        c = find_coord(place, coords)
        if c:
            points.append((place, c["lat"], c["lng"]))
    if not points:
        return None

    center = [sum(p[1] for p in points) / len(points),
              sum(p[2] for p in points) / len(points)]
    m = folium.Map(location=center, zoom_start=13)
    m.get_root().header.add_child(folium.Element(PULSE_CSS))

    if len(points) > 1:
        latlngs = [(p[1], p[2]) for p in points]
        if ANTPATH_AVAILABLE:
            AntPath(latlngs, weight=4, color="#4A90D9", delay=600,
                    dash_array=[10, 20], pulse_color="#FFFFFF").add_to(m)
        else:
            folium.PolyLine(latlngs, color="#4A90D9", weight=3, opacity=0.8).add_to(m)

    hl_lower = highlighted_place.lower() if highlighted_place else ""
    hnames = {n.lower() for n in (hotel_names or set())}
    anames = {n.lower() for n in (airport_names or set())}

    for i, (name, lat, lng) in enumerate(points):
        nl = name.lower()
        is_hl = bool(hl_lower and (hl_lower in nl or nl in hl_lower))
        is_hotel = nl in hnames
        is_airport = nl in anames

        if is_hl:
            bg, size, pulse_cls, label = "#F39C12", 36, "mk-pulse", str(i + 1)
            m.location = [lat, lng]
        elif is_airport:
            bg, size, pulse_cls, label = "#7F8C8D", 32, "", "✈"
        elif is_hotel:
            bg, size, pulse_cls, label = "#8E44AD", 32, "", "🏨"
        elif i == 0:
            bg, size, pulse_cls, label = "#E74C3C", 28, "", str(i + 1)
        elif i == len(points) - 1:
            bg, size, pulse_cls, label = "#2ECC71", 28, "", str(i + 1)
        else:
            bg, size, pulse_cls, label = "#3498DB", 28, "", str(i + 1)

        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(f"<b>{i+1}. {name}</b>", max_width=220),
            tooltip=f"{i+1}. {name}",
            icon=folium.DivIcon(
                html=(
                    f'<div class="{pulse_cls}" style="background:{bg};color:white;'
                    f'border-radius:50%;width:{size}px;height:{size}px;'
                    f'display:flex;align-items:center;justify-content:center;'
                    f'font-weight:bold;font-size:{"13" if len(label) > 2 else "14"}px;'
                    f'border:2px solid white;'
                    f'box-shadow:0 2px {"8" if is_hl else "4"}px rgba(0,0,0,0.4);">'
                    f'{label}</div>'
                ),
                icon_size=(size, size), icon_anchor=(size // 2, size // 2),
            ),
        ).add_to(m)
    return m


# ── Airport Search & Select UI ───────────────────────────────────────────────
def render_airport_select(
    label: str, key_prefix: str, default_date: date, google_key: str
) -> tuple:
    """
    Renders an airport search → select → confirm UI.
    Returns (display_name, flight_date, flight_time) or (None, None, None).
    """
    selected = st.session_state.get(f"{key_prefix}_selected")

    if not selected:
        with st.form(key=f"{key_prefix}_search_form", border=False):
            col_q, col_btn = st.columns([4, 1])
            with col_q:
                q = st.text_input(
                    label,
                    placeholder="예: 간사이, KIX, 오사카, 인천",
                    key=f"{key_prefix}_q",
                    label_visibility="collapsed",
                )
            with col_btn:
                do_search = st.form_submit_button("🔍 검색", use_container_width=True)

        if do_search:
            if q.strip():
                hits = search_airports(q.strip(), google_key)
                st.session_state[f"{key_prefix}_results"] = hits
                if not hits:
                    st.warning("검색 결과가 없습니다. 다른 키워드나 IATA 코드로 검색해보세요.")
            else:
                st.warning("공항명 또는 도시명을 입력해주세요.")

        results = st.session_state.get(f"{key_prefix}_results", [])
        if results:
            labels = [
                f"[{r['iata']}]  {r['name']}  |  {r['city']}, {r['country']}"
                if r.get("iata")
                else f"{r['name']}  |  {r.get('address', '')[:45]}"
                for r in results
            ]
            chosen = st.radio(
                "공항 선택",
                labels,
                key=f"{key_prefix}_radio",
                label_visibility="collapsed",
            )
            idx = labels.index(chosen)
            if st.button("✓ 이 공항으로 선택", key=f"{key_prefix}_confirm",
                         use_container_width=True, type="secondary"):
                st.session_state[f"{key_prefix}_selected"] = results[idx]
                st.session_state[f"{key_prefix}_results"] = []
                st.rerun()

        return None, None, None

    # ── Confirmed state ──────────────────────────────────────────────────────
    iata = selected.get("iata", "")
    name = selected["name"]
    display = f"{name} ({iata})" if iata else name
    icon = "🛬" if key_prefix == "arr" else "🛫"

    col_name, col_change = st.columns([5, 1])
    with col_name:
        st.success(f"{icon} **{display}**")
    with col_change:
        if st.button("변경", key=f"{key_prefix}_change", use_container_width=True):
            st.session_state[f"{key_prefix}_selected"] = None
            st.rerun()

    col_d, col_t = st.columns(2)
    with col_d:
        flight_date = st.date_input("날짜", value=default_date, key=f"{key_prefix}_date")
    with col_t:
        default_t = dtime(14, 0) if key_prefix == "arr" else dtime(10, 0)
        flight_time = st.time_input("시간", value=default_t, key=f"{key_prefix}_time")

    return display, flight_date, flight_time


# ── Accommodation section UI ──────────────────────────────────────────────────
def render_accommodation_section(google_key: str, start_date: date, end_date: date):
    st.markdown("**🏨 숙소 설정**")

    # 항공편에서 목적지 힌트 가져오기 (검색 바이어스용)
    arr_data = st.session_state.get("arr_selected")
    dest_hint = ""
    if arr_data:
        dest_hint = arr_data.get("city", "") or arr_data.get("country", "")

    source_label = "Google Places" if google_key else "OpenStreetMap (무료)"
    ph = f"예: 리츠칼튼" + (f" ({dest_hint} 자동 적용)" if dest_hint else " (도시명 포함 추천)")
    with st.form(key="acc_search_form", border=False):
        col_q, col_btn = st.columns([4, 1])
        with col_q:
            search_q = st.text_input(
                "숙소 검색",
                placeholder=ph,
                key="acc_search_q",
                label_visibility="collapsed",
            )
        with col_btn:
            do_search = st.form_submit_button("검색", use_container_width=True)

    if do_search and search_q.strip():
        # 목적지 힌트가 있고 쿼리에 포함 안 된 경우 자동 추가 → 관련 지역 결과 상위 노출
        effective_q = search_q.strip()
        if dest_hint and dest_hint.lower() not in effective_q.lower():
            effective_q = f"{effective_q} {dest_hint}"
        with st.spinner(f"검색 중... ({source_label})"):
            results = search_accommodations(effective_q, google_key)
            st.session_state["acc_search_results"] = results
            if not results:
                st.warning("검색 결과가 없습니다. 다른 키워드로 검색해 보세요.")

    results = st.session_state.get("acc_search_results", [])
    if results:
        labels = [
            f"{'★' + str(r['rating']) + '  ' if r['rating'] else ''}{r['name']}  |  {r['address'][:45]}"
            for r in results
        ]
        selected_label = st.radio(
            "검색 결과에서 선택",
            labels,
            key="acc_radio",
            label_visibility="collapsed",
        )
        selected_idx = labels.index(selected_label)
        selected = results[selected_idx]

        col1, col2, col3 = st.columns([5, 5, 3])
        with col1:
            ci = st.date_input("체크인", value=start_date, key="acc_ci")
        with col2:
            co = st.date_input("체크아웃", value=end_date, key="acc_co")
        with col3:
            st.write("")
            st.write("")
            if st.button("➕ 추가", key="acc_add_btn", use_container_width=True):
                st.session_state["acc_list"].append({
                    "name": selected["name"],
                    "lat": selected["lat"],
                    "lng": selected["lng"],
                    "address": selected["address"],
                    "place_id": selected.get("place_id", ""),
                    "checkin": ci,
                    "checkout": co,
                })
                st.session_state["acc_search_results"] = []
                st.rerun()

    # Display added accommodations
    acc_list = st.session_state["acc_list"]
    if acc_list:
        for i, acc in enumerate(acc_list):
            col_icon, col_name, col_date, col_del = st.columns([1, 5, 5, 1])
            with col_icon:
                st.write("🏨")
            with col_name:
                st.write(f"**{acc['name']}**")
            with col_date:
                st.caption(f"{acc['checkin']} ~ {acc['checkout']}")
            with col_del:
                if st.button("✕", key=f"acc_del_{i}"):
                    st.session_state["acc_list"].pop(i)
                    st.rerun()
    else:
        st.caption("숙소를 검색하여 추가해주세요.")


# ── Nominatim: POI Search ─────────────────────────────────────────────────────
def search_pois_nominatim(query: str, dest_hint: str = "") -> list[dict]:
    """Search places via Nominatim for POI selection — free, no API key needed."""
    try:
        q = f"{query} {dest_hint}".strip() if dest_hint else query
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "json", "limit": 5,
                    "addressdetails": 1, "extratags": 1},
            headers={"User-Agent": "AI-Travel-Planner/1.0"},
            timeout=10,
        )
        results = []
        for r in resp.json():
            name = r.get("display_name", "").split(",")[0].strip()
            ext = r.get("extratags") or {}
            # 가장 의미있는 카테고리 추출
            cat = (ext.get("shop") or ext.get("amenity") or ext.get("tourism")
                   or ext.get("leisure") or r.get("type", ""))
            addr_parts = r.get("display_name", "").split(",")
            short_addr = ", ".join(addr_parts[:3]).strip()
            results.append({
                "name": name,
                "address": short_addr,
                "category": cat,
                "lat": float(r["lat"]),
                "lng": float(r["lon"]),
            })
        return results
    except Exception:
        return []


def render_poi_search(category_key: str, icon: str,
                      placeholder: str, dest_hint: str) -> list[dict]:
    """검색→선택 UI for one POI category. Returns list of selected places."""
    list_key = f"poi_{category_key}_list"
    results_key = f"poi_{category_key}_results"

    with st.form(key=f"poi_{category_key}_form", border=False):
        col_q, col_btn = st.columns([5, 1])
        with col_q:
            q = st.text_input(
                "검색", placeholder=placeholder,
                key=f"poi_{category_key}_q",
                label_visibility="collapsed",
            )
        with col_btn:
            do_search = st.form_submit_button("🔍", use_container_width=True)

    if do_search:
        if q.strip():
            with st.spinner("검색 중..."):
                hits = search_pois_nominatim(q.strip(), dest_hint)
                st.session_state[results_key] = hits
                if not hits:
                    st.warning("검색 결과 없음 — 아래 '직접 입력'을 사용하세요.")
        else:
            st.warning("장소명을 입력해주세요.")

    results = st.session_state.get(results_key, [])
    if results:
        labels = []
        for r in results:
            cat_tag = f"  [{r['category']}]" if r.get('category') else ""
            labels.append(f"{r['name']}{cat_tag}  |  {r['address']}")
        chosen = st.radio("결과 선택", labels,
                          key=f"poi_{category_key}_radio",
                          label_visibility="collapsed")
        idx = labels.index(chosen)
        if st.button("➕ 추가", key=f"poi_{category_key}_add",
                     use_container_width=True, type="secondary"):
            lst = st.session_state[list_key]
            sel = results[idx]
            if not any(p["name"] == sel["name"] for p in lst):
                lst.append(sel)
                st.session_state[list_key] = lst
            st.session_state[results_key] = []
            st.rerun()

    # 직접 입력 fallback
    with st.expander("✏️ 직접 입력 (검색 결과 없을 때)"):
        man_col, man_btn = st.columns([4, 1])
        with man_col:
            manual = st.text_input("직접 입력",
                                   key=f"poi_{category_key}_manual",
                                   label_visibility="collapsed",
                                   placeholder="장소명 직접 입력")
        with man_btn:
            st.write("")
            if st.button("추가", key=f"poi_{category_key}_manual_add",
                         use_container_width=True):
                if manual.strip():
                    lst = st.session_state[list_key]
                    lst.append({"name": manual.strip(), "address": "",
                                "category": "", "lat": None, "lng": None})
                    st.session_state[list_key] = lst
                    st.rerun()

    # 추가된 POI 목록 표시
    poi_list = st.session_state.get(list_key, [])
    for i, p in enumerate(poi_list):
        col_info, col_del = st.columns([6, 1])
        with col_info:
            cat_tag = f"  `{p['category']}`" if p.get('category') else ""
            st.markdown(f"{icon} **{p['name']}**{cat_tag}")
            if p.get('address'):
                st.caption(p['address'])
        with col_del:
            if st.button("✕", key=f"poi_{category_key}_del_{i}"):
                poi_list.pop(i)
                st.session_state[list_key] = poi_list
                st.rerun()

    return poi_list


# ── Input form ────────────────────────────────────────────────────────────────
def render_inputs(google_key: str) -> dict:
    """Renders all travel input widgets. Returns values dict."""

    _today = date.today()
    _d30 = _today + timedelta(days=30)
    _d34 = _today + timedelta(days=34)
    arr_data = st.session_state.get("arr_selected")
    dep_data = st.session_state.get("dep_selected")

    # ── ✈️ 항공편 (expander — 선택 시 자동으로 열림) ────────────────────────
    flight_expanded = bool(arr_data or dep_data)
    with st.expander("✈️ 항공편 정보 (선택)", expanded=flight_expanded):
        st.caption("🛬 도착 공항")
        arr_airport, arr_date, arr_time = render_airport_select(
            "도착 공항 검색", "arr", default_date=_d30, google_key=google_key
        )
        st.caption("🛫 출발 공항")
        dep_airport, dep_date, dep_time = render_airport_select(
            "출발 공항 검색", "dep", default_date=_d34, google_key=google_key
        )

    # ── 여행지 / 날짜 — 항공편 선택 시 자동 유도 ────────────────────────────
    # Re-read after expander (session_state may have updated inside expander)
    arr_data = st.session_state.get("arr_selected")
    dep_data = st.session_state.get("dep_selected")

    # ── 국가 불일치 경고 ────────────────────────────────────────────────────
    if arr_data and dep_data:
        arr_country = arr_data.get("country", "")
        dep_country = dep_data.get("country", "")
        if arr_country and dep_country and arr_country != dep_country:
            st.warning(
                f"⚠️ 입국 공항 **{arr_data.get('name', '')}** ({arr_country})과 "
                f"출국 공항 **{dep_data.get('name', '')}** ({dep_country})의 "
                f"국가가 다릅니다. 올바르게 입력하셨나요?"
            )

    if arr_data:
        derived_dest = arr_data.get("dest", "")
        start_date = arr_date if arr_date else _d30
        end_date = dep_date if dep_date else (start_date + timedelta(days=4))
        if derived_dest:
            c1, c2, c3 = st.columns(3)
            c1.metric("🌏 여행지", derived_dest)
            c2.metric("📅 출발", start_date.strftime("%m/%d"))
            c3.metric("📅 귀국", end_date.strftime("%m/%d"))
            destination = derived_dest
        else:
            destination = st.text_input("🌏 여행지", placeholder="예: 일본 오사카", key="dest")
            start_date = arr_date if arr_date else _d30
            end_date = dep_date if dep_date else _d34
    else:
        destination = st.text_input("🌏 여행지", placeholder="예: 일본 오사카", key="dest")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("출발일", value=_d30, key="s_date")
        with col2:
            end_date = st.date_input("귀국일", value=_d34, key="e_date")

    arr_airport = arr_airport or ""
    dep_airport = dep_airport or ""

    # ── 숙소 ────────────────────────────────────────────────────────────────
    st.divider()
    render_accommodation_section(google_key, start_date, end_date)

    # ── 방문 희망 장소 ──────────────────────────────────────────────────────
    st.divider()
    st.markdown("**📍 방문 희망 장소**")
    _dest_hint = destination or ""

    st.markdown("🛍️ **쇼핑**")
    poi_shopping_list = render_poi_search(
        "shopping", "🛍️", "예: 만다라케, 돈키호테", _dest_hint)

    st.markdown("🍔 **맛집/식당**")
    poi_food_list = render_poi_search(
        "food", "🍔", "예: 이치란 라멘, 쿠로몬 시장", _dest_hint)

    st.markdown("📸 **관광명소**")
    poi_sight_list = render_poi_search(
        "sightseeing", "📸", "예: 오사카성, 후시미이나리", _dest_hint)

    theme = st.selectbox("여행 테마", ["맛집", "휴양", "관광명소", "쇼핑"], key="theme")

    # ── 하루 활동 시간 ──────────────────────────────────────────────────────
    st.divider()
    st.markdown("**⏰ 하루 활동 시간**")
    col1, col2 = st.columns(2)
    with col1:
        day_start = st.time_input("시작", value=dtime(9, 0), key="day_s")
    with col2:
        day_end = st.time_input("종료", value=dtime(22, 0), key="day_e")

    st.divider()
    demo_mode = st.toggle(
        "🧪 데모 모드 (UI 테스트 · LLM 미호출)",
        value=st.session_state.get("demo_mode", False),
        key="demo_mode_toggle",
        help="AI 호출 없이 샘플 일정으로 지도·탭·표 등 UI를 테스트합니다. 토큰 소비 없음.",
    )
    st.session_state["demo_mode"] = demo_mode

    label = "🗺️ 일정 재생성" if "itinerary" in st.session_state else "🗺️ 일정 생성하기"
    generate_btn = st.button(label, type="primary", use_container_width=True, key="gen_btn")

    return dict(
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        poi_shopping=poi_shopping_list,
        poi_food=poi_food_list,
        poi_sightseeing=poi_sight_list,
        theme=theme,
        arr_airport=arr_airport,
        arr_date=arr_date,
        arr_time=arr_time,
        dep_airport=dep_airport,
        dep_date=dep_date,
        dep_time=dep_time,
        day_start=day_start,
        day_end=day_end,
        generate_btn=generate_btn,
    )


# ── Generation pipeline ───────────────────────────────────────────────────────
def run_generation(inputs: dict, google_key: str, api_key: str):
    destination = inputs["destination"]
    start_date = inputs["start_date"]
    end_date = inputs["end_date"]

    # POI 리스트 (각 항목: {name, address, category, lat, lng})
    _shop_pois  = inputs.get("poi_shopping", [])
    _food_pois  = inputs.get("poi_food", [])
    _sight_pois = inputs.get("poi_sightseeing", [])

    # LLM 프롬프트용 — 카테고리 정보 포함한 문자열 리스트
    def _fmt(p: dict) -> str:
        cat = p.get("category", "").strip()
        return f"{p['name']} ({cat})" if cat else p["name"]

    poi_shopping    = [_fmt(p) for p in _shop_pois]
    poi_food        = [_fmt(p) for p in _food_pois]
    poi_sightseeing = [_fmt(p) for p in _sight_pois]

    acc_list = st.session_state["acc_list"]

    # Seed coords — 숙소 (Places API 결과)
    coords: dict = {}
    for acc in acc_list:
        if acc.get("lat") and acc.get("name"):
            coords[acc["name"]] = {"name": acc["name"], "lat": acc["lat"], "lng": acc["lng"]}

    # Seed coords — POI (Nominatim 검색 결과는 이미 좌표 보유)
    for p in _shop_pois + _food_pois + _sight_pois:
        if p.get("lat") and p.get("name"):
            coords[p["name"]] = {"name": p["name"], "lat": p["lat"], "lng": p["lng"]}

    # 좌표 없는 항목만 geocode (직접 입력한 POI + 공항)
    airports = [a for a in [inputs["arr_airport"].strip(), inputs["dep_airport"].strip()] if a]
    needs_geocode = [
        p["name"] for p in (_shop_pois + _food_pois + _sight_pois)
        if not p.get("lat") and p.get("name")
    ] + airports
    if needs_geocode:
        with st.status("📍 위치 좌표 확인 중...", expanded=False) as s:
            extra = geocode_places(needs_geocode, google_key)
            coords.update(extra)
            found = sum(1 for v in coords.values() if v)
            s.update(label=f"좌표 확인 완료 — {found}/{len(coords)}개 처리됨", state="complete")

    top_restaurants = []
    if google_key and (inputs["theme"] == "맛집" or poi_food):
        with st.status("🍽️ 고평점 맛집 검색 중...", expanded=False) as s:
            top_restaurants = get_top_restaurants(destination, google_key)
            for r in top_restaurants:
                coords[r["name"]] = {"name": r["name"], "lat": r["lat"], "lng": r["lng"]}
            s.update(label=f"맛집 {len(top_restaurants)}곳 발견", state="complete")

    transit_hints = ""
    if google_key:
        with st.status("🚇 이동 시간 계산 중...", expanded=False) as s:
            transit_hints = get_transit_hints(coords, google_key)
            s.update(label="이동 시간 계산 완료", state="complete")

    if st.session_state.get("demo_mode"):
        itinerary = generate_demo_itinerary(destination, start_date, end_date, acc_list)
        # Geocode destination → derive mock nearby coords for demo place names
        with st.status("🗺️ 데모 지도 좌표 설정 중...", expanded=False) as s:
            dest_coord = get_coordinates(destination, google_key)
            if dest_coord:
                coords[destination] = dest_coord
                _offsets = [(-0.008, -0.010), (0.005, 0.008), (0.012, -0.005),
                            (-0.003, 0.015), (0.018, 0.003)]
                for _j, _sfx in enumerate(["중앙 광장", "전통 시장", "박물관", "공원", "쇼핑몰"]):
                    _pname = f"{destination} {_sfx}"
                    coords[_pname] = {
                        "name": _pname,
                        "lat": dest_coord["lat"] + _offsets[_j][0],
                        "lng": dest_coord["lng"] + _offsets[_j][1],
                    }
            s.update(label="데모 지도 좌표 설정 완료", state="complete")
    else:
        itinerary = generate_itinerary(
            destination, start_date, end_date,
            acc_list, poi_shopping, poi_food, poi_sightseeing,
            inputs["theme"], coords, top_restaurants, transit_hints, api_key,
            arr_airport=inputs["arr_airport"], arr_date=inputs["arr_date"],
            arr_time=inputs["arr_time"], dep_airport=inputs["dep_airport"],
            dep_date=inputs["dep_date"], dep_time=inputs["dep_time"],
            day_start=inputs["day_start"], day_end=inputs["day_end"],
        )
        # Post-generation: geocode ROUTE_JSON places + destination
        route_names: set[str] = set()
        for _m in re.finditer(r'<!--\s*ROUTE_JSON:\s*(\[.*?\])\s*-->', itinerary, re.DOTALL):
            try:
                route_names.update(json.loads(_m.group(1)))
            except Exception:
                pass
        route_names.add(destination)
        missing = [p for p in route_names if not coords.get(p)]
        if missing:
            with st.status("🗺️ 지도 좌표 보완 중...", expanded=False) as s:
                for p in missing:
                    c = get_coordinates(p, google_key)
                    if c:
                        coords[p] = c
                s.update(label="지도 좌표 보완 완료", state="complete")

    st.session_state["itinerary"] = itinerary
    st.session_state["coords"] = coords
    st.session_state["start_date"] = start_date
    st.session_state["end_date"] = end_date
    st.session_state["dest_hint"] = destination
    st.session_state["hotel_names"] = {a["name"] for a in acc_list if a.get("name")}
    st.session_state["airport_names"] = set(airports)


# ── Per-day fragment (scopes rerun so map stays visible) ─────────────────────
@st.fragment
def _render_day_fragment(
    day_key: str, day_text: str, coords: dict,
    hotel_names: set, airport_names: set, dest: str, google_key: str,
) -> None:
    sel_key = f"sel_{day_key}"
    if sel_key not in st.session_state:
        st.session_state[sel_key] = None
    dk = day_key.replace(" ", "_")

    # route는 map과 table 번호 매핑 모두에서 사용
    route = extract_route_json(day_text) or [k for k, v in coords.items() if v]
    route_num_map = {name: i + 1 for i, name in enumerate(route)}

    col_map, col_sched = st.columns([1, 1])

    with col_map:
        highlighted = st.session_state.get(sel_key)
        if FOLIUM_AVAILABLE:
            m = build_day_map(route, coords,
                              highlighted_place=highlighted,
                              hotel_names=hotel_names,
                              airport_names=airport_names)
            if m:
                map_return = st_folium(
                    m, height=440,
                    key=f"map_{dk}",
                    use_container_width=True,
                )
                if map_return:
                    tooltip = map_return.get("last_object_clicked_tooltip") or ""
                    last_key = f"last_tooltip_{dk}"
                    if tooltip and tooltip != st.session_state.get(last_key, ""):
                        st.session_state[last_key] = tooltip
                        hit = re.match(r'^\d+\.\s+(.+)$', tooltip)
                        if hit and hit.group(1) != st.session_state.get(sel_key):
                            st.session_state[sel_key] = hit.group(1)
                            st.rerun()
            else:
                st.info("지도에 표시할 좌표 정보가 없습니다.")
        else:
            map_data = [{"lat": v["lat"], "lon": v["lng"]} for v in coords.values() if v]
            if map_data:
                st.map(pd.DataFrame(map_data))

    with col_sched:
        df = parse_schedule_table(day_text)
        if not df.empty:
            # Identify place column before modifying df
            place_col = next(
                (c for c in df.columns if '장소' in c or 'place' in c.lower()),
                df.columns[1] if len(df.columns) > 1 else df.columns[0],
            )
            # # 컬럼 = 지도 마커 번호와 동기화 (ROUTE_JSON 순서 기준)
            def _place_to_num(pname: str) -> str:
                s = str(pname)
                if s in route_num_map:
                    return str(route_num_map[s])
                sl = s.lower()
                for rn, num in route_num_map.items():
                    if sl in rn.lower() or rn.lower() in sl:
                        return str(num)
                return ""
            df = df.copy()
            df.insert(0, '#', df[place_col].apply(_place_to_num))
            st.caption("📌 행을 클릭하면 지도에서 해당 장소가 강조됩니다")
            event = st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                height=320,
                selection_mode="single-row",
                on_select="rerun",
                key=f"df_{dk}",
            )
            sel_rows = (event.selection.rows
                        if (event and hasattr(event, "selection")) else [])
            if sel_rows:
                new_sel = df.iloc[sel_rows[0]][place_col]
                if new_sel != st.session_state.get(sel_key):
                    st.session_state[sel_key] = new_sel
                    st.rerun()  # re-render map with updated highlight
        else:
            st.markdown(clean_route_tags(day_text))

        selected_place = st.session_state.get(sel_key)
        if selected_place:
            st.divider()
            render_place_card(selected_place, dest, google_key)

        with st.expander("✏️ 텍스트 편집"):
            st.text_area(
                "편집",
                value=clean_route_tags(day_text),
                height=200,
                key=f"edit_{dk}",
                label_visibility="collapsed",
            )

    # 새 포맷: "동선" / "오늘의 팁" 인라인 라인 추출
    # 구 포맷 호환: "교통 상세" / "스마트 팁" 섹션도 시도
    route_line = next(
        (l for l in day_text.split('\n') if '동선' in l and '➔' in l), ""
    )
    tips_line = next(
        (l for l in day_text.split('\n') if '오늘의 팁' in l), ""
    )
    transport_section = extract_day_section(day_text, "교통 상세")
    tips_section = extract_day_section(day_text, "스마트 팁")

    col_tr, col_tip = st.columns(2)
    with col_tr:
        if route_line:
            st.markdown(route_line)
        elif transport_section:
            with st.expander("🚇 교통 상세", expanded=False):
                st.markdown(transport_section)
        else:
            for line in day_text.split('\n'):
                if '이동 요약' in line or ('➔' in line and len(line) > 10):
                    st.markdown(line)
                    break
    with col_tip:
        if tips_line:
            st.markdown(tips_line)
        elif tips_section:
            with st.expander("💡 스마트 팁", expanded=False):
                st.markdown(tips_section)


# ── Collaboration: save / load itinerary as JSON ──────────────────────────────
def build_save_data() -> dict:
    """현재 세션에서 공유 가능한 일정 데이터를 JSON-직렬화 가능한 dict로 반환."""
    def _ser(v):
        if isinstance(v, date):
            return v.isoformat()
        if isinstance(v, set):
            return list(v)
        return v

    keys = [
        "itinerary", "coords", "dest_hint",
        "hotel_names", "airport_names",
        "acc_list", "arr_selected", "dep_selected",
        "poi_shopping_list", "poi_food_list", "poi_sight_list",
    ]
    data: dict = {}
    for k in keys:
        v = st.session_state.get(k)
        if v is not None:
            data[k] = _ser(v)
    for k in ("start_date", "end_date"):
        v = st.session_state.get(k)
        if v is not None:
            data[k] = _ser(v)
    return data


def load_save_data(data: dict):
    """저장된 dict를 세션 상태로 복원."""
    for k, v in data.items():
        if k in ("start_date", "end_date"):
            try:
                st.session_state[k] = date.fromisoformat(v)
            except Exception:
                st.session_state[k] = v
        elif k in ("hotel_names", "airport_names") and isinstance(v, list):
            st.session_state[k] = set(v)
        else:
            st.session_state[k] = v


def render_share_panel():
    """공유/저장/불러오기 패널."""
    with st.expander("🤝 일정 공유 & 저장", expanded=False):
        st.caption("JSON 파일로 내보내거나 남편이 공유한 파일을 불러오세요.")
        col_save, col_load = st.columns(2)

        with col_save:
            st.markdown("**💾 내보내기**")
            if "itinerary" in st.session_state:
                dest = st.session_state.get("dest_hint", "여행")
                fname = f"여행일정_{dest}.json"
                save_bytes = json.dumps(
                    build_save_data(), ensure_ascii=False, indent=2
                ).encode("utf-8")
                st.download_button(
                    label="⬇️ JSON 저장",
                    data=save_bytes,
                    file_name=fname,
                    mime="application/json",
                    use_container_width=True,
                )
            else:
                st.info("일정을 먼저 생성하세요.")

        with col_load:
            st.markdown("**📂 불러오기**")
            uploaded = st.file_uploader(
                "JSON 파일 선택",
                type=["json"],
                label_visibility="collapsed",
                key="share_upload",
            )
            if uploaded:
                try:
                    loaded = json.loads(uploaded.read().decode("utf-8"))
                    load_save_data(loaded)
                    st.success("✅ 일정을 불러왔습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"불러오기 실패: {e}")


# ── Output display ────────────────────────────────────────────────────────────
def render_results():
    itinerary = st.session_state["itinerary"]
    coords = st.session_state.get("coords", {})
    dest = st.session_state.get("dest_hint", "")
    hotel_names = st.session_state.get("hotel_names", set())
    airport_names = st.session_state.get("airport_names", set())
    google_key = get_google_key()

    days_dict = parse_days(itinerary)
    tab_labels = list(days_dict.keys()) + ["📋 전체 정보"]
    tabs = st.tabs(tab_labels)

    for i, (day_key, day_text) in enumerate(days_dict.items()):
        with tabs[i]:
            _render_day_fragment(
                day_key, day_text, coords,
                hotel_names, airport_names, dest, google_key,
            )

    # ── 📋 전체 정보 tab ─────────────────────────────────────────────────────
    with tabs[-1]:
        t_preview, t_edit = st.tabs(["📖 미리보기", "✏️ 전체 편집"])
        with t_preview:
            st.markdown(clean_route_tags(itinerary))
        with t_edit:
            edited_full = st.text_area(
                "전체 편집",
                value=itinerary,
                height=600,
                label_visibility="collapsed",
                key="edit_full",
            )
            if edited_full != itinerary:
                st.session_state["itinerary"] = edited_full

    st.divider()
    col_dl, col_share = st.columns([1, 1])
    with col_dl:
        st.download_button(
            label="⬇️ Markdown 다운로드",
            data=clean_route_tags(st.session_state["itinerary"]),
            file_name="final_trip.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_share:
        dest = st.session_state.get("dest_hint", "여행")
        fname = f"여행일정_{dest}.json"
        save_bytes = json.dumps(
            build_save_data(), ensure_ascii=False, indent=2
        ).encode("utf-8")
        st.download_button(
            label="🤝 공유용 JSON 저장",
            data=save_bytes,
            file_name=fname,
            mime="application/json",
            use_container_width=True,
            type="primary",
        )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN LAYOUT — state-based
# ══════════════════════════════════════════════════════════════════════════════

google_key = get_google_key()
api_key = get_groq_key()

has_itinerary = "itinerary" in st.session_state

if not has_itinerary:
    # ── INITIAL STATE: hide sidebar, show centered search form ────────────────
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; padding: 3rem 0 0.5rem;">
        <div style="font-size:3.5rem;">✈️</div>
        <h1 style="font-size:2.6rem; margin:0.3rem 0;">AI 여행 플래너</h1>
        <p style="font-size:1.1rem; color:#888; margin-bottom:0;">
            여행지와 조건을 입력하면 AI가 최적의 맞춤 일정을 만들어 드립니다
        </p>
    </div>
    """, unsafe_allow_html=True)

    _, center_col, _ = st.columns([1, 3, 1])
    with center_col:
        inputs = render_inputs(google_key)
        st.divider()
        render_share_panel()

    if inputs["generate_btn"]:
        if not inputs["destination"].strip():
            st.error("여행지를 입력해주세요.")
            st.stop()
        if inputs["end_date"] < inputs["start_date"]:
            st.error("귀국일은 출발일 이후여야 합니다.")
            st.stop()
        _, gen_col, _ = st.columns([1, 3, 1])
        with gen_col:
            run_generation(inputs, google_key, api_key)
        st.rerun()

else:
    # ── GENERATED STATE: sidebar form + wide main results ─────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ 일정 설정")
        inputs = render_inputs(google_key)
        st.divider()
        render_share_panel()

    st.title("✈️ AI 여행 플래너")

    if inputs["generate_btn"]:
        if not inputs["destination"].strip():
            st.error("여행지를 입력해주세요.")
        elif inputs["end_date"] < inputs["start_date"]:
            st.error("귀국일은 출발일 이후여야 합니다.")
        else:
            run_generation(inputs, google_key, api_key)
            st.rerun()

    render_results()
