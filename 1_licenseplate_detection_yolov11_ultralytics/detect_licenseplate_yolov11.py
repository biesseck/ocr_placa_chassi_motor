import os
import sys
import cv2
import numpy as np
import argparse
from ultralytics import YOLO


def parse_arguments():
    parser = argparse.ArgumentParser(description='Detect license plates using YOLOv11')
    parser.add_argument('--model', type=str, default='license-plate-finetune-v1l.pt', help='Path to the YOLO model')
    parser.add_argument('--image', type=str, required=True, help='Path to the input image')
    return parser.parse_args()


def resize_with_scale(image, target_size=640):
    h, w = image.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    resized_image = cv2.resize(image, (new_w, new_h), interpolation=interpolation)
    return resized_image, scale


if __name__ == "__main__":
    args = parse_arguments()

    print(f"Loading img '{args.image}'")
    img = cv2.imread(args.image)
    # img_resized = cv2.resize(img, (640, 640))
    img_resized, scale = resize_with_scale(img, target_size=640)
    cv2.imshow("img_resized", img_resized)
    cv2.waitKey(0)

    print(f"Loading model '{args.model}'")
    model = YOLO(args.model)
    print("    Done")

    print("Performing inference...")
    results = model.predict(source=img_resized, conf=0.60, iou=0.45, max_det=1)
    # print("results:", results)

    if len(results[0].boxes) > 0:
        for result in results:
            for box in result.boxes:
                coords = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = result.names[cls_id]
                print(f"--- Detection Found ---")
                print(f"Label: {label}")
                print(f"Confidence: {conf:.2%}")
                print(f"Coordinates: x1={coords[0]:.1f}, y1={coords[1]:.1f}, x2={coords[2]:.1f}, y2={coords[3]:.1f}")

                # Extract coordinates (top-left x, top-left y, bottom-right x, bottom-right y)
                x1, y1, x2, y2 = box.xyxy[0]
                
                # Convert tensors/floats to integers for OpenCV
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # 4. Draw the red rectangle (BGR format: Red is 0, 0, 255)
                cv2.rectangle(img_resized, (x1, y1), (x2, y2), (0, 0, 255), 2)
                
                # Optional: Add a label
                cv2.putText(img_resized, "License Plate", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # 5. Show on screen
        cv2.imshow('License Plate Detection', img_resized)

        # Keep the window open until a key is pressed
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    else:
        print("No license plate detected.")

    print("Finished\n")
