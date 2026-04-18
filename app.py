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
    .report-row { border-bottom: 1px solid #eee; padding: 10px 0; display: flex; align-items: center; }
    .status-pass { color: #155724; background-color: #d4edda; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; }
    .status-risk { color: #856404; background-color: #fff3cd; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; }
    .prompt-text { font-family: monospace; font-size: 12px; color: #555; background: #f9f9f9; padding: 5px; border: 1px dashed #ccc; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Bulk Adobe Stock Auditor (Visual Mode)")
st.write("একাধিক ছবি আপলোড করুন। নামের পাশে ছবির থাম্বনেইল সহ রিপোর্ট দেখুন।")

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
    st.subheader(f"📊 {len(uploaded_files)} টি ছবি স্ক্যান করা হচ্ছে")
    progress_bar = st.progress(0)
    
    for idx, uploaded_file in enumerate(uploaded_files):
        # ছবি লোড করা
        image = Image.open(uploaded_file).convert('RGB')
        img_array = np.array(image)
        
        # অডিট করা
        score, audit_logs = deep_audit(img_array, image)
        
        # থাম্বনেইল ডিসপ্লে করার জন্য কলাম
        col1, col2, col3, col4 = st.columns([1, 3, 1.5, 1])
        
        with col1:
            # ছোট থাম্বনেইল তৈরি
            image.thumbnail((100, 100))
            st.image(image, use_column_width=False)
            
        with col2:
            st.write(f"**{uploaded_file.name}**")
            if audit_logs:
                st.caption(", ".join(audit_logs))
            else:
                st.caption("কোনো টেকনিক্যাল ত্রুটি নেই")
                
        with col3:
            if score >= 85:
                st.markdown('<span class="status-pass">✅ ACCEPTED</span>', unsafe_allow_html=True)
            elif score >= 55:
                st.markdown('<span class="status-risk">⚠️ RISKY</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="status-fail">🛑 REJECTED</span>', unsafe_allow_html=True)
            st.write(f"Score: **{score}%**")

        with col4:
            # বিস্তারিত এবং প্রম্পট দেখার জন্য ছোট বাটন বা পপওভার
            with st.popover("AI Prompt"):
                st.write("**Master AI Prompt:**")
                st.markdown(f'<div class="prompt-text">Professional stock photography, masterpiece, sharp focus, 8k, no text, no logo --v 6.0</div>', unsafe_allow_html=True)

        st.divider() # প্রতিটি ছবির পর একটি দাগ
        progress_bar.progress((idx + 1) / len(uploaded_files))

    st.success(f"মোট {len(uploaded_files)} টি ছবির অডিট সম্পন্ন হয়েছে।")
