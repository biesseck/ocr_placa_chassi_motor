import os
import sys
import numpy as np
import argparse
import cv2

from jdeskew.estimator import get_angle
from jdeskew.utility import rotate

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
from pytesseract import Output


def parse_args():
    parser = argparse.ArgumentParser(description='Test JDskew')
    parser.add_argument('--input', type=str, required=True, help='Path to the input image')
    # parser.add_argument('--output', type=str, required=True, help='Path to save the output image')
    return parser.parse_args()



if __name__ == '__main__':
    args = parse_args()
    # output_image_path = args.output

    image = cv2.imread(args.input)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # angle = get_angle(image)
    # output_image = rotate(image, angle)
    # print(f"Estimated angle: {angle:.2f} degrees")
    # cv2.imshow('Original Image', image)
    # cv2.imshow('Deskewed Image', output_image)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    text = pytesseract.image_to_string('test.png')
    print("Extracted text: ", text)
    results = pytesseract.image_to_osd(image, output_type=Output.DICT)
    print("[INFO] detected orientation: {}".format(
	    results["orientation"]))
    print("[INFO] rotate by {} degrees to correct".format(
        results["rotate"]))
    print("[INFO] detected script: {}".format(results["script"]))
    print("results: ", results)
    print("Test completed successfully.")