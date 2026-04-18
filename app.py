import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import torch
from torchvision import models, transforms
import requests

# ১. এআই মডেল এবং ১০০০টি বস্তুর নামের লিস্ট (Labels) লোড করা
@st.cache_resource
def load_ai_expert():
    # সাবজেক্ট চেনার মডেল
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    model.eval()
    
    # ১০০০টি বস্তুর নাম (ImageNet Labels)
    LABELS_URL = "https://raw.githubusercontent.com/pytorch/hub/master/imagenet_class_index.json"
    labels = requests.get(LABELS_URL).json()
    return model, labels

classifier, labels = load_ai_expert()

# ২. ইউনিক প্রম্পট তৈরির ফাংশন (ছবির আসল সাবজেক্ট দিয়ে)
def get_unique_prompt(image, logs):
    preprocess = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    input_tensor = preprocess(image).unsqueeze(0)
    with torch.no_grad():
        output = classifier(input_tensor)
    _, index = torch.max(output, 1)
    
    # ছবির আসল সাবজেক্টের নাম বের করা
    detected_name = labels[str(index.item())][1].replace('_', ' ')
    
    # প্রম্পট সাজানো
    quality_tags = "razor sharp focus, highly detailed, 8k resolution, cinematic lighting"
    if "❌ Soft Focus" in str(logs): quality_tags += ", extreme clarity, macro details"
    
    final_prompt = f"Professional stock photography of {detected_name.title()}, {quality_tags}, photorealistic masterpiece, clean background, no text, no logo, commercially ready, shot on Sony A7R IV --ar 16:9 --v 6.0"
    return final_prompt, detected_name

# ৩. টেকনিক্যাল অডিট লজিক (Strict Mode)
def deep_audit(img_array, pil_img):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs, score = [], 100
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    if mp < 4.0:
        score -= 40
        logs.append(f"❌ Low Res ({mp:.2f}MP)")
    gh, gw = h//6, w//6
    peak_sharp = max([cv2.Laplacian(gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw], cv2.CV_64F).var() for i in range(6) for j in range(6)])
    if peak_sharp < 42:
        score -= 35
        logs.append("❌ Soft Focus")
    try:
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        if noise > 6.0:
            score -= 20
            logs.append("❌ High Noise")
    except: pass
    text = pytesseract.image_to_string(pil_img).strip()
    if len(text) > 3:
        score -= 60
        logs.append("❌ Logo/Text Detected")
    return score, logs

# ৪. ইন্টারফেস ডিজাইন
st.set_page_config(page_title="Bulk Smart Auditor", layout="wide")
st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .status-risk { color: #856404; background-color: #fff3cd; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Bulk Adobe Stock Smart Auditor")
uploaded_files = st.file_uploader("ছবিগুলো আপলোড করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        image = Image.open(uploaded_file).convert('RGB')
        img_array = np.array(image)
        
        # অডিট এবং ইউনিক প্রম্পট জেনারেশন
        score, logs = deep_audit(img_array, image)
        unique_prompt, subject_name = get_unique_prompt(image, logs)
        
        col1, col2, col3, col4 = st.columns([1, 3, 1.5, 1])
        with col1:
            thumb = image.copy()
            thumb.thumbnail((120, 120))
            st.image(thumb)
        with col2:
            st.write(f"**{uploaded_file.name}**")
            st.caption(f"Detected Subject: {subject_name.title()}")
            st.write(", ".join(logs) if logs else "✅ টেকনিক্যাল কোয়ালিটি পারফেক্ট")
        with col3:
            if score >= 85: st.markdown('<span class="status-pass">ACCEPTED</span>', unsafe_allow_html=True)
            elif score >= 55: st.markdown('<span class="status-risk">RISKY</span>', unsafe_allow_html=True)
            else: st.markdown('<span class="status-fail">REJECTED</span>', unsafe_allow_html=True)
            st.write(f"Score: **{score}%**")
        with col4:
            with st.popover("AI Prompt"):
                st.write(f"**Unique Prompt for {subject_name.title()}:**")
                st.code(unique_prompt, language="text")
        st.divider()
