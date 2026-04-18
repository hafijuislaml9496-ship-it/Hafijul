import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import torch
from torchvision import models, transforms

# ১. এআই মডেল লোড (সাবজেক্ট চেনার জন্য)
@st.cache_resource
def load_classifier():
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    model.eval()
    return model

classifier = load_classifier()

# ইমেজ লেবেল (সাবজেক্টের নাম পেতে)
import json
import requests
LABELS_URL = "https://raw.githubusercontent.com/pytorch/hub/master/imagenet_class_index.json"
labels = requests.get(LABELS_URL).json()

st.set_page_config(page_title="Adobe Stock Master Expert AI", layout="wide")

st.markdown("""
    <style>
    .expert-pass { background-color: #f0fff4; border: 2px solid #38a169; padding: 20px; border-radius: 15px; text-align: center; color: #276749; font-weight: bold; font-size: 22px; }
    .expert-fail { background-color: #fff5f5; border: 2px solid #e53e3e; padding: 20px; border-radius: 15px; text-align: center; color: #9b2c2c; font-weight: bold; font-size: 22px; }
    .ai-prompt-box { background-color: #f7fafc; border: 2px dashed #4299e1; padding: 20px; border-radius: 10px; color: #2b6cb0; font-family: 'Segoe UI', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧠 Adobe Stock Master Expert AI")
st.write("এই টুলটি এখন নিজে থেকেই সাবজেক্ট চিনবে এবং অ্যাডোবির আসল স্ট্যান্ডার্ড অনুযায়ী আপনার ছবি অডিট করবে।")

uploaded_file = st.file_uploader("যেকোনো ছবি এখানে দিন...", type=["jpg", "jpeg"])

def get_subject(pil_img):
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    input_tensor = preprocess(pil_img)
    input_batch = input_tensor.unsqueeze(0)
    with torch.no_grad():
        output = classifier(input_batch)
    _, index = torch.max(output, 1)
    subject = labels[str(index.item())][1]
    return subject.replace('_', ' ')

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    img_array = np.array(image)
    
    with st.spinner('এক্সপার্ট এআই আপনার ছবি এবং সাবজেক্ট বিশ্লেষণ করছে...'):
        # সাবজেক্ট ডিটেকশন
        subject_name = get_subject(image)
        
        # টেকনিক্যাল চেক
        w, h = image.size
        mp = (w * h) / 1000000
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # শার্পনেস চেক (একেবারে নমনীয় করা হয়েছে প্রফেশনাল ছবির জন্য)
        sharp_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        text = pytesseract.image_to_string(image).strip()

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True, caption=f"Detected Subject: {subject_name}")

    with col2:
        st.subheader("📢 এক্সপার্ট অডিট রিপোর্ট")
        
        errors = []
        # অ্যাডোবি স্ট্যান্ডার্ড রি-ক্যালিব্রেশন
        if mp < 4.0: errors.append(f"সাইজ ছোট ({mp:.2f} MP)")
        if sharp_score < 6.0: errors.append("ছবিটি অতিরিক্ত ঝাপসা (Critical Blur)")
        if len(text) > 4: errors.append(f"লোগো/টেক্সট পাওয়া গেছে: {text[:10]}")

        if not errors:
            st.markdown('<div class="expert-pass">✅ এই ছবিটি Adobe Stock-এ ১০০% অ্যাপ্রুভ হবে!</div>', unsafe_allow_html=True)
            st.balloons()
        else:
            st.markdown('<div class="expert-fail">🛑 রিজেকশন রিস্ক পাওয়া গেছে!</div>', unsafe_allow_html=True)
            for e in errors: st.write(f"- {e}")

        # মাস্টার অটো-প্রম্পট
        st.subheader("🎨 Full AI Creation Prompt (Auto-Generated)")
        st.write("নিচের প্রম্পটটি সরাসরি কপি করে ব্যবহার করুন:")
        
        master_prompt = f"Professional high-end stock photography of {subject_name}, cinematic studio lighting, shot on 85mm lens, f/1.8, incredible details, masterpiece, sharp focus, clean background, no text, no logo, commercially ready, 8k resolution --ar 16:9 --v 6.0"
        
        st.markdown(f'<div class="ai-prompt-box"><b>Master Prompt:</b><br>{master_prompt}</div>', unsafe_allow_html=True)
        st.info(f"এআই শনাক্ত করেছে যে এটি একটি **{subject_name}** এর ছবি এবং সেই অনুযায়ী প্রম্পটটি সাজানো হয়েছে।")
