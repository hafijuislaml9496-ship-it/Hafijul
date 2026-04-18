import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import os

# পেজ সেটআপ
st.set_page_config(page_title="Adobe Stock Auditor Pro", layout="wide")

st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .prompt-box { background-color: #f8f9fa; border: 1px dashed #007bff; padding: 10px; font-family: monospace; font-size: 13px; color: #333; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Adobe Stock Master Auditor (Stable V4)")
st.write("বাল্ক ফটো অডিট এবং অটোমেটিক সাবজেক্ট-বেজড প্রম্পট জেনারেটর।")

uploaded_files = st.file_uploader("আপনার ছবিগুলো একসাথে এখানে দিন...", type=["jpg", "jpeg"], accept_multiple_files=True)

def analyze_image(img_array, pil_img, filename):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs, score = [], 100
    
    # ১. মেগাপিক্সেল
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    if mp < 4.0:
        score -= 40
        logs.append(f"❌ Low Res ({mp:.2f}MP)")
    
    # ২. স্মার্ট শার্পনেস (Peak Analysis)
    gh, gw = h//6, w//6
    peak_sharp = max([cv2.Laplacian(gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw], cv2.CV_64F).var() for i in range(6) for j in range(6)])
    if peak_sharp < 42:
        score -= 35
        logs.append("❌ Soft Focus")
    
    # ৩. নয়েজ ডিটেকশন
    try:
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        if noise > 6.0:
            score -= 20
            logs.append("❌ High Noise")
    except: noise = 0
    
    # ৪. টেক্সট এবং সাবজেক্ট ডিটেকশন
    text = pytesseract.image_to_string(pil_img).strip()
    if len(text) > 3:
        score -= 60
        logs.append("❌ Logo Detected")
    
    # ৫. স্মার্ট সাবজেক্ট এক্সট্রাকশন (ফাইলের নাম থেকে)
    subject_name = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
    # যদি নাম খুব বড় হয় বা হিজিবিজি হয় তবে ছোট করা
    if len(subject_name) > 20: subject_name = subject_name[:20]
    
    return score, logs, subject_name, peak_sharp

if uploaded_files:
    st.subheader(f"📊 {len(uploaded_files)} টি ছবি বিশ্লেষণ করা হচ্ছে...")
    progress_bar = st.progress(0)
    
    for idx, uploaded_file in enumerate(uploaded_files):
        try:
            image = Image.open(uploaded_file).convert('RGB')
            img_array = np.array(image)
            
            score, logs, subject, sharpness = analyze_image(img_array, image, uploaded_file.name)
            
            col1, col2, col3, col4 = st.columns([1, 3, 1.5, 1.2])
            with col1:
                thumb = image.copy()
                thumb.thumbnail((120, 120))
                st.image(thumb)
            with col2:
                st.write(f"**{uploaded_file.name}**")
                st.caption(f"Detected Subject: {subject}")
                st.write(", ".join(logs) if logs else "✅ টেকনিক্যাল কোয়ালিটি পারফেক্ট")
            with col3:
                if score >= 85: st.markdown('<span class="status-pass">ACCEPTED</span>', unsafe_allow_html=True)
                else: st.markdown('<span class="status-fail">REJECTED</span>', unsafe_allow_html=True)
                st.write(f"Score: **{score}%**")
            with col4:
                with st.popover("Master Prompt"):
                    st.write(f"**Unique Prompt for {subject}:**")
                    q_tags = "razor sharp focus, 8k, cinematic lighting, masterpiece"
                    if score < 85: q_tags += ", extreme clarity, ultra-clean textures"
                    
                    m_prompt = f"Professional stock photography of {subject}, {q_tags}, photorealistic, no text, no logo, commercially ready --v 6.0"
                    st.code(m_prompt, language="text")
            st.divider()
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")
            
        progress_bar.progress((idx + 1) / len(uploaded_files))
