import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (
    Conv2D, MaxPooling2D, Flatten,
    Dense, Dropout
)
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.optimizers import Adam
import os

# ===============================
# PATHS
# ===============================
BASE_DIR = os.path.dirname(__file__)
DATASET_DIR = os.path.join(BASE_DIR, "..", "cnn_dataset")

TRAIN_DIR = os.path.join(DATASET_DIR, "train")
VAL_DIR = os.path.join(DATASET_DIR, "val")

IMG_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS = 15

# ===============================
# DATA GENERATORS
# ===============================
train_gen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=20,
    zoom_range=0.2,
    horizontal_flip=True
)

val_gen = ImageDataGenerator(rescale=1./255)

train_data = train_gen.flow_from_directory(
    TRAIN_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical"   # 🔥 MULTI-CLASS
)

val_data = val_gen.flow_from_directory(
    VAL_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical"
)

NUM_CLASSES = train_data.num_classes
print("Classes:", train_data.class_indices)

# ===============================
# CNN MODEL (MULTI-CLASS)
# ===============================
model = Sequential([
    Conv2D(32, (3,3), activation="relu", input_shape=(224,224,3)),
    MaxPooling2D(2,2),

    Conv2D(64, (3,3), activation="relu"),
    MaxPooling2D(2,2),

    Conv2D(128, (3,3), activation="relu"),
    MaxPooling2D(2,2),

    Flatten(),
    Dense(128, activation="relu"),
    Dropout(0.5),

    Dense(NUM_CLASSES, activation="softmax")  # 🔥 KEY FIX
])

model.compile(
    optimizer=Adam(learning_rate=0.0001),
    loss="categorical_crossentropy",   # 🔥 KEY FIX
    metrics=["accuracy"]
)

model.summary()

# ===============================
# TRAIN
# ===============================
history = model.fit(
    train_data,
    validation_data=val_data,
    epochs=EPOCHS
)

# ===============================
# SAVE MODEL
# ===============================
MODEL_PATH = os.path.join(BASE_DIR, "disease_cnn_multiclass.h5")
model.save(MODEL_PATH)

print("✅ Model saved at:", MODEL_PATH)
