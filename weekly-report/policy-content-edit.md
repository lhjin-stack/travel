# KMTC 정책 페이지 콘텐츠 (한국어 기준)
> 이 파일을 수정하면 제가 HTML(한/영/중)에 반영합니다.
> - 삭제할 항목: ~~취소선~~ 또는 통째로 지워주세요
> - 수정할 항목: 직접 고치세요
> - 추가할 항목: 해당 위치에 넣어주세요
> - 탭 자체를 빼고 싶으면 탭 제목 옆에 [삭제] 표시

---

## 페이지 탭 구조
1. 📊 현황 (대시보드)
2. 🚢 선박·항로
3. 📋 NSA EOV 가이드
4. 💰 비용(WRS,EFS)
5. 📢 공지·회의 (삭제)
6. 🔄 이력 (변경로그 - JSON 자동 렌더링)

---

# 📊 탭1: 현황

## 공통 유의사항
- 🔴 **[NEW 3/19] 중동향 특수화물(DG/OOG/RF) 접수 전면 중단** — SPECIAL CENTER 공지. 중동 발/착 DG·OOG·RF 전체 임시 접수 중단. 추후 공지 시까지 신규 부킹 불가.
- 🔴 **[NEW 3/19] WRS 징수 중단** — KMU 모선 이후 선적건부터는 DEVIATION $800/$1600 + 로컬 운송료 별도로 대체
- 🔴 **LOI 징구 필수** — 전쟁위험 관련 추가비용 부담 LOI를 화주로부터 반드시 사전 징구. 법무법인 검토 완료 양식 사용. **중국발: WRS 항목 2번 삭제된 개정판 사용 (3/10 개정)**
- 🔴 **KLF 3일 미픽업 → SHJ ICD 강제이송** — 도착 후 3일 이내 미픽업 시 SHJ ICD로 강제 이송. 스토리지 Day 1부터 청구. 화주 즉시 통보 필수.
- 🟡 **EOV 화물 비용** — 비용·이송방법은 현지 상황에 따라 변동 가능. 화주에게 반드시 사전 안내 필요. (NSA EOV 가이드 탭 확인)
- 🔵 **보세운송 세관 해결 완료** — JEA, QIW, ADP, SHJ → KLF 통관 없이 IN-TRANSIT 보세운송 가능 (샤르자 세관 협의 완료).


## 목적지별 빠른 조회
현재 포트: JEA / DMM·KSP / KWI·UQR·HMA / SHJ·AJM·RAK / AQJ·JED·SKN / NSA

### JEA (Jebel Ali)
- 상태: 직항 불가 — KLF 종착
- ROUTING: POL → KLF (종착)
- B/L: POD: KLF / DLY: KLF (B/L상 KLF만 표기)
- DEVIATION $800/$1600 + 로컬 운송료 별도
- 부킹 가이드: 부킹 레그 KLF에서 종료 | B/L에는 KLF만 표기 | KLF→JEA 운송은 도착지에서 별도 보세운송 처리 (CNEE 비용 부담)
- ⚠️ LOI 징구 필수 | KLF 3일 내 미픽업 시 SHJ ICD 강제이송
- 처리 상세:
  - 1안: DPW LOGISTIC 경유 JEA 운송 (한국발: THC+LIFTING+DVC $800/1,600+운송+JEA LOCAL+KLF Storage / 한국외: THC+LIFTING+WRP $2,000/3,500+JEA LOCAL+KLF Storage)
  - 2안: KLF에서 화물 직접 반출 (THC+LIFTING+DVC $800/1,600+JEA DROP OFF AED 900/1,200+JEA LOCAL)

### DMM / KSP (Dammam / King Salman Port)
- 상태: 직항 불가 — JED 경유 또는 KLF 경유
- 두 가지 루트:
  1. **JED 경유 (최근 요청 증가, 권장)**: NSA → JED (IRX2 이용, 별도 피더비 없음) → JED에서 화주 비용 트럭킹 → DMM/KSP. 수입자 WRS $2,000/$3,500 징수, 현지 로컬비용은 화주 진행.
  2. **KLF 경유**: NSA → KLF → JEA → DMM/KSP (더블 T/S). 피더비 별도 발생.

### KWI / UQR / HMA (Upper Gulf 기타)
- 상태: 되도록 Ship-back 권유
- 피더 선복·현지 운송·통관 가능성·비용에 따라 별도 검토

### SHJ / AJM / RAK / QIW
- 상태: KLF 경유 트럭
- (기존 내용 유지)

### AQJ / JED / SKN (홍해)
- 상태: 더블 T/S — 적체 경보
- (기존 내용 유지)

### NSA (Nhava Sheva)
- 상태: 대체 양하항 (EOV)
- (기존 내용 유지)

---

