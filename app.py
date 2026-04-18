import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import os

# পেজ কনফিগারেশন
st.set_page_config(page_title="Adobe Contributor Expert", layout="wide")

st.markdown("""
    <style>
    .pass-tag { color: #155724; background-color: #d4edda; padding: 4px 10px; border-radius: 15px; font-weight: bold; font-size: 11px; }
    .fail-tag { color: #721c24; background-color: #f8d7da; padding: 4px 10px; border-radius: 15px; font-weight: bold; font-size: 11px; }
    .log-text { font-size: 12px; color: #444; margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

def adobe_standard_audit(img_array, pil_img, filename):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs = []
    score = 100
    
    # ১. রেজোলিউশন (হার্ড রুল: অন্তত ৪ এমপি)
    mp = (h * w) / 1,000,000
    if mp < 4.0:
        score -= 40
        logs.append(f"❌ রেজোলিউশন কম ({mp:.2f} MP)। ৪ মেগাপিক্সেল লাগবে।")

    # ২. ফোকাল শার্পনেস (Peak Sharpness Logic)
    # আমরা পুরো ছবি দেখব না, শুধু দেখব ছবির কোনো একটি অংশে কি প্রফেশনাল শার্পনেস আছে? (Intentional Blur সাপোর্ট)
    gh, gw = h//8, w//8
    sections = [cv2.Laplacian(gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw], cv2.CV_64F).var() for i in range(8) for j in range(8)]
    peak_sharp = max(sections)
    
    if peak_sharp < 15.0: # যদি ছবির কোথাও ফোকাস না থাকে
        score -= 35
        logs.append("❌ Out of Focus: ছবির কোথাও কোনো শার্প সাবজেক্ট পাওয়া যায়নি।")
    elif peak_sharp < 30.0:
        score -= 10
        logs.append("⚠️ Soft Focus: সাবজেক্টের শার্পনেস কিছুটা কম।")

    # ৩. এক্সপোজার এবং লাইটিং (Highlights Clipping)
    over_exposed = np.sum(gray > 250) / (h * w)
    if over_exposed > 0.06:
        score -= 20
        logs.append("❌ Lighting Issue: ছবি অতিরিক্ত উজ্জ্বল (Blown highlights)।")

    # ৪. আর্টিফ্যাক্টস এবং এআই টেক্সচার (Waxy skin check)
    try:
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        if noise > 7.5:
            score -= 15
            logs.append("⚠️ Artifacts/Noise: ছবিতে ডিজিটাল ত্রুটি বা দানা বেশি।")
    except: pass

    # ৫. ব্র্যান্ড লোগো এবং টেক্সট (অ্যাডোবির সবচেয়ে কড়া নিয়ম)
    try:
        text = pytesseract.image_to_string(pil_img).strip()
        if len(text) > 2:
            score -= 60
            logs.append(f"❌ Intellectual Property: ছবিতে লোগো বা টেক্সট পাওয়া গেছে।")
    except: pass

    subject = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')[:20]
    return score, logs, subject, peak_sharp

# মেইন অ্যাপ ইন্টারফেস
st.title("🛡️ Adobe Stock Intelligence Auditor")
st.write("এই টুলটি এখন অ্যাডোবির 'টেকনিক্যাল কোয়ালিটি' এবং 'আর্টিস্টিক ব্লার' দুটোই বুঝতে পারে।")

files = st.file_uploader("আপনার ছবিগুলো আপলোড করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

if files:
    for uploaded_file in files:
        try:
            image = Image.open(uploaded_file).convert('RGB')
            img_array = np.array(image)
            score, audit_logs, subj, s_score = adobe_standard_audit(img_array, image, uploaded_file.name)
            
            col1, col2, col3, col4 = st.columns([1, 3, 1.5, 1.2])
            with col1:
                thumb = image.copy(); thumb.thumbnail((120, 120)); st.image(thumb)
            with col2:
                st.write(f"**{uploaded_file.name}**")
                st.caption(f"Context: {subj.title()}")
                if not audit_logs: st.markdown('<p style="color:green; font-size:12px;">✅ কোয়ালিটি নিখুঁত।</p>', unsafe_allow_html=True)
                for log in audit_logs: st.markdown(f'<p class="log-text">{log}</p>', unsafe_allow_html=True)
            with col3:
                if score >= 75: st.markdown('<span class="pass-tag">✅ ACCEPTED</span>', unsafe_allow_html=True)
                else: st.markdown('<span class="fail-tag">🛑 REJECTED</span>', unsafe_allow_html=True)
                st.write(f"S-Score: {s_score:.1f}")
            with col4:
                with st.popover("Master Prompt"):
                    q_fix = "ultra-high resolution photography, sharp focus on subject, commercial grade texture, cinematic lighting"
                    st.code(f"Professional photography of {subj}, {q_fix}, zero artifacts, 8k --ar 16:9 --v 6.0", language="text")
            st.divider()
        except Exception as e:
            st.error(f"Error: {e}")
