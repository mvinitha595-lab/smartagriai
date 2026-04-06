
import os
import tensorflow as tf
from django.conf import settings

# absolute path to model
MODEL_PATH = os.path.join(
    settings.BASE_DIR,
    "ml_models",
    "disease_cnn_multiclass.h5"
)

# load model ONCE
disease_cnn_model = tf.keras.models.load_model(MODEL_PATH)

print("✅ Disease CNN model loaded successfully")
