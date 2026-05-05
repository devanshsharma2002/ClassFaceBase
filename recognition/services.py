import numpy as np
import face_recognition

from academics.models import StudentFaceImage
from attendance.models import AttendancePhoto, AttendanceRecord


MATCH_TOLERANCE = 0.50


def generate_embedding(image_path):
    try:
        image = face_recognition.load_image_file(image_path)

        face_locations = face_recognition.face_locations(
            image,
            model="hog",
            number_of_times_to_upsample=2
        )

        if not face_locations:
            return None

        encodings = face_recognition.face_encodings(
            image,
            known_face_locations=face_locations,
            num_jitters=2
        )

        if not encodings:
            return None

        return encodings[0].tolist()

    except Exception as exc:
        print(f"ERROR generating embedding for {image_path}: {exc}")
        return None


def store_embedding_for_image(face_image):
    if not face_image.image:
        return False

    embedding = generate_embedding(face_image.image.path)

    if embedding:
        face_image.embedding_data = embedding
        face_image.quality_score = 1.0
        face_image.save(update_fields=['embedding_data', 'quality_score'])
        print(f"SUCCESS: stored embedding for StudentFaceImage #{face_image.id}")
        return True

    print(f"FAILED: no face encoding generated for StudentFaceImage #{face_image.id}")
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

    return f"Generated {success}/{total} embeddings"


def get_known_student_encodings():
    known_encodings = []
    known_student_ids = []

    images = StudentFaceImage.objects.filter(
        is_active=True,
        embedding_data__isnull=False,
        student__isnull=False
    ).select_related('student')

    for img in images:
        try:
            known_encodings.append(np.array(img.embedding_data, dtype=np.float64))
            known_student_ids.append(img.student_id)
        except Exception as exc:
            print(f"ERROR loading embedding from StudentFaceImage #{img.id}: {exc}")

    return known_encodings, known_student_ids


def process_attendance_photos(session):
    known_encodings, known_student_ids = get_known_student_encodings()

    if not known_encodings:
        return False, "No known student embeddings found."

    photos = AttendancePhoto.objects.filter(
        attendance_session=session,
        image__isnull=False
    )

    if not photos.exists():
        return False, "No attendance photos found."

    matched_students = {}

    for photo in photos:
        try:
            image = face_recognition.load_image_file(photo.image.path)

            face_locations = face_recognition.face_locations(
                image,
                model="hog",
                number_of_times_to_upsample=1
            )

            if not face_locations:
                print(f"No faces detected in photo #{photo.id}")
                continue

            face_encodings = face_recognition.face_encodings(
                image,
                known_face_locations=face_locations
            )

            for face_encoding in face_encodings:
                distances = face_recognition.face_distance(known_encodings, face_encoding)

                if len(distances) == 0:
                    continue

                best_match_index = int(np.argmin(distances))
                best_distance = float(distances[best_match_index])

                if best_distance < MATCH_TOLERANCE:
                    student_id = known_student_ids[best_match_index]

                    if student_id not in matched_students:
                        matched_students[student_id] = {
                            'count': 0,
                            'best_distance': best_distance,
                        }

                    matched_students[student_id]['count'] += 1
                    matched_students[student_id]['best_distance'] = min(
                        matched_students[student_id]['best_distance'],
                        best_distance
                    )

        except Exception as exc:
            print(f"ERROR processing attendance photo #{photo.id}: {exc}")

    updated_present = 0

    for record in session.records.all():
        if record.student_id in matched_students:
            match_info = matched_students[record.student_id]
            record.status = AttendanceRecord.Status.PRESENT
            record.confidence_score = round(1 - match_info['best_distance'], 4)
            record.recognized_in_photo_count = match_info['count']
            record.reviewed_manually = False
            record.remarks = 'Marked present by face recognition'
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