# 🚢 탭2: 선박·항로

## 선박 운영 현황 & 항로 결정 사항 (3/16 기준)

### 중동항로 공동사 협의 결과 & 당사 모선 운영 방안
| 항로 | 공동운항사 | 기존 Rotation | 변경 Rotation | 협의 결과 | 당사 모선 |
|------|-----------|-------------|-------------|----------|---------|
| AIM | KMTC,ESL,GFS,HMM | PNC-TAO-XMN-DCB-PKW-JEA-DMM-KSP | PNC-TAO-XMN-DCB-PKW-KLF | JEA·DMM Drop(C75), HMM부터 Suspension→Ad-Hoc | KDM호 KLF ETA 3/23 |
| AIM2 | KMTC,ESL,ONE | SHA-NBO-SHK-SIN-JEA-KLF-SOH-PKW | SHA-NBO-SHK-SIN-NSA-KLF-PKW | C16 수행 후 Suspension, ONE ME 불기항→NSA 양하 | KMU호 KLF ETA 4/5 |
| VGI | KMTC,RCL,GFS,ESL | CMP-LCH-PKW-NSA-JEA-DMM-MUN-PKW | CMP-LCH-PKW-NSA-MUN-PKW | 5개 항차 ME Skip (ROB→NSA 양하) | KMB호 VGI 계속 수행 |

### ② AIM 항로 선박별 현황 (Cycle 75→76)
(상세 선박 테이블 — 현재 내용 유지)

### ③ AIM2 항로 선박별 현황 (Cycle 16→17)
(상세 선박 테이블 — 현재 내용 유지)

### ④ VGI 항로 선박별 현황 (Cycle 34→35)
(상세 선박 테이블 — 현재 내용 유지)

### ⑤ 항로/Cycle 기준 선박 상황 & 화물 처리 방안 요약
- 합계 BSA: 4,545 TEU / NSA 대체양하: 2,050 TEU
- (상세 테이블 — 현재 내용 유지)

# 💰 탭3: 비용 변동 공지

## **EFS (긴급 연료 할증)**: 3/18 확정, **3/28 출항분부터 적용** (베트남 4/1). POL 징수.
  - EFS 요율: JAPAN 60/120/90/180 | CHN/HKG/TW 40/80/60/120 | SEA 40/80/60/120 | ISC 160/320/240/480 | ME 160/320/240/480 | RED SEA 200/400/300/600 | AFRICA 200/400/300/600 | MEXICO 200/400/300/600
  - 적용 대상: 중국·한국·일본·미국 제외 전 선적지

## [NEW 3/19] WRS 비용 청구 구조 (Final Leg 기준)

### 개전일 이전 : 비용 면제

### 기선적 건 (KMU 이전 모선)
- WRS 징수되지 않은 건 → **Deviation $800/1,600 + 로컬 운송료(트럭킹)** 별도 청구
- 중국/동남아발도 한국발과 동일하게 적용 (WRS 청구 X, Deviation+트럭킹)

### 신규 선적 건 (KMU 이후 모선)
- 운임에 이미 반영되었으므로 → **트럭킹 비용만 청구**


## NSA EOV 목적지별 비용 정리표

| 경로 | 수출자(Shipper) 부담 | 수입자(Consignee) 부담 | 비고 |
|------|-------------------|---------------------|------|
| NSA → KLF (JEA, AUH) | $2,000 / $4,000 | $2,000 / $3,500 + 도착지 로컬차지 | 가장 일반적 |
| NSA → JED / AQJ / SKN | 없음 | $2,000 / $3,500 + 도착지 로컬차지 | IRX2 이용, 별도 피더비 없음 |
| NSA → DMM / KSP | 없음 | $2,000 / $3,500 (JED까지) + JED→DMM/KSP 트럭킹 (수입자 부담) | JED 경유 트럭킹 루트 |
| SOH | 미정 | 미정 | 비용 이슈 多, DVC $800/1,600만 청구 |
| KWI / UQR | - | - | 되도록 Ship-back 권유 |

## WRS 면제 / 할인 기준
| 구분 | 면제 여부 |
|------|---------|
| 2/28 이전 입항(접안 완료) 선적 화물 | ✅ 면제 가능 |
| 3/1 이후 접안 선박 선적 화물 | ❌ Full Tariff |
| HELLA 02606W 3/5 DMM 도착분 | ❌ 불가 |
| 화주 "전쟁 영향 없다" 주장 | ⚠️ 개별 판단 |
| 공동운항사 면제 주장 | ⚠️ 당사 독자 판단 |


# 📋 탭4: NSA EOV 가이드

## NSA EOV 임시 운영 가이드라인 (GCS JHKIM | 3/17)
- 금주 금요일(3/20)까지 시트 건 전량 확인

