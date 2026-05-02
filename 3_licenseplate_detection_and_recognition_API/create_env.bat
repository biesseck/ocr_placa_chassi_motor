@echo off

conda create -n licenseplate_ocr_api_py310 python=3.10 -y
conda activate licenseplate_ocr_api_py310

pip3 install -r requirements.txt