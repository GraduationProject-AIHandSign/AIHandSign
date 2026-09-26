# SORI — AI 한국 수어 학습 플랫폼

웹캠으로 한국 수어 단어 3,000개를 실시간으로 인식하고, 학습·퀴즈·오답 복습·3D 아바타 시연·챗봇 코칭을 제공하는 웹 기반 수어 학습 플랫폼입니다. (충북대학교 졸업작품, 3인 팀)

| 항목 | 내용 |
|---|---|
| 인식 모델 | Transformer (TensorFlow/Keras), 파라미터 약 1.2M |
| 성능 (v4) | Test Top-1 **91.3%**, Top-5 **96.4%** (3,000 클래스) |
| 입력 | 30프레임 × 274차원 키포인트 (왼손 42 + 오른손 42 + 얼굴 140 + 포즈 50) |
| 데이터 | AI-Hub 한국 수어 사전 데이터 (batch_01, 키포인트 JSON 약 190만 개 · 23.4GB) |
| 백엔드 | FastAPI (Python 3.11), SQLAlchemy, WebSocket 실시간 추론 |
| 인프라 | GCP Cloud Storage · Cloud SQL (MySQL 8.4) · Cloud Run |

---

## 폴더 구조

```
AIHandSign/
├── data_preprocessing/            # 원본 JSON → 학습용 npy
│   ├── 01_gcs_connection_test.ipynb     GCS 버킷 연결 확인
│   ├── 02_make_label_map.ipynb          단어 ID → 한글 매핑 3,000개 생성
│   ├── 03_data_exploration.ipynb        원본 JSON 구조 탐색, 추출 함수 정의
│   ├── 04_preprocess_2d_5angles.py      2D 키포인트 추출 → X_train (15,000개, 5각도)
│   ├── 05_select_DFU_angles.ipynb       D·F·U 3각도만 선택 → X_train_DFU (9,000개)
│   ├── 06_preprocess_3d.py              3D 키포인트 추출 → X_train_3d (v2 실험용)
│   └── 07_preprocess_signer02_03.py     시연자 2·3 추가 → X_train_DFU_v2 (27,000개)
│
├── avatar/                        # Three.js 아바타용 동작 JSON 생성
│   ├── make_avatar_2d.py                processed/avatars/WORD0001~3000.json
│   └── make_avatar_3d.py                processed/avatars_3d/WORD0001~3000.json
│
├── model_training/                # Colab(T4) 학습 노트북
│   ├── model_v1_5angles.ipynb           5각도 + 3배 증강 → 80.1%
│   ├── model_v2_3d_experiment.ipynb     3D 좌표 실험 → 학습 불가 판정 (0.04%)
│   ├── model_v3_DFU.ipynb               D·F·U 3각도 → 75.6%
│   └── model_v4_final.ipynb             80/10/10 분할 + batch 32 → 91.3% (최종)
│
├── models/                        # 학습된 모델 가중치와 정규화 값
├── processed/                     # 라벨(y), label_map, 전처리 오류 기록
└── backend/                       # FastAPI 서버
    └── app/
        ├── main.py, database.py, models.py
        └── routers/  users · words · learning · daily · chat · badges · predict(WebSocket)
```

## 처리 흐름

```
AI-Hub 원본 JSON ─▶ 02 label_map ─▶ 04 2D 전처리 (15,000) ─▶ 05 D·F·U 선택 (9,000)
                                                                   │
                                   model_v1 ◀─ 15,000              ▼
                                   model_v3 / v4 ◀─────────── 9,000
원본 3D ─▶ 06 3D 전처리 ─▶ model_v2 (실험 후 폐기)
원본 D각도 ─▶ avatar/ ─▶ 3D 아바타 JSON ─▶ 프론트엔드 재생
v4 모델 ─▶ backend/app/routers/predict.py ─▶ WebSocket /ws/predict
```

## 모델 버전별 결과

| 버전 | 데이터 | 분할 | 학습 샘플 (증강 후) | batch | Top-1 | Top-5 |
|---|---|---|---|---|---|---|
| v1 | 5각도 15,000 | 70/15/15 | 31,500 | 64 | 80.1% | 93.3% |
| v2 | 3D 15,000 | 70/15/15 | 31,500 | 64 | 0.04% | – |
| v3 | D·F·U 9,000 | 70/15/15 | 18,900 | 64 | 75.6% | 89.2% |
| **v4** | **D·F·U 9,000** | **80/10/10** | **21,600** | **32** | **91.3%** | **96.4%** |

- 증강: 가우시안 노이즈(σ 0.01), 크기 ×0.9~1.1, 위치 이동 ±0.05. 학습셋에만 적용
- v2 실패 원인: AI-Hub 3D 좌표는 5개 각도가 같은 값으로 복원돼 있어 클래스 내 분산이 0
- `X_train_DFU_v2` (시연자 3명, 27,000개)는 만들어 두었으며 다음 학습·검증에 사용할 예정

## 대용량 학습 데이터

용량 문제로 `X_train*.npy`는 GitHub에 포함하지 않았습니다. 아래 Google Drive에서 받을 수 있습니다.

- [processed 폴더 (X_train 관련)](https://drive.google.com/drive/folders/1R7o9EVTy6dqAAMu3QXdilu7wDVA520al?usp=sharing)
  - `X_train.npy` (15000, 30, 274) · `X_train_DFU.npy` (9000, 30, 274)
  - `X_train_DFU_v2.npy` (27000, 30, 274) · `X_train_3d.npy` (15000, 30, 411)

## 백엔드 실행

```bash
cd backend
python -m venv venv && venv\Scripts\activate      # Windows
pip install fastapi uvicorn sqlalchemy pymysql python-dotenv tensorflow==2.19.0 google-cloud-storage
uvicorn app.main:app --reload
```

`backend/.env`에 DB 접속 정보를 넣어야 합니다 (저장소에는 포함하지 않음).

```
DB_HOST=
DB_PORT=3306
DB_NAME=
DB_USER=
DB_PASSWORD=
```

## 알려진 한계

- 학습 데이터(OpenPose 픽셀 좌표)와 웹캠 추론(MediaPipe 0~1 정규화 좌표)의 좌표계가 달라, 실시간 인식 정확도가 테스트 정확도보다 낮습니다. 현재는 비어 있는 손·얼굴 구간을 학습 평균값(X_mean)으로 채워 완화하고 있으며, MediaPipe 기준 재전처리·재학습이 근본 해결책입니다.
- 한 단어의 D·F·U 샘플은 같은 시연 영상의 다른 각도라, 무작위 분할 시 테스트셋과 학습셋이 비슷해질 수 있습니다. 시연자 2·3 데이터로 별도 검증할 예정입니다.

## 팀

| 이름 | 역할 |
|---|---|
| 조건 | AI 모델, 데이터 전처리, DB, FastAPI 백엔드, 팀 조율 |
| 이준석 | WebSocket · 실시간 통신 |
| 박재원 | 프론트엔드 · Three.js 3D 아바타 |
