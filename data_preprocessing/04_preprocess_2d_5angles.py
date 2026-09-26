import os
import json
import numpy as np
from google.cloud import storage
from collections import Counter
import io

# 설정 
PROJECT_ID  = "project-id"
BUCKET_NAME = "sign-language-data-2026"
LOCAL_PATH  = r"C:\Users\chogu\OneDrive\바탕 화면\졸업작품\01"
SAVE_PATH   = r"C:\Users\chogu\keypoints_backup"

FEATURE_SIZE     = 274 # 키포인트 개수
TARGET_FRAMES    = 30 # 정규화할 프레임 수
MIN_FRAMES       = 10 # 최소 유효 프레임
ANGLES           = ["D", "F", "L", "R", "U"] # 5각도 전체
CHECKPOINT_EVERY = 10 # 10단어마다 저장

# GCS 연결
client = storage.Client(project=PROJECT_ID)
bucket = client.bucket(BUCKET_NAME)

# label_map 로드
blob = bucket.blob("processed/label_map.json")
label_map = json.loads(blob.download_as_text())
print(f"label_map 로드 완료! {len(label_map)}개 단어")

errors = []

def extract_keypoints(people, filepath=""): # JSON에서 신뢰도를 제거하고 x, y만 추출
    def remove_confidence(kp):
        return [kp[i] for i in range(len(kp)) if i % 3 != 2]

    left_hand  = remove_confidence(people.get("hand_left_keypoints_2d",  []))
    right_hand = remove_confidence(people.get("hand_right_keypoints_2d", []))
    face       = remove_confidence(people.get("face_keypoints_2d",       []))
    pose       = remove_confidence(people.get("pose_keypoints_2d",       []))

    result = left_hand + right_hand + face + pose

    if len(result) != FEATURE_SIZE: # 키포인트 개수가 274가 아닌 경우
        errors.append({"type": "키포인트 개수 오류", "file": filepath, "error": f"{len(result)}개 (274개여야 함)"})
        return None

    arr = np.array(result)
    if np.any(np.isnan(arr)): # NaN 값이 있는 경우
        errors.append({"type": "NaN 값 포함", "file": filepath, "error": "숫자가 아닌 값 포함"})
        return None
    if np.any(np.isinf(arr)): # Inf 값이 있는 경우
        errors.append({"type": "Inf 값 포함", "file": filepath, "error": "무한대 값 포함"})
        return None
    if np.all(arr == 0): # 전부 0인 빈 프레임인 경우
        errors.append({"type": "빈 프레임", "file": filepath, "error": "키포인트 전부 0"})
        return None

    return result


def normalize_frames(frames): # 프레임 정규화
    frames = np.array(frames)
    n = len(frames)

    if n == 0:
        return np.zeros((TARGET_FRAMES, FEATURE_SIZE))
    elif n >= TARGET_FRAMES: # 30프레임 초과 -> np.linspace로 균등 샘플링
        indices = np.linspace(0, n-1, TARGET_FRAMES, dtype=int)
        return frames[indices]
    else: # 30프레임 미만 -> 뒤를 0으로 제로패딩
        padded = np.zeros((TARGET_FRAMES, FEATURE_SIZE))
        padded[:n] = frames
        return padded


def save_checkpoint(X_all, y_all, word_id):
    """로컬에 중간 저장"""
    print(f"  저장 시도 중... 경로: {SAVE_PATH}")
    os.makedirs(SAVE_PATH, exist_ok=True)  # 폴더 없으면 자동 생성
    X_np = np.array(X_all, dtype=np.float32)
    y_np = np.array(y_all, dtype=np.int32)
    np.save(os.path.join(SAVE_PATH, "X_partial.npy"), X_np)
    np.save(os.path.join(SAVE_PATH, "y_partial.npy"), y_np)
    with open(os.path.join(SAVE_PATH, "progress.txt"), "w") as f:
        f.write(str(word_id))
    print(f"  로컬 저장 완료 ({word_id}단어까지)")


