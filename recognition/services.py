import gc

import cv2
import mediapipe as mp
import numpy as np

from academics.models import StudentFaceImage
from attendance.models import AttendancePhoto, AttendanceRecord


MATCH_THRESHOLD = 0.15

mp_face_detection = mp.solutions.face_detection
haar_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def load_image_from_field(image_field):
    if not image_field:
        return None

    try:
        image_field.open("rb")
        file_bytes = image_field.read()
        image_field.close()

        if not file_bytes:
            return None

        np_arr = np.frombuffer(file_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return image
    except Exception as exc:
        print(f"ERROR loading image field: {exc}")
        return None


def preprocess_for_detection(image_bgr):
    if image_bgr is None:
        return None

    image = image_bgr.copy()
    image = cv2.convertScaleAbs(image, alpha=1.10, beta=8)

    h, w = image.shape[:2]

    max_width = 960
    min_width = 700

    if w > max_width:
        scale = max_width / w
        image = cv2.resize(
            image,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_AREA,
        )
    elif w < min_width:
        scale = min_width / w
        image = cv2.resize(
            image,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC,
        )

    return image


def run_mediapipe_detection(image_bgr, model_selection=0, min_conf=0.35):
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    with mp_face_detection.FaceDetection(
        model_selection=model_selection,
        min_detection_confidence=min_conf,
    ) as detector:
        results = detector.process(rgb)
    return results.detections if results and results.detections else []


def run_haar_detection(image_bgr):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = haar_cascade.detectMultiScale(
        gray,
        scaleFactor=1.08,
        minNeighbors=5,
        minSize=(50, 50),
    )
    return faces


def deduplicate_boxes(boxes, tolerance=25):
    final_boxes = []

    for x1, y1, x2, y2 in boxes:
        duplicate = False
        for fx1, fy1, fx2, fy2 in final_boxes:
            if (
                abs(x1 - fx1) < tolerance
                and abs(y1 - fy1) < tolerance
                and abs(x2 - fx2) < tolerance
                and abs(y2 - fy2) < tolerance
            ):
                duplicate = True
                break
        if not duplicate:
            final_boxes.append((x1, y1, x2, y2))

    return final_boxes


def detect_and_crop_faces(image_bgr):
    if image_bgr is None:
        return []

    original = image_bgr.copy()
    oh, ow = original.shape[:2]

    processed = preprocess_for_detection(original)
    ph, pw = processed.shape[:2]

    detections = []
    for model_selection, min_conf in [(0, 0.35), (1, 0.35)]:
        detections = run_mediapipe_detection(
            processed,
            model_selection=model_selection,
            min_conf=min_conf,
        )
        if detections:
            break

    boxes = []

    for detection in detections:
        bbox = detection.location_data.relative_bounding_box

        x1 = max(int(bbox.xmin * pw), 0)
        y1 = max(int(bbox.ymin * ph), 0)
        bw = int(bbox.width * pw)
        bh = int(bbox.height * ph)

        x2 = min(x1 + bw, pw)
        y2 = min(y1 + bh, ph)

        if x2 <= x1 or y2 <= y1:
            continue

        ox1 = int(x1 * ow / pw)
        oy1 = int(y1 * oh / ph)
        ox2 = int(x2 * ow / pw)
        oy2 = int(y2 * oh / ph)

        pad_x = int((ox2 - ox1) * 0.16)
        pad_y = int((oy2 - oy1) * 0.20)

        ox1 = max(0, ox1 - pad_x)
        oy1 = max(0, oy1 - pad_y)
        ox2 = min(ow, ox2 + pad_x)
        oy2 = min(oh, oy2 + pad_y)

        if (ox2 - ox1) >= 60 and (oy2 - oy1) >= 60:
            boxes.append((ox1, oy1, ox2, oy2))

    if not boxes:
        haar_faces = run_haar_detection(processed)
        for (x, y, w, h) in haar_faces:
            x1 = max(int(x * ow / pw), 0)
            y1 = max(int(y * oh / ph), 0)
            x2 = min(int((x + w) * ow / pw), ow)
            y2 = min(int((y + h) * oh / ph), oh)

            pad_x = int((x2 - x1) * 0.12)
            pad_y = int((y2 - y1) * 0.16)

            x1 = max(0, x1 - pad_x)
            y1 = max(0, y1 - pad_y)
            x2 = min(ow, x2 + pad_x)
            y2 = min(oh, y2 + pad_y)

            if (x2 - x1) >= 60 and (y2 - y1) >= 60:
                boxes.append((x1, y1, x2, y2))

    boxes = deduplicate_boxes(boxes)

    faces = []
    for x1, y1, x2, y2 in boxes[:10]:
        crop = original[y1:y2, x1:x2]
        if crop.size != 0:
            faces.append(crop)

    return faces


def normalize_face(face_bgr):
    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (128, 128))
    gray = cv2.equalizeHist(gray)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return gray


