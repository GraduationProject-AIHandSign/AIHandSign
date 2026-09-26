import os
import json
import numpy as np
from google.cloud import storage
from collections import Counter
import io

# ── 설정 ──────────────────────────────────────────
PROJECT_ID  = "project-id"
BUCKET_NAME = "sign-language-data-2026"

LOCAL_PATHS = {
    "02": r"C:\Users\chogu\OneDrive\바탕 화면\졸업작품\02",
    "03": r"C:\Users\chogu\OneDrive\바탕 화면\졸업작품\03",
}

FEATURE_SIZE     = 274
TARGET_FRAMES    = 30
MIN_FRAMES       = 10
ANGLES           = ["D", "F", "U"]  # D+F+U만 사용
CHECKPOINT_EVERY = 10
SAVE_PATH        = r"C:\Users\chogu\keypoints_backup"
# ──────────────────────────────────────────────────

# GCS 연결
client = storage.Client(project=PROJECT_ID)
bucket = client.bucket(BUCKET_NAME)

# label_map 로드
blob = bucket.blob("processed/label_map.json")
label_map = json.loads(blob.download_as_text())
print(f"✅ label_map 로드 완료! {len(label_map)}개 단어")

errors = []

def extract_keypoints(people, filepath=""):
    def remove_confidence(kp):
        return [kp[i] for i in range(len(kp)) if i % 3 != 2]

    left_hand  = remove_confidence(people.get("hand_left_keypoints_2d",  []))
    right_hand = remove_confidence(people.get("hand_right_keypoints_2d", []))
    face       = remove_confidence(people.get("face_keypoints_2d",       []))
    pose       = remove_confidence(people.get("pose_keypoints_2d",       []))

    result = left_hand + right_hand + face + pose

    if len(result) != FEATURE_SIZE:
        errors.append({"type": "키포인트 개수 오류", "file": filepath, "error": f"{len(result)}개 (274개여야 함)"})
        return None

    arr = np.array(result)
    if np.any(np.isnan(arr)):
        errors.append({"type": "NaN 값 포함", "file": filepath, "error": "숫자가 아닌 값 포함"})
        return None
    if np.any(np.isinf(arr)):
        errors.append({"type": "Inf 값 포함", "file": filepath, "error": "무한대 값 포함"})
        return None
    if np.all(arr == 0):
        errors.append({"type": "빈 프레임", "file": filepath, "error": "키포인트 전부 0"})
        return None

    return result


def normalize_frames(frames):
    frames = np.array(frames)
    n = len(frames)

    if n == 0:
        return np.zeros((TARGET_FRAMES, FEATURE_SIZE))
    elif n >= TARGET_FRAMES:
        indices = np.linspace(0, n-1, TARGET_FRAMES, dtype=int)
        return frames[indices]
    else:
        padded = np.zeros((TARGET_FRAMES, FEATURE_SIZE))
        padded[:n] = frames
        return padded


def save_checkpoint(X_all, y_all, batch, word_id):
    """로컬에 중간 저장"""
    print(f"  저장 시도 중... 경로: {SAVE_PATH}")
    os.makedirs(SAVE_PATH, exist_ok=True)
    X_np = np.array(X_all, dtype=np.float32)
    y_np = np.array(y_all, dtype=np.int32)
    np.save(os.path.join(SAVE_PATH, f"X_partial_{batch}.npy"), X_np)
    np.save(os.path.join(SAVE_PATH, f"y_partial_{batch}.npy"), y_np)
    with open(os.path.join(SAVE_PATH, f"progress_{batch}.txt"), "w") as f:
        f.write(str(word_id))
    print(f"  💾 batch_{batch} 로컬 저장 완료! ({word_id}단어까지)")


def load_checkpoint(batch):
    """이전 진행상황 불러오기"""
    progress_file = os.path.join(SAVE_PATH, f"progress_{batch}.txt")
    X_file = os.path.join(SAVE_PATH, f"X_partial_{batch}.npy")
    y_file = os.path.join(SAVE_PATH, f"y_partial_{batch}.npy")

    if os.path.exists(progress_file) and os.path.exists(X_file):
        with open(progress_file, "r") as f:
            last_word_id = int(f.read().strip())
        X_all = list(np.load(X_file))
        y_all = list(np.load(y_file))
        print(f"✅ batch_{batch} 이전 진행상황 발견! WORD{last_word_id:04d}까지 완료")
        print(f"   누적 샘플: {len(X_all)}개 → WORD{last_word_id+1:04d}부터 시작!")
        return X_all, y_all, last_word_id + 1
    else:
        print(f"🆕 batch_{batch} 처음부터 시작!")
        return [], [], 1


