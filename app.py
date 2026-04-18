import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract

# কনফিগারেশন
st.set_page_config(page_title="Bulk Adobe Stock Auditor", layout="wide")

st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
    .status-risk { color: #856404; background-color: #fff3cd; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
    .prompt-box { background-color: #f8f9fa; border: 1px dashed #007bff; padding: 10px; font-family: monospace; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Bulk Adobe Stock Auditor (Strict Mode)")
st.write("একসাথে একাধিক ছবি আপলোড করুন। প্রতিটি ছবি অ্যাডোবি স্ট্যান্ডার্ড অনুযায়ী নিখুঁতভাবে বিশ্লেষণ হবে।")

uploaded_files = st.file_uploader("আপনার ছবিগুলো একসাথে সিলেক্ট করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

def deep_audit(img_array, pil_img):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs = []
    score = 100
    
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    if mp < 4.0:
        score -= 40
        logs.append(f"❌ Low Res ({mp:.2f}MP)")

    gh, gw = h//6, w//6
    peak_sharp = max([cv2.Laplacian(gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw], cv2.CV_64F).var() for i in range(6) for j in range(6)])
    if peak_sharp < 42:
        score -= 35
        logs.append("❌ Soft Focus")
    elif peak_sharp < 65:
        score -= 15
        logs.append("⚠️ Slightly Soft")

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

if uploaded_files:
    st.subheader(f"📊 {len(uploaded_files)} টি ছবি বিশ্লেষণ করা হচ্ছে...")
    pass_count = 0
    progress_bar = st.progress(0)
    
    for idx, uploaded_file in enumerate(uploaded_files):
        image = Image.open(uploaded_file).convert('RGB')
        img_array = np.array(image)
        score, audit_logs = deep_audit(img_array, image)
        
        with st.expander(f"📷 {uploaded_file.name} (Score: {score}%)"):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(image, use_column_width=True)
            with col2:
                if score >= 85:
                    st.markdown('<span class="status-pass">✅ ACCEPTED</span>', unsafe_allow_html=True)
                    pass_count += 1
                elif score >= 55:
                    st.markdown('<span class="status-risk">⚠️ RISKY</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-fail">🛑 REJECTED</span>', unsafe_allow_html=True)
                
                for log in audit_logs: st.write(log)
                st.markdown(f'<div class="prompt-box">AI Prompt: Professional commercial stock photography, masterpiece, sharp focus, 8k, zero noise, no text, no logo --v 6.0</div>', unsafe_allow_html=True)

        progress_bar.progress((idx + 1) / len(uploaded_files))

    st.divider()
    st.metric("মোট পাশ করেছে", f"{pass_count} / {len(uploaded_files)}")
    if pass_count == len(uploaded_files): st.balloons()
