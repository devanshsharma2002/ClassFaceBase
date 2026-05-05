def store_embedding_for_image(face_image):
    embedding = generate_embedding(face_image.image.path)

    if embedding:
        face_image.embedding_data = embedding
        face_image.quality_score = 1.0
        face_image.save(update_fields=['embedding_data', 'quality_score'])
        print(f"SUCCESS: {face_image.image.path}")
        return True

    print(f"FAILED: No face encoding for {face_image.image.path}")
    return False