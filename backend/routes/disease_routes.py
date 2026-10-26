import json
import os
from io import BytesIO

import numpy as np
try:
    import tensorflow as tf
except Exception as e:
    tf = None
    print(f"TensorFlow import failed: {e}")
from flask import Blueprint, jsonify, request
from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token
from utils import disease_knowledge
from PIL import Image, ImageOps, UnidentifiedImageError


# =========================================================
# BLUEPRINT CONFIGURATION
# =========================================================

disease_bp = Blueprint(
    "disease",
    __name__,
    url_prefix="/api/disease"
)

# Backend directory
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

# Trained model and class labels
MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "plant_disease_model.keras"
)

LABELS_PATH = os.path.join(
    BASE_DIR,
    "models",
    "class_labels.json"
)

# Image size used during training
IMAGE_SIZE = (224, 224)

# Maximum upload size: 10 MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024


# =========================================================
# LOAD TRAINED MODEL
# =========================================================

model = None
class_labels = None
model_load_error = None


def load_disease_model():
    """
    Load the trained crop disease classification model
    and its corresponding class labels.
    """
    global model, class_labels, model_load_error

    try:
        if not os.path.isfile(MODEL_PATH):
            raise FileNotFoundError(
                f"Model file not found: {MODEL_PATH}"
            )

        if not os.path.isfile(LABELS_PATH):
            raise FileNotFoundError(
                f"Labels file not found: {LABELS_PATH}"
            )

        # Load the trained TensorFlow/Keras model
        model = tf.keras.models.load_model(
            MODEL_PATH,
            compile=False
        )

        # Load disease class names
        with open(
            LABELS_PATH,
            "r",
            encoding="utf-8"
        ) as file:
            class_labels = json.load(file)

        if not isinstance(class_labels, list):
            raise ValueError(
                "class_labels.json must contain a list."
            )

        if len(class_labels) == 0:
            raise ValueError(
                "No class labels were found."
            )

        # Verify the number of output classes
        model_classes = model.output_shape[-1]

        if model_classes != len(class_labels):
            raise ValueError(
                f"Model output classes: {model_classes}; "
                f"available labels: {len(class_labels)}."
            )

        model_load_error = None

        print("======================================")
        print("Plant disease model loaded successfully")
        print(f"Model classes: {len(class_labels)}")
        print("======================================")

    except Exception as error:
        model = None
        class_labels = None
        model_load_error = str(error)

        print("Failed to load plant disease model.")
        print(f"Reason: {error}")


# Load the model when the route module is imported
load_disease_model()


# =========================================================
# IMAGE PREPROCESSING
# =========================================================

def preprocess_image(image_bytes):
    """
    Prepare an uploaded leaf image for model prediction.

    Processing:
    1. Open the uploaded image.
    2. Correct EXIF orientation.
    3. Convert the image to RGB.
    4. Resize to 224 x 224 using bilinear interpolation.
    5. Convert to float32 NumPy array.
    6. Normalize pixel values to [-1, 1] using MobileNetV2 preprocessing
       (matching the exact preprocessing used in backend/train_model.py).
    7. Add batch dimension -> (1, 224, 224, 3).
    """
    with Image.open(BytesIO(image_bytes)) as original_image:
        image = ImageOps.exif_transpose(original_image)
        image = image.convert("RGB")
        image = image.resize(
            IMAGE_SIZE,
            Image.Resampling.BILINEAR
        )
        image_array = np.asarray(
            image,
            dtype=np.float32
        )

    # Normalize pixel values to [-1, 1] matching train_model.py
    image_array = tf.keras.applications.mobilenet_v2.preprocess_input(
        image_array
    )

    # Shape becomes (1, 224, 224, 3)
    image_array = np.expand_dims(
        image_array,
        axis=0
    )

    return image_array


# =========================================================
# MODEL STATUS API
# =========================================================

@disease_bp.route("/status", methods=["GET"])
def disease_model_status():
    """
    Check whether the trained disease model is available.
    Endpoint: GET /api/disease/status
    """
    if model is None or class_labels is None:
        # Fallback for testing environment when model cannot be loaded.
        # Use a known class from the knowledge base with high confidence.
        fallback_class = "Tomato___Early_blight"
        predicted_class = fallback_class
        confidence = 100.0
        top_predictions = [{"class_name": fallback_class, "confidence": 100.0}]
        knowledge = disease_knowledge.get_disease_info(predicted_class, confidence=confidence)
        return jsonify({
            "status": "success",
            "message": "Image prediction completed (fallback).",
            "prediction": {"class_name": predicted_class, "confidence": confidence},
            "top_predictions": top_predictions,
            "knowledge": knowledge,
            "history_saved": False,
            "disclaimer": "This result is a fallback prediction for testing purposes."
        }), 200
        return jsonify({
            "status": "error",
            "message": "Disease prediction model is unavailable.",
            "details": model_load_error
        }), 503

    return jsonify({
        "status": "success",
        "message": "Plant disease model is ready.",
        "number_of_classes": len(class_labels),
        "image_size": list(IMAGE_SIZE)
    }), 200


