import tensorflow as tf
from tensorflow.keras.models import load_model
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "disease_cnn_multiclass.h5")

# Load model WITHOUT compiling (best practice for inference)
cnn_model = load_model(MODEL_PATH, compile=False)

# 🔥 FORCE BUILD THE MODEL GRAPH (THIS FIXES ALL ERRORS)
cnn_model(tf.zeros((1, 224, 224, 3)))
