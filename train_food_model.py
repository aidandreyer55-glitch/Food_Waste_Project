import os
import shutil
import torch
from roboflow import Roboflow
from ultralytics import YOLO


ROBOFLOW_API_KEY = "1faP6vhUAa3i3I0bjSlP"
WORKSPACE_NAME = "aidan-dreyer"
PROJECT_NAME = "food-types-thx5o-motcz"
DATASET_VERSION = 1

EPOCHS = 50
IMAGE_SIZE = 640
BATCH_SIZE = 16



def main():

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        print(f"✅ GPU Detected: {gpu_name} — Training will be super fast!")
        device = 0
    else:
        print("⚠️ WARNING: CUDA GPU not detected. Running on CPU (will be slow).")
        device = "cpu"


    print("\nDownloading dataset from Roboflow...")
    rf = Roboflow(api_key=ROBOFLOW_API_KEY)
    project = rf.workspace(WORKSPACE_NAME).project(PROJECT_NAME)
    version = project.version(DATASET_VERSION)
    dataset = version.download("yolov8")

    # Define the exact path to data.yaml from the downloaded dataset
    data_yaml_path = os.path.join(dataset.location, "data.yaml")

    # 3. Load the base YOLOv8 Segmentation model
    # Use 'yolov8n-seg.pt' (nano/fastest) or 'yolov8s-seg.pt' (small/more accurate)
    model = YOLO("yolov8m-seg.pt")

    # 4. Train the model on your GPU
    print("\nStarting training...")
    results = model.train(
        data=data_yaml_path,
        epochs=EPOCHS,
        imgsz=IMAGE_SIZE,
        batch=BATCH_SIZE,
        device=device,
        project="food_waste_training",
        name="run1",
        workers=2
    )

    # 5. Copy the best weights to the script's directory
    trained_weights = os.path.join(results.save_dir, "weights", "best.pt")
    final_model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best.pt")

    if os.path.exists(trained_weights):
        shutil.copy(trained_weights, final_model_path)
        print(f"\n🎉 Training complete! Your custom model is saved at:\n{final_model_path}")
    else:
        print("\nTraining finished, check the 'food_waste_training/run1/weights' folder for best.pt.")


if __name__ == "__main__":
    main()