def load_checkpoint():
    """이전 진행상황 불러오기"""
    progress_file = os.path.join(SAVE_PATH, "progress.txt")
    X_file = os.path.join(SAVE_PATH, "X_partial.npy")
    y_file = os.path.join(SAVE_PATH, "y_partial.npy")

    if os.path.exists(progress_file) and os.path.exists(X_file):
        with open(progress_file, "r") as f:
            last_word_id = int(f.read().strip())
        X_all = list(np.load(X_file))
        y_all = list(np.load(y_file))
        print(f"이전 진행상황 발견! WORD{last_word_id:04d}까지 완료")
        print(f"   누적 샘플: {len(X_all)}개 → WORD{last_word_id+1:04d}부터 시작!")
        return X_all, y_all, last_word_id + 1
    else:
        print("처음부터 시작")
        return [], [], 1


# ── 이전 진행상황 확인 ─────────────────────────────
X_all, y_all, start_word_id = load_checkpoint()

# ── 메인 처리 루프 ─────────────────────────────────
for word_id in range(start_word_id, 3001):

    for angle in ANGLES:
        folder = os.path.join(LOCAL_PATH, f"NIA_SL_WORD{word_id:04d}_REAL01_{angle}")

        if not os.path.exists(folder):
            errors.append({"type": "폴더 없음", "file": folder, "error": f"WORD{word_id:04d}_{angle} 폴더 없음"})
            continue

        files  = sorted([f for f in os.listdir(folder) if f.endswith(".json")])
        frames = []

        for filename in files:
            filepath = os.path.join(folder, filename)
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                kp = extract_keypoints(data["people"], filepath)
                if kp is not None:
                    frames.append(kp)
            except Exception as e:
                errors.append({"type": "파싱 오류", "file": filepath, "error": str(e)})

        if len(frames) < MIN_FRAMES:
            errors.append({"type": "프레임 부족", "file": folder, "error": f"{len(frames)}프레임 (최소 {MIN_FRAMES}개)"})
            continue

        normalized = normalize_frames(frames)
        X_all.append(normalized)
        y_all.append(word_id - 1)

    # 10단어마다 로컬 저장
    if word_id % CHECKPOINT_EVERY == 0:
        print(f"[{word_id}/3000] 처리 중... 누적 샘플: {len(X_all)}개 | 오류: {len(errors)}개")
        save_checkpoint(X_all, y_all, word_id)

# ── 최종 완료 ──────────────────────────────────────
X_np = np.array(X_all, dtype=np.float32)
y_np = np.array(y_all, dtype=np.int32)

print(f"\n전처리 완료")
print(f"X_train shape: {X_np.shape}")
print(f"y_train shape: {y_np.shape}")
print(f"오류 총 {len(errors)}개")

if errors:
    types = Counter([e["type"] for e in errors])
    print("\n오류 유형별 집계:")
    for t, count in types.items():
        print(f"  {t}: {count}개")

# ── 오류 확인 후 GCS 업로드 ───────────────────────
answer = input("\nGCS에 업로드할까요? (y/n): ")
if answer.lower() == "y":
    buf_x = io.BytesIO(); np.save(buf_x, X_np); buf_x.seek(0)
    buf_y = io.BytesIO(); np.save(buf_y, y_np); buf_y.seek(0)

    bucket.blob("processed/X_train.npy").upload_from_file(buf_x, content_type="application/octet-stream")
    bucket.blob("processed/y_train.npy").upload_from_file(buf_y, content_type="application/octet-stream")

    error_json = json.dumps(errors, ensure_ascii=False, indent=2)
    bucket.blob("processed/errors.json").upload_from_string(error_json, content_type="application/json")

    print("GCS 업로드 완료")
    print(f"  processed/X_train.npy")
    print(f"  processed/y_train.npy")
    print(f"  processed/errors.json")

    # 로컬 임시 파일 삭제
    for f in ["X_partial.npy", "y_partial.npy", "progress.txt"]:
        path = os.path.join(SAVE_PATH, f)
        if os.path.exists(path):
            os.remove(path)
    print("로컬 임시 파일 삭제 완료!")

else:
    print("업로드 취소됨")
