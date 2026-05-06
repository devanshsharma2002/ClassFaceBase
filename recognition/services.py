import cv2
import mediapipe as mp
import numpy as np

from academics.models import StudentFaceImage
from attendance.models import AttendancePhoto, AttendanceRecord

MATCH_THRESHOLD = 0.45

mp_face_detection = mp.solutions.face_detection


def detect_and_crop_faces(image_bgr):
    faces = []
    if image_bgr is None:
        return faces

    h, w = image_bgr.shape[:2]

    with mp_face_detection.FaceDetection(
        model_selection=1,
        min_detection_confidence=0.5
    ) as detector:
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = detector.process(rgb)

        if not results.detections:
            return faces

        for detection in results.detections:
            bbox = detection.location_data.relative_bounding_box

            x1 = max(int(bbox.xmin * w), 0)
            y1 = max(int(bbox.ymin * h), 0)
            bw = int(bbox.width * w)
            bh = int(bbox.height * h)

            x2 = min(x1 + bw, w)
            y2 = min(y1 + bh, h)

            if x2 <= x1 or y2 <= y1:
                continue

            face = image_bgr[y1:y2, x1:x2]
            if face.size == 0:
                continue

            faces.append(face)

    return faces


def normalize_face(face_bgr):
    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (160, 160))
    gray = cv2.equalizeHist(gray)
    return gray


def orb_similarity(face1_bgr, face2_bgr):
    img1 = normalize_face(face1_bgr)
    img2 = normalize_face(face2_bgr)

    orb = cv2.ORB_create(nfeatures=256)
    kp1, des1 = orb.detectAndCompute(img1, None)
    kp2, des2 = orb.detectAndCompute(img2, None)

    if des1 is None or des2 is None:
        return 0.0

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(des1, des2)

    if not matches:
        return 0.0

    matches = sorted(matches, key=lambda x: x.distance)
    good_matches = [m for m in matches if m.distance < 60]

    max_keypoints = max(len(kp1), len(kp2), 1)
    return len(good_matches) / max_keypoints


def histogram_similarity(face1_bgr, face2_bgr):
    img1 = normalize_face(face1_bgr)
    img2 = normalize_face(face2_bgr)

    hist1 = cv2.calcHist([img1], [0], None, [256], [0, 256])
    hist2 = cv2.calcHist([img2], [0], None, [256], [0, 256])

    cv2.normalize(hist1, hist1)
    cv2.normalize(hist2, hist2)

    score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    return max(0.0, min(float(score), 1.0))


def compare_faces(face1_bgr, face2_bgr):
    orb_score = orb_similarity(face1_bgr, face2_bgr)
    hist_score = histogram_similarity(face1_bgr, face2_bgr)

    combined = (0.7 * orb_score) + (0.3 * hist_score)
    return round(float(combined), 4)


def generate_embedding(image_path):
    try:
        image = cv2.imread(image_path)
        if image is None:
            return None

        faces = detect_and_crop_faces(image)
        if not faces:
            return None

        face = normalize_face(faces[0])
        return face.tolist()

    except Exception as exc:
        print(f"ERROR generating face data for {image_path}: {exc}")
        return None


def store_embedding_for_image(face_image):
    if not face_image.image:
        return False

    embedding = generate_embedding(face_image.image.path)

    if embedding:
        face_image.embedding_data = embedding
        face_image.quality_score = 1.0
        face_image.save(update_fields=['embedding_data', 'quality_score'])
        print(f"SUCCESS: stored face data for StudentFaceImage #{face_image.id}")
        return True

    print(f"FAILED: no face data generated for StudentFaceImage #{face_image.id}")
    return False


def generate_student_embeddings():
    images = StudentFaceImage.objects.filter(
        is_active=True,
        embedding_data__isnull=True
    ).select_related('student')

    total = images.count()
    success = 0

    for img in images:
        if store_embedding_for_image(img):
            success += 1

    return f"Generated {success}/{total} face templates"


def get_known_student_faces():
    student_faces = []

    images = StudentFaceImage.objects.filter(
        is_active=True,
        image__isnull=False,
        student__isnull=False
    ).select_related('student')

    for img in images:
        try:
            ref_image = cv2.imread(img.image.path)
            if ref_image is None:
                continue

            faces = detect_and_crop_faces(ref_image)
            if not faces:
                print(f"No face found in StudentFaceImage #{img.id}")
                continue

            student_faces.append({
                'student_id': img.student_id,
                'face_image_id': img.id,
                'face': faces[0],
            })

        except Exception as exc:
            print(f"ERROR loading student face #{img.id}: {exc}")

    return student_faces


def process_attendance_photos(session):
    known_faces = get_known_student_faces()

    if not known_faces:
        return False, "No known student face images found."

    photos = AttendancePhoto.objects.filter(
        attendance_session=session,
        image__isnull=False
    )

    if not photos.exists():
        return False, "No attendance photos found."

    matched_students = {}

    for photo in photos:
        try:
            image = cv2.imread(photo.image.path)
            if image is None:
                print(f"Could not read photo #{photo.id}")
                continue

            detected_faces = detect_and_crop_faces(image)

            if not detected_faces:
                print(f"No faces detected in photo #{photo.id}")
                continue

            for detected_face in detected_faces:
                best_student_id = None
                best_score = 0.0

                for known in known_faces:
                    score = compare_faces(detected_face, known['face'])

                    if score > best_score:
                        best_score = score
                        best_student_id = known['student_id']

                if best_student_id is not None and best_score >= MATCH_THRESHOLD:
                    if best_student_id not in matched_students:
                        matched_students[best_student_id] = {
                            'count': 0,
                            'best_score': best_score,
                        }

                    matched_students[best_student_id]['count'] += 1
                    matched_students[best_student_id]['best_score'] = max(
                        matched_students[best_student_id]['best_score'],
                        best_score
                    )

        except Exception as exc:
            print(f"ERROR processing attendance photo #{photo.id}: {exc}")

    updated_present = 0

    for record in session.records.all():
        if record.student_id in matched_students:
            match_info = matched_students[record.student_id]
            record.status = AttendanceRecord.Status.PRESENT
            record.confidence_score = round(match_info['best_score'], 4)
            record.recognized_in_photo_count = match_info['count']
            record.reviewed_manually = False
            record.remarks = 'Marked present by MediaPipe + OpenCV matching'
            record.save()
            updated_present += 1
        else:
            record.status = AttendanceRecord.Status.ABSENT
            record.confidence_score = 0.0
            record.recognized_in_photo_count = 0
            record.reviewed_manually = False
            record.remarks = 'Not recognized in uploaded photos'
            record.save()

    return True, f"Processed {photos.count()} photos and updated {updated_present} present records."