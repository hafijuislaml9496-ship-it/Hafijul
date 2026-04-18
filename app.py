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
def load_model():
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    model.eval()
    return model

classifier = load_model()

# ২. ডাইনামিক প্রম্পট ফাংশন
def generate_custom_prompt(image, score, logs):
    # সাবজেক্ট ডিটেকশন
    preprocess = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    input_tensor = preprocess(image).unsqueeze(0)
    with torch.no_grad():
        output = classifier(input_tensor)
    _, index = torch.max(output, 1)
    
    # সিম্পল সাবজেক্ট আইডেন্টিফায়ার (এখানে জাস্ট ডিফল্ট কিছু ক্যাটাগরি)
    subj = "High-quality subject"
    if index.item() < 400: subj = "Professional Portrait"
    elif 400 <= index.item() < 600: subj = "Commercial Object"
    else: subj = "Scenic Landscape/Architecture"

    # কোয়ালিটি অনুযায়ী প্রম্পট টিউনিং
    quality_tags = "razor sharp focus, 8k resolution, masterpiece, cinematic lighting"
    if "❌ Soft Focus" in str(logs): quality_tags += ", extra detailed textures, extreme clarity"
    if "❌ High Noise" in str(logs): quality_tags += ", zero noise, clean ISO"
    
    prompt = f"Professional stock photography of {subj}, {quality_tags}, photorealistic, no text, no logo, commercially ready, shot on Sony A7R IV --ar 16:9 --v 6.0"
    return prompt

# ৩. অডিট লজিক
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

# ৪. মেইন অ্যাপ ইন্টারফেস
st.set_page_config(page_title="Bulk AI Stock Auditor", layout="wide")
st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 5px 12px; border-radius: 20px; font-weight: bold; }
    .status-risk { color: #856404; background-color: #fff3cd; padding: 5px 12px; border-radius: 20px; font-weight: bold; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 5px 12px; border-radius: 20px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Bulk Adobe Stock Auditor (Intelligent Mode)")
uploaded_files = st.file_uploader("আপনার ছবিগুলো আপলোড করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    progress_bar = st.progress(0)
    for idx, uploaded_file in enumerate(uploaded_files):
        image = Image.open(uploaded_file).convert('RGB')
        img_array = np.array(image)
        score, logs = deep_audit(img_array, image)
        unique_prompt = generate_custom_prompt(image, score, logs)
        
        col1, col2, col3, col4 = st.columns([1, 3, 1.5, 1])
        with col1:
            thumb = image.copy()
            thumb.thumbnail((100, 100))
            st.image(thumb)
        with col2:
            st.write(f"**{uploaded_file.name}**")
            st.caption(", ".join(logs) if logs else "টেকনিক্যাল কোয়ালিটি পারফেক্ট")
        with col3:
            if score >= 85: st.markdown('<span class="status-pass">✅ ACCEPTED</span>', unsafe_allow_html=True)
            elif score >= 55: st.markdown('<span class="status-risk">⚠️ RISKY</span>', unsafe_allow_html=True)
            else: st.markdown('<span class="status-fail">🛑 REJECTED</span>', unsafe_allow_html=True)
            st.write(f"Score: **{score}%**")
        with col4:
            with st.popover("AI Prompt"):
                st.write("**Unique Master Prompt:**")
                st.code(unique_prompt, language="text") # st.code এ অটোমেটিক কপি বাটন থাকে
        st.divider()
        progress_bar.progress((idx + 1) / len(uploaded_files))
    st.success("অডিট সম্পন্ন হয়েছে!")