def orb_similarity(face1_bgr, face2_bgr):
    img1 = normalize_face(face1_bgr)
    img2 = normalize_face(face2_bgr)

    orb = cv2.ORB_create(nfeatures=300)
    kp1, des1 = orb.detectAndCompute(img1, None)
    kp2, des2 = orb.detectAndCompute(img2, None)

    if des1 is None or des2 is None or not kp1 or not kp2:
        return 0.0

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(des1, des2)

    if not matches:
        return 0.0

    good_matches = [m for m in matches if m.distance < 65]
    max_keypoints = max(len(kp1), len(kp2), 1)

    return len(good_matches) / max_keypoints


def histogram_similarity(face1_bgr, face2_bgr):
    img1 = normalize_face(face1_bgr)
    img2 = normalize_face(face2_bgr)

    hist1 = cv2.calcHist([img1], [0], None, [128], [0, 256])
    hist2 = cv2.calcHist([img2], [0], None, [128], [0, 256])

    cv2.normalize(hist1, hist1)
    cv2.normalize(hist2, hist2)

    score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    return max(0.0, min(float(score), 1.0))


def compare_faces(face1_bgr, face2_bgr):
    orb_score = orb_similarity(face1_bgr, face2_bgr)
    hist_score = histogram_similarity(face1_bgr, face2_bgr)
    return round((0.7 * orb_score) + (0.3 * hist_score), 4)


def generate_embedding_from_field(image_field):
    try:
        image = load_image_from_field(image_field)
        if image is None:
            print("Could not read image from storage")
            return None

        faces = detect_and_crop_faces(image)
        if not faces:
            print("No face detected in stored image")
            return None

        face = normalize_face(faces[0])

        del image
        del faces
        gc.collect()

        return face.tolist()

    except Exception as exc:
        print(f"ERROR generating face data: {exc}")
        return None


def store_embedding_for_image(face_image):
    if not face_image.image:
        return False

    embedding = generate_embedding_from_field(face_image.image)

    if embedding:
        face_image.embedding_data = embedding
        face_image.quality_score = 1.0
        face_image.save(update_fields=["embedding_data", "quality_score"])
        print(f"SUCCESS: stored face data for StudentFaceImage #{face_image.id}")
        return True

    print(f"FAILED: no face data generated for StudentFaceImage #{face_image.id}")
    return False


def generate_student_embeddings():
    images = StudentFaceImage.objects.filter(
        is_active=True,
        image__isnull=False,
    ).select_related("student")

    total = images.count()
    success = 0

    for img in images:
        if store_embedding_for_image(img):
            success += 1
        gc.collect()

    return f"Generated {success}/{total} face templates"