# ── batch_02, 03 전처리 ───────────────────────────
all_X = []
all_y = []

for batch, local_path in LOCAL_PATHS.items():
    print(f"\n{'='*50}")
    print(f"batch_{batch} 전처리 시작")
    print(f"{'='*50}")

    X_all, y_all, start_word_id = load_checkpoint(batch)

    for word_id in range(start_word_id, 3001):
        for angle in ANGLES:
            folder = os.path.join(local_path, f"NIA_SL_WORD{word_id:04d}_REAL{batch}_{angle}")

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

        if word_id % CHECKPOINT_EVERY == 0:
            print(f"[{word_id}/3000] 처리 중... 누적 샘플: {len(X_all)}개 | 오류: {len(errors)}개")
            save_checkpoint(X_all, y_all, batch, word_id)

    # batch 완료
    X_np = np.array(X_all, dtype=np.float32)
    y_np = np.array(y_all, dtype=np.int32)
    print(f"\n✅ batch_{batch} 완료! 샘플 수: {X_np.shape}")

    if errors:
        types = Counter([e["type"] for e in errors])
        print(f"\n오류 유형별 집계:")
        for t, count in types.items():
            print(f"  {t}: {count}개")

    all_X.append(X_np)
    all_y.append(y_np)

    # 임시 파일 삭제
    for f in [f"X_partial_{batch}.npy", f"y_partial_{batch}.npy", f"progress_{batch}.txt"]:
        path = os.path.join(SAVE_PATH, f)
        if os.path.exists(path):
            os.remove(path)
    print(f"🗑️ batch_{batch} 임시 파일 삭제 완료!")

# ── GCS에서 기존 batch_01 로드 ───────────────────
print(f"\n{'='*50}")
print("GCS에서 기존 X_train_DFU.npy(batch_01) 로드 중...")
print(f"{'='*50}")

def load_npy(blob_name):
    buf = io.BytesIO(bucket.blob(blob_name).download_as_bytes())
    return np.load(buf)

X_01 = load_npy("processed/X_train_DFU.npy")  # (9000, 30, 274)
y_01 = load_npy("processed/y_train_DFU.npy")  # (9000,)
print(f"✅ batch_01 로드 완료! shape: {X_01.shape}")

# ── 01 + 02 + 03 합치기 ──────────────────────────
X_final = np.concatenate([X_01] + all_X, axis=0)
y_final = np.concatenate([y_01] + all_y, axis=0)

print(f"\n✅ 합치기 완료!")
print(f"   batch_01: {X_01.shape}")
for i, (batch, X) in enumerate(zip(LOCAL_PATHS.keys(), all_X)):
    print(f"   batch_{batch}: {X.shape}")
print(f"   최종: {X_final.shape}")

cnt = Counter(y_final.tolist())
print(f"   단어당 샘플 수 (최소/최대): {min(cnt.values())} / {max(cnt.values())}")

# ── GCS 업로드 ────────────────────────────────────
answer = input("\nGCS에 업로드할까요? (y/n): ")
if answer.lower() == "y":
    buf_x = io.BytesIO(); np.save(buf_x, X_final); buf_x.seek(0)
    buf_y = io.BytesIO(); np.save(buf_y, y_final); buf_y.seek(0)

    bucket.blob("processed/X_train_DFU_v2.npy").upload_from_file(buf_x, content_type="application/octet-stream")
    bucket.blob("processed/y_train_DFU_v2.npy").upload_from_file(buf_y, content_type="application/octet-stream")

    error_json = json.dumps(errors, ensure_ascii=False, indent=2)
    bucket.blob("processed/errors_02_03.json").upload_from_string(error_json, content_type="application/json")

    print("\n✅ GCS 업로드 완료!")
    print("   processed/X_train_DFU_v2.npy")
    print("   processed/y_train_DFU_v2.npy")
    print("   processed/errors_02_03.json")
else:
    print("❌ 업로드 취소됨")
