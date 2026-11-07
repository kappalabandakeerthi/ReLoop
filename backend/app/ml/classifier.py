
from pathlib import Path
from io import BytesIO

import torch
import torch.nn as nn
from PIL import Image, UnidentifiedImageError
from torchvision import models, transforms


MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "reloop_device_classifier.pth"
)

DEVICE = torch.device("cpu")

# Same preprocessing used during validation in Colab
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485, 0.456, 0.406],
        [0.229, 0.224, 0.225]
    )
])

model = None
class_names = None


def load_model():
    global model, class_names

    if model is not None:
        return

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found: {MODEL_PATH}"
        )

    checkpoint = torch.load(
        MODEL_PATH,
        map_location=DEVICE,
        weights_only=True
    )

    class_names = checkpoint["class_names"]

    model = models.resnet18(weights=None)
    model.fc = nn.Linear(
        model.fc.in_features,
        len(class_names)
    )

    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(DEVICE)
    model.eval()


def predict_device_image(image_bytes: bytes):
    load_model()

    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValueError("Uploaded file is not a valid image.")

    image_tensor = transform(image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        outputs = model(image_tensor)
        probabilities = torch.softmax(outputs, dim=1)

        top_probabilities, top_indices = torch.topk(
            probabilities,
            k=min(3, len(class_names)),
            dim=1
        )

    predictions = []

    for probability, index in zip(
        top_probabilities[0],
        top_indices[0]
    ):
        predictions.append({
            "category": class_names[index.item()],
            "confidence": round(probability.item() * 100, 2)
        })

    return {
        "predicted_category": predictions[0]["category"],
        "confidence": predictions[0]["confidence"],
        "top_predictions": predictions
    }