def get_known_student_faces():
    student_faces = []

    images = StudentFaceImage.objects.filter(
        is_active=True,
        image__isnull=False,
        student__isnull=False,
    ).select_related("student")

    for img in images:
        try:
            ref_image = load_image_from_field(img.image)

            if ref_image is None:
                print(f"Could not read student face image #{img.id}")
                continue

            faces = detect_and_crop_faces(ref_image)
            if not faces:
                print(f"No face found in StudentFaceImage #{img.id}")
                del ref_image
                gc.collect()
                continue

            student_faces.append(
                {
                    "student_id": img.student_id,
                    "face_image_id": img.id,
                    "face": faces[0],
                }
            )

            del ref_image
            del faces
            gc.collect()

        except Exception as exc:
            print(f"ERROR loading student face #{img.id}: {exc}")
            gc.collect()

    print(f"Loaded {len(student_faces)} known student face(s)")
    return student_faces


def process_attendance_photos(session):
    known_faces = get_known_student_faces()

    if not known_faces:
        return False, "No known student face images found."

    photos = AttendancePhoto.objects.filter(
        attendance_session=session,
        image__isnull=False,
    )

    if not photos.exists():
        return False, "No attendance photos found."

    matched_students = {}

    for photo in photos:
        try:
            image = load_image_from_field(photo.image)

            if image is None:
                print(f"Could not read attendance photo #{photo.id}")
                continue

            detected_faces = detect_and_crop_faces(image)
            print(f"Photo #{photo.id}: detected {len(detected_faces)} faces")

            if not detected_faces:
                del image
                gc.collect()
                continue

            face_best_matches = []

            for idx, detected_face in enumerate(detected_faces, start=1):
                best_student_id = None
                best_score = 0.0

                for known in known_faces:
                    score = compare_faces(detected_face, known["face"])
                    print(
                        f"Photo #{photo.id}, face #{idx}, compare with student {known['student_id']} -> score={score}"
                    )
                    if score > best_score:
                        best_score = score
                        best_student_id = known["student_id"]

                print(
                    f"Photo #{photo.id}, face #{idx}, best_student_id={best_student_id}, best_score={best_score}"
                )

                if best_student_id is not None and best_score >= MATCH_THRESHOLD:
                    face_best_matches.append((best_student_id, best_score))

            best_per_student = {}
            for student_id, score in face_best_matches:
                if student_id not in best_per_student or score > best_per_student[student_id]:
                    best_per_student[student_id] = score

            for student_id, score in best_per_student.items():
                if student_id not in matched_students:
                    matched_students[student_id] = {
                        "count": 0,
                        "best_score": score,
                    }

                matched_students[student_id]["count"] += 1
                matched_students[student_id]["best_score"] = max(
                    matched_students[student_id]["best_score"],
                    score,
                )

            del image
            del detected_faces
            del face_best_matches
            gc.collect()

        except Exception as exc:
            print(f"ERROR processing attendance photo #{photo.id}: {exc}")
            gc.collect()

    print(f"Matched students map: {matched_students}")

    updated_present = 0
    session_records = session.records.select_related("student").all()

    for record in session_records:
        if record.student_id in matched_students:
            match_info = matched_students[record.student_id]
            record.status = AttendanceRecord.Status.PRESENT
            record.confidence_score = round(match_info["best_score"], 4)
            record.recognized_in_photo_count = match_info["count"]
            record.marked_by_system = True
            record.remarks = "Marked present by AI face matching"
            record.save(
                update_fields=[
                    "status",
                    "confidence_score",
                    "recognized_in_photo_count",
                    "marked_by_system",
                    "remarks",
                ]
            )
            updated_present += 1
        else:
            record.status = AttendanceRecord.Status.ABSENT
            record.confidence_score = 0.0
            record.recognized_in_photo_count = 0
            record.marked_by_system = False
            record.remarks = "Face not matched in uploaded photo(s)"
            record.save(
                update_fields=[
                    "status",
                    "confidence_score",
                    "recognized_in_photo_count",
                    "marked_by_system",
                    "remarks",
                ]
            )

    gc.collect()
    return True, f"Processed {photos.count()} photo(s) and marked {updated_present} student(s) present."