import os
import json
import numpy as np
from google.cloud import storage
from collections import Counter

# 설정 
PROJECT_ID  = "project-id"
BUCKET_NAME = "sign-language-data-2026"
LOCAL_PATH  = r"C:\Users\chogu\OneDrive\바탕 화면\졸업작품\01"
SAVE_PATH   = r"C:\Users\chogu\keypoints_backup"

TARGET_FRAMES = 30
MIN_FRAMES    = 10
ANGLES        = ["D"]  # 아바타는 정면(D)만 사용

# GCS 연결
client = storage.Client(project=PROJECT_ID)
bucket = client.bucket(BUCKET_NAME)

# label_map 로드
blob = bucket.blob("processed/label_map.json")
label_map = json.loads(blob.download_as_text())
print(f"label_map 로드 완료! {len(label_map)}개 단어")

errors = []

def extract_keypoints_avatar(people, filepath=""):
    """관절별로 따로 추출 (아바타용)"""
    def remove_confidence(kp):
        # [x, y, conf, x, y, conf, ...] → [[x,y], [x,y], ...]
        result = []
        for i in range(0, len(kp), 3):
            result.append([kp[i], kp[i+1]])
        return result

    left_hand  = remove_confidence(people.get("hand_left_keypoints_2d",  []))
    right_hand = remove_confidence(people.get("hand_right_keypoints_2d", []))
    face       = remove_confidence(people.get("face_keypoints_2d",       []))
    pose       = remove_confidence(people.get("pose_keypoints_2d",       []))

    # 오류 탐지
    if len(left_hand) != 21:
        errors.append({"type": "왼손 키포인트 오류", "file": filepath, "error": f"{len(left_hand)}개"})
        return None
    if len(right_hand) != 21:
        errors.append({"type": "오른손 키포인트 오류", "file": filepath, "error": f"{len(right_hand)}개"})
        return None
    if len(face) != 70:
        errors.append({"type": "얼굴 키포인트 오류", "file": filepath, "error": f"{len(face)}개"})
        return None
    if len(pose) != 25:
        errors.append({"type": "상체 키포인트 오류", "file": filepath, "error": f"{len(pose)}개"})
        return None

    return {
        "left_hand":  left_hand,
        "right_hand": right_hand,
        "face":       face,
        "pose":       pose
    }


def normalize_frames_avatar(frames, target=TARGET_FRAMES):
    """프레임 수를 30으로 정규화"""
    n = len(frames)
    if n == 0:
        return []
    elif n >= target:
        indices = np.linspace(0, n-1, target, dtype=int)
        return [frames[i] for i in indices]
    else:
        # 프레임 부족 시 마지막 프레임으로 패딩
        padded = frames.copy()
        while len(padded) < target: # 마지막 프레임 반복
            padded.append(frames[-1]) # 마지막 자세 유지
        return padded


def save_checkpoint(last_word_id):
    """진행상황 저장"""
    os.makedirs(SAVE_PATH, exist_ok=True)
    with open(os.path.join(SAVE_PATH, "avatar_progress.txt"), "w") as f:
        f.write(str(last_word_id))
    print(f"  진행상황 저장 완료! ({last_word_id}단어까지)")


def load_checkpoint():
    """이전 진행상황 불러오기"""
    progress_file = os.path.join(SAVE_PATH, "avatar_progress.txt")
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            last_word_id = int(f.read().strip())
        print(f"이전 진행상황 발견! WORD{last_word_id:04d}까지 완료")
        print(f"   WORD{last_word_id+1:04d}부터 시작!")
        return last_word_id + 1
    else:
        print("처음부터 시작!")
        return 1


# ── 이전 진행상황 확인 ─────────────────────────────
start_word_id = load_checkpoint()

# ── 메인 처리 루프 ─────────────────────────────────
for word_id in range(start_word_id, 3001):
    word_name = label_map.get(str(word_id), f"WORD{word_id:04d}")

    folder = os.path.join(LOCAL_PATH, f"NIA_SL_WORD{word_id:04d}_REAL01_D")

    if not os.path.exists(folder):
        errors.append({"type": "폴더 없음", "file": folder, "error": f"WORD{word_id:04d}_D 폴더 없음"})
        continue

    files  = sorted([f for f in os.listdir(folder) if f.endswith(".json")])
    frames = []

    for filename in files:
        filepath = os.path.join(folder, filename)
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            kp = extract_keypoints_avatar(data["people"], filepath)
            if kp is not None:
                frames.append(kp)
        except Exception as e:
            errors.append({"type": "파싱 오류", "file": filepath, "error": str(e)})

    if len(frames) < MIN_FRAMES:
        errors.append({"type": "프레임 부족", "file": folder, "error": f"{len(frames)}프레임"})
        continue

    # 30프레임으로 정규화
    normalized = normalize_frames_avatar(frames)

    # 아바타 JSON 구성
    avatar_data = {
        "word_id":   word_id,
        "word_name": word_name,
        "frames": [
            {
                "frame":      i,
                "left_hand":  normalized[i]["left_hand"],
                "right_hand": normalized[i]["right_hand"],
                "face":       normalized[i]["face"],
                "pose":       normalized[i]["pose"]
            }
            for i in range(len(normalized))
        ]
    }

    # GCS 업로드
    avatar_json = json.dumps(avatar_data, ensure_ascii=False)
    bucket.blob(f"processed/avatars/WORD{word_id:04d}.json").upload_from_string(
        avatar_json, content_type="application/json"
    )

    # 10단어마다 진행상황 출력 및 저장
    if word_id % 10 == 0:
        print(f"[{word_id}/3000] 처리 중... | 오류: {len(errors)}개")
        save_checkpoint(word_id)

# ── 최종 완료 ──────────────────────────────────────
print(f"\n아바타 JSON 생성 완료!")
print(f"오류 총 {len(errors)}개")

if errors:
    types = Counter([e["type"] for e in errors])
    print("\n오류 유형별 집계:")
    for t, count in types.items():
        print(f"  {t}: {count}개")

# 진행상황 파일 삭제
progress_file = os.path.join(SAVE_PATH, "avatar_progress.txt")
if os.path.exists(progress_file):
    os.remove(progress_file)
    print("진행상황 파일 삭제 완료!")

print(f"\nGCS 경로: processed/avatars/WORD0001.json ~ WORD3000.json")