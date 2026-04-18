import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import os

# ১. পেজ কনফিগারেশন
st.set_page_config(page_title="Extreme Adobe Auditor", layout="wide")

st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 11px; border: 1px solid #28a745; }
    .status-risk { color: #856404; background-color: #fff3cd; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 11px; border: 1px solid #ffc107; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 11px; border: 1px solid #dc3545; }
    .log-text { font-size: 12px; margin-bottom: 2px; color: #d32f2f; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# ২. এক্সট্রিম অডিট ইঞ্জিন
def extreme_audit(img_array, pil_img, filename):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs = []
    score = 100
    
    # --- মেগাপিক্সেল চেক ---
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    if mp < 4.0:
        score -= 50
        logs.append(f"❌ Low MP: {mp:.2f} (Need 4MP+)")

    # --- এক্সট্রিম শার্পনেস অডিট (১০০% জুম লেভেল) ---
    gh, gw = h//10, w//10
    peak_sharp = max([cv2.Laplacian(gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw], cv2.CV_64F).var() for i in range(10) for j in range(10)])
    
    # অ্যাডোবি এক্সট্রিম লিমিট: ৭৫ এর নিচে মানেই রিস্ক, ৪৫ এর নিচে মানে রিজেক্ট
    if peak_sharp < 45.0:
        score -= 40
        logs.append(f"❌ Soft Focus: মূল অংশটি ঝাপসা ({peak_sharp:.1f})")
    elif peak_sharp < 75.0:
        score -= 15
        logs.append(f"⚠️ Focus Risk: কিছুটা সফট মনে হচ্ছে ({peak_sharp:.1f})")

    # --- এআই আর্টিফ্যাক্টস এবং নয়েজ ---
    try:
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        if noise > 5.5: # অনেক বেশি কঠোর করা হয়েছে
            score -= 20
            logs.append(f"❌ Technical Artifacts: হাই নয়েজ বা এআই ত্রুটি।")
    except: pass

    # --- লোগো এবং টেক্সট স্ক্যান ---
    try:
        text = pytesseract.image_to_string(pil_img).strip()
        if len(text) > 2:
            score -= 60
            logs.append(f"❌ IP Violation: লোগো বা টেক্সট ডিটেক্ট হয়েছে।")
    except: pass

    # সাবজেক্ট নাম
    subject = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')[:20]
    
    return score, logs, subject, peak_sharp

# ৩. মেইন অ্যাপ
st.title("🛡️ Adobe Stock Extreme Expert Auditor")
st.write("বাল্ক অডিট। এটি এখন অত্যন্ত কঠোরভাবে প্রতিটি পিক্সেল এবং এআই আর্টিফ্যাক্ট চেক করবে।")

uploaded_files = st.file_uploader("ছবিগুলো ড্রপ করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            image = Image.open(uploaded_file).convert('RGB')
            img_array = np.array(image)
            score, audit_logs, subject_name, s_score = extreme_audit(img_array, image, uploaded_file.name)
            
            col1, col2, col3, col4 = st.columns([1, 3, 1.5, 1.2])
            with col1:
                thumb = image.copy(); thumb.thumbnail((120, 120))
                st.image(thumb)
            with col2:
                st.write(f"**{uploaded_file.name}**")
                st.caption(f"Sub: {subject_name.title()}")
                if not audit_logs: st.markdown('<p style="color:green; font-size:12px;">✅ Quality Perfect</p>', unsafe_allow_html=True)
                for log in audit_logs: st.markdown(f'<p class="log-text">{log}</p>', unsafe_allow_html=True)
            with col3:
                if score >= 85: st.markdown('<span class="status-pass">ACCEPTED</span>', unsafe_allow_html=True)
                elif score >= 60: st.markdown('<span class="status-risk">RISKY</span>', unsafe_allow_html=True)
                else: st.markdown('<span class="status-fail">REJECTED</span>', unsafe_allow_html=True)
                st.write(f"S-Score: {s_score:.1f}")
            with col4:
                with st.popover("Master Prompt"):
                    st.write("**Fix & Re-Create Prompt:**")
                    q_fix = "ultra-sharp 8k resolution, cinematic lighting, zero artifacts"
                    if score < 85: q_fix += ", razor sharp focus, photorealistic textures"
                    st.code(f"Professional photography of {subject_name}, {q_fix}, commercially ready --v 6.0", language="text")
            st.divider()
        except Exception as e:
            st.error(f"Error: {e}")