### 대상 선복
- AIM2: JORS 0252W
- VGI: JAYB 02607W / JZSY 02609W / JAPL 02610W

### 1. 기본 처리 원칙
- 화물은 NSA(Nhava Sheva)에서 EOV 양하
- NSA 양하 이후 처리(픽업·통관·운송 등)는 별도 후속 조치로 취급, 추가 비용 별도

### 2. 화주 안내 옵션 (4가지)

**Option 1 — NSA 직접 픽업 / Ship-back / COD**
- NSA 현지 통관 후 픽업, 선적항 반송, 또는 다른 목적지 COD
- Ship-back/COD 시 송하인·수하인 양측 서면 동의 및 요청서 서류 징구 필수
- COD의 경우 **화물포기각서**별도 징구 필요
- 발생하는 모든 비용 화주측에서 지불 필요.
- 서류 징수 완료 후 시트 내 리마크 입력.

**Option 2 — NSA → KLF 이송 후 최종 목적지 처리**
- NSA에서 KLF로 이송 후 최종 목적지별 후속 처리. 현재 가장 실현 가능한 대안.
- 피더리지 비용 지불 여부(Y) 최대한 빠르게 확인 필수(미확인 시 피더 연결 지장)
- Y 표시 건은 B/L Additional Freight 탭 → OTH 코드 → 피더리지 USD 2,000/TEU 즉시 입력, 기본 PPD 청구 진행

**Option 3 — Upper Gulf 별도 연결 (DMM / KWI / UQR)**
- 피더 선복·현지 운송·통관 가능성·비용에 따라 별도 검토
- **DMM/KSP는 JED 경유 루트 권장** 
- **KWI/UQR은 되도록 Ship-back 권유**

**Option 4 — Red Sea 별도 연결 (JED / SKN / AQJ)**
- **[NEW 3/19] IRX2 이용 시 별도 피더비 없음.** 수입자 WRS $2,000/$3,500 + 도착지 로컬차지.

### [NEW 3/19] NSA EOV 목적지별 비용 총정리

| 경로 | 수출자(Shipper) 부담 | 수입자(Consignee) 부담 | 비고 |
|------|-------------------|---------------------|------|
| **NSA → KLF (JEA, AUH)** | 피더리지 $2,000 / $4,000 | DEVIATION $800/$1600 + 도착지 로컬차지 + 로컬 운송비 | 가장 일반적 |
| **NSA → JED / AQJ / SKN** | 없음 | $2,000 / $3,500 + 도착지 로컬차지 | IRX2 이용, 별도 피더비 없음 |
| **NSA → DMM / KSP** | 없음 | $2,000 / $3,500 (JED까지) + JED→목적지 트럭킹 | JED 경유, 트럭킹은 수입자 비용 |
| **SOH** | 미정 | DVC $800/$1,600만 청구 (WRS 대신) | 도착지 비용 이슈 多 |
| **KWI / UQR** | - | - | 되도록 Ship-back 권유 |


### 3. 화주 안내 필수 사항
- 당사는 EOV선언 하였으므로, EOV이후 처리에 대한 의무는 없음.
- NSA 양하 이후 발생 비용은 원칙적으로 화주 부담
- 추가 비용은 반드시 본사 재확인 후 화주에게 안내
- Ship-back/COD 시 송하인+수하인 서면 동의 필수
- **COD 시 화물포기각서 별도 징구 필요** (Ship-back과 구분)
- Surrender B/L 또는 Sea Waybill 권장
- OBL 사용 시 대체 양하지에서 화물 인도 지연 가능성

### ⚠ 중동향 특수화물 접수 중단 (3/19 SPECIAL CENTER)
- **DG(위험물) / OOG(규격외) / RF(냉동)** — 중동 발/착 전체 임시 접수 중단
- KLF 장치장 이슈 + 전쟁 상황으로 추후 공지 시까지 신규 부킹 불가
- 기 ROB DG 화물은 운항선사 차항지 양하 후 통보 예상
- 화주에게 COD / Ship-back / EOV 옵션 안내 필요

## JEA 현지 운영 참고사항 (Shiny Seraphine, JEA Office)
- 🚛 트럭 운송: DPW Logistics 계약 KLF→JEA / KLF 통관 희망 시 2일 전 사전 통보 / 미통보 시 JEA로 자동 이송
- ⚠ KLF 유의: 양하 후 5-6일 지연(야적장 부족) / 3일 경과 시 ICD 야드 이동(B/L별 분리 불가) / ICD 이동 후 포탈 추적 불가
- 🧊 특수 컨테이너: RF=JEA에서만 수령 / DG=접수 불가 / OOG=case by case / Flexi bag=가능
- 📄 D/O: JEA 반입 완료 후 정상 수령 / POL WRP 결제 시 ICC 반영 필요

---
