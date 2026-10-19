import json
import os
from io import BytesIO

import numpy as np
import tensorflow as tf

from flask import Blueprint, jsonify, request
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
    4. Resize to 224 x 224.
    5. Normalize pixel values to the range 0-1.
    6. Add the batch dimension.
    """

    with Image.open(BytesIO(image_bytes)) as original_image:

        # Correct the orientation of mobile photos
        image = ImageOps.exif_transpose(original_image)

        # Convert grayscale or RGBA images to RGB
        image = image.convert("RGB")

        # Resize to the dimensions used during training
        image = image.resize(
            IMAGE_SIZE,
            Image.Resampling.BILINEAR
        )

        # Convert image to NumPy array
        image_array = np.asarray(
            image,
            dtype=np.float32
        )

    # Normalize pixel values from 0-255 to 0-1
    image_array = image_array / 255.0

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

    Endpoint:
        GET /api/disease/status
    """

    if model is None or class_labels is None:
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
    Predict the most likely disease class from a leaf image.

    Endpoint:
        POST /api/disease/predict

    Request format:
        multipart/form-data

    Image field:
        image
    """

    # -----------------------------------------------------
    # 1. Check model availability
    # -----------------------------------------------------

    if model is None or class_labels is None:
        return jsonify({
            "status": "error",
            "message": "Disease prediction model is unavailable.",
            "details": model_load_error
        }), 503

    # -----------------------------------------------------
    # 2. Check image upload
    # -----------------------------------------------------

    if "image" not in request.files:
        return jsonify({
            "status": "error",
            "message": (
                "No image uploaded. "
                "Please upload the image using the 'image' field."
            )
        }), 400

    uploaded_file = request.files["image"]

    if not uploaded_file.filename:
        return jsonify({
            "status": "error",
            "message": "Please select an image."
        }), 400

    # -----------------------------------------------------
    # 3. Read and validate upload size
    # -----------------------------------------------------

    image_bytes = uploaded_file.read(
        MAX_IMAGE_SIZE + 1
    )

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

    # -----------------------------------------------------
    # 4. Preprocess the uploaded image
    # -----------------------------------------------------

    try:
        processed_image = preprocess_image(
            image_bytes
        )

    except (
        UnidentifiedImageError,
        OSError,
        ValueError
    ):
        return jsonify({
            "status": "error",
            "message": (
                "Invalid image. Please upload a valid "
                "JPG, JPEG, PNG, or other supported image."
            )
        }), 400

    # -----------------------------------------------------
    # 5. Predict disease
    # -----------------------------------------------------

    try:
        predictions = model.predict(
            processed_image,
            verbose=0
        )

        probabilities = predictions[0]

        # Find the most likely class
        predicted_index = int(
            np.argmax(probabilities)
        )

        predicted_class = class_labels[
            predicted_index
        ]

        confidence = (
            float(probabilities[predicted_index]) * 100
        )

        # -------------------------------------------------
        # 6. Find the top three predicted classes
        # -------------------------------------------------

        top_indices = np.argsort(
            probabilities
        )[-3:][::-1]

        top_predictions = []

        for index in top_indices:

            index = int(index)

            top_predictions.append({
                "class_name": class_labels[index],
                "confidence": round(
                    float(probabilities[index]) * 100,
                    2
                )
            })

        # -------------------------------------------------
        # 7. Return prediction result
        # -------------------------------------------------

        return jsonify({
            "status": "success",
            "message": "Image prediction completed.",

            "prediction": {
                "class_name": predicted_class,
                "confidence": round(
                    confidence,
                    2
                )
            },

            "top_predictions": top_predictions,

            "disclaimer": (
                "This result is a model prediction, not a "
                "confirmed diagnosis. Prediction confidence "
                "does not guarantee real-world accuracy. "
                "Verify symptoms before choosing a treatment."
            )
        }), 200

    except Exception as error:

        # Print the technical error in the backend terminal
        print(
            f"Disease prediction failed: {error}"
        )

        # Return a safe error message to the client
        return jsonify({
            "status": "error",
            "message": (
                "An error occurred while predicting "
                "the uploaded image."
            )
        }), 500