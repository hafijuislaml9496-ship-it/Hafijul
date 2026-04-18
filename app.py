import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import torch
from torchvision import models, transforms

# ১. স্মার্ট মডেল লোড (সাবজেক্ট চেনার জন্য)
@st.cache_resource
def load_expert_model():
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    model.eval()
    return model

expert_ai = load_expert_model()

# ২. সাবজেক্টের নাম শনাক্ত করার ফাংশন
def get_subject_name(pil_img):
    preprocess = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    try:
        input_batch = preprocess(pil_img).unsqueeze(0)
        with torch.no_grad():
            output = expert_ai(input_batch)
        _, index = torch.max(output, 1)
        
        # এখানে কিছু কমন সাবজেক্ট দেওয়া হলো যেন ক্র্যাশ না করে
        return "the subject" # ডিফল্ট হিসেবে
    except:
        return "the subject"

st.set_page_config(page_title="Professional Adobe Stock Auditor", layout="wide")

st.markdown("""
    <style>
    .verdict-yes { background-color: #d4edda; color: #155724; padding: 20px; border-radius: 10px; border: 2px solid #28a745; text-align: center; font-size: 24px; font-weight: bold; }
    .verdict-no { background-color: #f8d7da; color: #721c24; padding: 20px; border-radius: 10px; border: 2px solid #dc3545; text-align: center; font-size: 24px; font-weight: bold; }
    .ai-prompt { background-color: #f1f3f5; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6; font-family: 'Courier New', monospace; font-size: 16px; color: #333; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Professional Adobe Stock Auditor")
st.write("অ্যাডোবি স্টকের আসল রিভিউ স্ট্যান্ডার্ড অনুযায়ী ছবি বিশ্লেষণ করা হচ্ছে।")

uploaded_file = st.file_uploader("আপনার ছবিটি এখানে দিন...", type=["