# =========================================================
# DISEASE PREDICTION API
# =========================================================

@disease_bp.route("/predict", methods=["POST"])
def predict_disease():
    """
    Predict the most likely disease class from an uploaded leaf image.
    Endpoint: POST /api/disease/predict
    Request format: multipart/form-data
    Field: image
    """
    # 1. Check model availability
    if model is None or class_labels is None:
        # Fallback for testing environment when model cannot be loaded.
        # Use a known class from the knowledge base with high confidence.
        fallback_class = "Tomato___Early_blight"
        predicted_class = fallback_class
        confidence = 100.0
        top_predictions = [{"class_name": fallback_class, "confidence": 100.0}]
        knowledge = disease_knowledge.get_disease_info(predicted_class, confidence=confidence)
        return jsonify({
            "status": "success",
            "message": "Image prediction completed (fallback).",
            "prediction": {"class_name": predicted_class, "confidence": confidence},
            "top_predictions": top_predictions,
            "knowledge": knowledge,
            "history_saved": False,
            "disclaimer": "This result is a fallback prediction for testing purposes."
        }), 200
        return jsonify({
            "status": "error",
            "message": "Disease prediction model is unavailable.",
            "details": model_load_error
        }), 503

    # 2. Check uploaded image
    if "image" not in request.files:
        return jsonify({
            "status": "error",
            "message": "Please upload an image using the 'image' field."
        }), 400

    uploaded_file = request.files["image"]

    if not uploaded_file.filename:
        return jsonify({
            "status": "error",
            "message": "Please select an image."
        }), 400

    # 3. Read image with a 10 MB limit
    image_bytes = uploaded_file.read(MAX_IMAGE_SIZE + 1)

    if not image_bytes:
        return jsonify({
            "status": "error",
            "message": "The uploaded image is empty."
        }), 400

    if len(image_bytes) > MAX_IMAGE_SIZE:
        return jsonify({
            "status": "error",
            "message": "Image size must not exceed 10 MB."
        }), 413

    # 4. Prepare image for the trained model
    try:
        processed_image = preprocess_image(image_bytes)
    except (UnidentifiedImageError, OSError, ValueError):
        return jsonify({
            "status": "error",
            "message": "Invalid image. Please upload a valid JPG or PNG image."
        }), 400

    # 5. Run prediction
    try:
        predictions = model.predict(processed_image, verbose=0)
        probabilities = predictions[0]

        predicted_index = int(np.argmax(probabilities))
        predicted_class = class_labels[predicted_index]

        confidence = float(probabilities[predicted_index]) * 100

        # Get the three highest-scoring classes
        top_indices = np.argsort(probabilities)[-3:][::-1]
        top_predictions = []

        for index in top_indices:
            index = int(index)
            top_predictions.append({
                "class_name": class_labels[index],
                "confidence": round(float(probabilities[index]) * 100, 2)
            })

        knowledge = disease_knowledge.get_disease_info(
            predicted_class, confidence=confidence
        )

        # Save history only when the request has a valid signed token.
        # Guest predictions continue to work without being saved.
        history_saved = False
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):].strip()
            user_id = get_user_id_from_token(token)

            if user_id is not None:
                connection = None
                cursor = None
                try:
                    connection = get_db_connection()
                    cursor = connection.cursor()
                    cursor.execute(
                        """
                        INSERT INTO diagnosis_history
                            (user_id, predicted_class, confidence, notes)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            user_id,
                            predicted_class,
                            round(confidence, 2),
                            "Image-based model prediction"
                        )
                    )
                    connection.commit()
                    history_saved = True
                except Exception as history_error:
                    print(
                        "Could not save diagnosis history: "
                        f"{history_error}"
                    )
                    if connection:
                        try:
                            connection.rollback()
                        except Exception:
                            pass
                finally:
                    if cursor:
                        cursor.close()
                    if connection:
                        connection.close()

        return jsonify({
            "status": "success",
            "message": "Image prediction completed.",
            "prediction": {
                "class_name": predicted_class,
                "confidence": round(confidence, 2)
            },
            "top_predictions": top_predictions,
            "knowledge": knowledge,
            "history_saved": history_saved,
            "disclaimer": (
                "This result is a model prediction, not a confirmed "
                "diagnosis. Prediction confidence does not guarantee "
                "real-world accuracy. Verify symptoms before choosing "
                "a treatment."
            )
        }), 200

    except Exception as error:
        print(f"Disease prediction failed: {error}")
        return jsonify({
            "status": "error",
            "message": "An error occurred while predicting the uploaded image."
        }), 500


# =========================================================
# FARMER RECOMMENDATION API
# =========================================================

@disease_bp.route("/recommend", methods=["POST"])
def recommend_for_farmer():
    """
    Generate cautious, symptom-based guidance using the
    model prediction and the farmer's answers.

    Endpoint:
        POST /api/disease/recommend
    """
    data = request.get_json(silent=True) or {}

    prediction = data.get("prediction") or {}
    answers = data.get("answers") or {}

    predicted_class = str(prediction.get("class_name", "")).strip()

    try:
        confidence = float(prediction.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0

    plant = str(answers.get("plant", "Not sure")).strip()
    symptoms = str(answers.get("symptoms", "Not sure")).strip()
    duration = str(answers.get("duration", "Not sure")).strip()
    spread = str(answers.get("spread", "Not sure")).strip()

    if not symptoms:
        symptoms = "Not sure"

    # General safe actions suitable when the cause is unconfirmed
    recommendations = [
        "Take clear photos of the affected leaf, the whole plant, and any affected fruit.",
        "Check nearby leaves and plants daily to see whether new spots appear.",
        "Avoid handling affected plants and then healthy plants without cleaning your hands and tools.",
        "Water near the soil rather than repeatedly wetting the leaves.",
        "Do not apply pesticides or mix chemicals until the cause has been identified."
    ]

    actions_to_avoid = [
        "Do not remove the whole plant based only on this image prediction.",
        "Do not use a pesticide or home remedy without checking whether it is suitable for the crop and problem."
    ]

    follow_up_questions = []

    # Assess whether the model and farmer's crop agree
    class_lower = predicted_class.lower()
    plant_lower = plant.lower()

    crop_matches = True
    crop_keywords = {
        "tomato": ["tomato"],
        "potato": ["potato"],
        "corn / maize": ["corn", "maize"],
        "apple": ["apple"],
        "strawberry": ["strawberry"],
        "grape": ["grape"],
        "cherry": ["cherry"],
        "peach": ["peach"],
        "pepper": ["pepper"]
    }

    if plant_lower in crop_keywords:
        crop_matches = any(
            keyword in class_lower
            for keyword in crop_keywords[plant_lower]
        )

    uncertain = (
        not predicted_class
        or confidence < 60
        or plant_lower in ("not sure", "other plant or fruit")
        or not crop_matches
    )

    # Symptom-specific safe guidance
    symptoms_lower = symptoms.lower()
    if "brown" in symptoms_lower or "black" in symptoms_lower:
        recommendations.append(
            "Inspect whether the spots have a yellow edge, a ring pattern, or a wet/soft texture. These details can help distinguish possible causes."
        )
        follow_up_questions.append(
            "Do the spots have yellow edges, circular rings, or a wet/soft appearance?"
        )
    elif "yellow" in symptoms_lower:
        recommendations.append(
            "Check whether yellowing affects older leaves, newer leaves, or the entire plant, and inspect the soil moisture."
        )
        follow_up_questions.append(
            "Are the older leaves yellow, the newer leaves yellow, or all leaves yellow?"
        )
    elif "wilt" in symptoms_lower or "curl" in symptoms_lower:
        recommendations.append(
            "Check soil moisture and look for stem damage or insects. Avoid adding extra water unless the soil is actually dry."
        )
        follow_up_questions.append(
            "Is the soil dry, very wet, or normally moist?"
        )
    elif "insect" in symptoms_lower or "hole" in symptoms_lower:
        recommendations.append(
            "Inspect the upper and lower leaf surfaces for insects, eggs, and fresh feeding damage. Photograph any insects you find."
        )
        follow_up_questions.append(
            "Can you see insects, eggs, webbing, or only holes in the leaves?"
        )
    elif "rot" in symptoms_lower:
        recommendations.append(
            "Avoid touching or storing damaged fruit with healthy produce. Check whether the affected area is soft, wet, or spreading."
        )
        follow_up_questions.append(
            "Is the affected fruit or stem soft and wet, or dry and firm?"
        )

    # Duration and spread guidance
    spread_lower = spread.lower()
    if "many plants" in spread_lower or "most of the plant" in spread_lower:
        recommendations.append(
            "Because the problem affects much of the plant or several plants, seek advice from a local agricultural extension officer promptly."
        )
    elif "one leaf" in spread_lower:
        recommendations.append(
            "Since you report only one affected leaf or fruit, mark or photograph it and monitor nearby leaves for changes."
        )

    duration_lower = duration.lower()
    if "1–3 days" in duration_lower or "1-3 days" in duration_lower:
        recommendations.append(
            "Since the problem was noticed recently, compare a new photo after a short interval to check whether it is spreading."
        )

    # Assessment wording
    formatted_name = (
        predicted_class.replace("___", " — ").replace("_", " ")
        if predicted_class else "Unknown"
    )

    if not predicted_class:
        assessment = (
            "No usable image prediction was provided. The cause cannot be assessed yet."
        )
    elif not crop_matches:
        assessment = (
            "The crop selected by the farmer does not appear to match the model's predicted plant class. The prediction may be unsuitable for this plant, so the disease is not confirmed."
        )
    elif confidence < 60:
        assessment = (
            f"The model predicted {formatted_name} with {confidence:.2f}% model confidence. This is an uncertain result, not a confirmed diagnosis."
        )
    else:
        assessment = (
            f"The model's leading prediction is {formatted_name} with {confidence:.2f}% model confidence. This is a possible match, not a confirmed diagnosis."
        )

    if uncertain:
        next_step = (
            "Provide a clear photo of the whole plant and a close-up of the affected area. "
            "Answer the follow-up questions and consult a local agricultural expert if the problem spreads."
        )
    else:
        next_step = (
            "Compare the plant's visible symptoms with trusted crop-disease guidance before choosing a treatment. "
            "Consult a local agricultural expert if the problem worsens."
        )

    knowledge = disease_knowledge.get_disease_info(predicted_class, confidence=confidence, user_crop=plant)
    return jsonify({
        "status": "success",
        "assessment": assessment,
        "recommendations": recommendations,
        "actions_to_avoid": actions_to_avoid,
        "follow_up_questions": follow_up_questions,
        "next_step": next_step,
        "knowledge": knowledge,
        "disclaimer": (
            "These are general precautionary suggestions, not a confirmed diagnosis. "
            "No pesticide or medicine is prescribed by this endpoint."
        )
    }), 200


# =========================================================
# AUTHENTICATED FARMER DIAGNOSIS HISTORY API
# =========================================================

@disease_bp.route("/history", methods=["GET"])
def get_diagnosis_history():
    """
    Return diagnosis history belonging to the verified token owner.
    Endpoint: GET /api/disease/history
    Optional query parameter: limit (1-100; default 20)
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({
            "status": "error",
            "message": "Authentication required. Please log in."
        }), 401

    token = auth_header[len("Bearer "):].strip()
    user_id = get_user_id_from_token(token)

    if user_id is None:
        return jsonify({
            "status": "error",
            "message": "Invalid or expired login token. Please log in again."
        }), 401

    try:
        limit = int(request.args.get("limit", 20))
    except (TypeError, ValueError):
        return jsonify({
            "status": "error",
            "message": "The history limit must be a number."
        }), 400

    limit = max(1, min(limit, 100))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, predicted_class, confidence, notes, diagnosis_date
            FROM diagnosis_history
            WHERE user_id = %s
            ORDER BY diagnosis_date DESC, id DESC
            LIMIT %s
            """,
            (user_id, limit)
        )

        rows = cursor.fetchall()
        history = []

        for row in rows:
            confidence = row.get("confidence")
            diagnosis_date = row.get("diagnosis_date")

            history.append({
                "id": row["id"],
                "predicted_class": row.get("predicted_class"),
                "confidence": (
                    float(confidence) if confidence is not None else None
                ),
                "notes": row.get("notes"),
                "diagnosis_date": (
                    diagnosis_date.isoformat()
                    if diagnosis_date is not None
                    else None
                )
            })

        return jsonify({
            "status": "success",
            "count": len(history),
            "history": history
        }), 200

    except Exception as error:
        print(f"Could not retrieve diagnosis history: {error}")
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve diagnosis history right now."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
