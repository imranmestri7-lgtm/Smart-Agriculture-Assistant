import json
import os

import numpy as np
import tensorflow as tf

from datasets import load_dataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


# ==================================================
# CONFIGURATION
# ==================================================

DATASET_NAME = "geraldmc/plantvillage-tiny"
DATASET_REVISION = "v0.1.0"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS = 5
RANDOM_STATE = 42

MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "plant_disease_model.keras")
LABELS_PATH = os.path.join(MODEL_DIR, "class_labels.json")


# ==================================================
# REPRODUCIBILITY AND DIRECTORIES
# ==================================================

tf.keras.utils.set_random_seed(RANDOM_STATE)
os.makedirs(MODEL_DIR, exist_ok=True)


# ==================================================
# LOAD DATASET
# ==================================================

print("\nLoading PlantVillage dataset...")

dataset = load_dataset(
    DATASET_NAME,
    revision=DATASET_REVISION,
    split="train"
)

print("Total images:", len(dataset))


# ==================================================
# PREPARE LABELS
# ==================================================

labels = [str(item) for item in dataset["class_label"]]

label_encoder = LabelEncoder()
encoded_labels = label_encoder.fit_transform(labels)

class_names = label_encoder.classes_.tolist()
number_of_classes = len(class_names)

print("Number of disease classes:", number_of_classes)
print("Classes:", class_names)


# ==================================================
# SPLIT DATA
# ==================================================

indices = np.arange(len(dataset))

train_indices, validation_indices = train_test_split(
    indices,
    test_size=0.20,
    random_state=RANDOM_STATE,
    stratify=encoded_labels
)

print("Training images:", len(train_indices))
print("Validation images:", len(validation_indices))


# ==================================================
# CONVERT IMAGES
# ==================================================

print("\nPreparing images...")

images = []

for index, example in enumerate(dataset):
    image = example["image"].convert("RGB")
    image = image.resize(IMAGE_SIZE)

    images.append(np.asarray(image, dtype=np.uint8))

    if (index + 1) % 200 == 0:
        print(f"Processed {index + 1}/{len(dataset)} images")

images = np.asarray(images, dtype=np.uint8)

train_images = images[train_indices]
validation_images = images[validation_indices]

train_labels = encoded_labels[train_indices]
validation_labels = encoded_labels[validation_indices]

del images


# ==================================================
# DATA PIPELINES
# ==================================================

def prepare_image(image, label):
    image = tf.cast(image, tf.float32)

    image = tf.keras.applications.mobilenet_v2.preprocess_input(
        image
    )

    return image, label


train_dataset = tf.data.Dataset.from_tensor_slices(
    (train_images, train_labels)
)

train_dataset = (
    train_dataset
    .shuffle(len(train_images), seed=RANDOM_STATE)
    .batch(BATCH_SIZE)
    .map(prepare_image, num_parallel_calls=tf.data.AUTOTUNE)
    .prefetch(tf.data.AUTOTUNE)
)

validation_dataset = tf.data.Dataset.from_tensor_slices(
    (validation_images, validation_labels)
)

validation_dataset = (
    validation_dataset
    .batch(BATCH_SIZE)
    .map(prepare_image, num_parallel_calls=tf.data.AUTOTUNE)
    .prefetch(tf.data.AUTOTUNE)
)


# ==================================================
# BUILD TRANSFER-LEARNING MODEL
# ==================================================

print("\nBuilding MobileNetV2 model...")

base_model = tf.keras.applications.MobileNetV2(
    input_shape=(224, 224, 3),
    include_top=False,
    weights="imagenet"
)

base_model.trainable = False

inputs = tf.keras.Input(shape=(224, 224, 3))

x = base_model(inputs, training=False)
x = tf.keras.layers.GlobalAveragePooling2D()(x)
x = tf.keras.layers.Dropout(0.25)(x)

outputs = tf.keras.layers.Dense(
    number_of_classes,
    activation="softmax"
)(x)

model = tf.keras.Model(inputs, outputs)

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()


# ==================================================
# TRAIN MODEL
# ==================================================

print("\nStarting training...")

early_stopping = tf.keras.callbacks.EarlyStopping(
    monitor="val_loss",
    patience=2,
    restore_best_weights=True
)

history = model.fit(
    train_dataset,
    validation_data=validation_dataset,
    epochs=EPOCHS,
    callbacks=[early_stopping]
)


# ==================================================
# EVALUATE MODEL
# ==================================================

print("\nEvaluating model...")

validation_loss, validation_accuracy = model.evaluate(
    validation_dataset,
    verbose=1
)

print(f"Validation loss: {validation_loss:.4f}")
print(f"Validation accuracy: {validation_accuracy:.4f}")


# ==================================================
# SAVE MODEL AND LABELS
# ==================================================

print("\nSaving trained model...")

model.save(MODEL_PATH)

with open(LABELS_PATH, "w", encoding="utf-8") as file:
    json.dump(class_names, file, ensure_ascii=False, indent=2)

print("\nTraining completed!")
print("Model saved to:", MODEL_PATH)
print("Labels saved to:", LABELS_PATH)
print(f"Validation accuracy: {validation_accuracy:.2%}")