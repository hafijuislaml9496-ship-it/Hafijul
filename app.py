import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import os

# কনফিগারেশন
st.set_page_config(page_title="Adobe Stock Master Intelligence", layout="wide")

st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .status-risk { color: #856404; background-color: #fff3cd; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Adobe Stock Expert Auditor (Smart Context Mode)")
st.write("এই টুলটি এখন নিজে থেকেই বুঝবে ছবিতে আইকন আছে কি না এবং সেই অনুযায়ী নিখুঁত অডিট করবে।")

uploaded_files = st.file_uploader("আপনার ছবিগুলো আপলোড করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

def analyze_smart_graphics(img_array):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # ১. প্রথমে দেখি ছবিতে কি কোনো উজ্জ্বল ডিজিটাল এলিমেন্ট (Icons/UI) আছে?
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # যদি অনেকগুলো ছোট ছোট উজ্জ্বল অবজেক্ট থাকে, তবে ধরে নেব আইকন আছে
    has_icons = len(contours) > 5
    messy_graphics = False
    
    if has_icons:
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 10:
                perimeter = cv2.arcLength(cnt, True)
                if perimeter == 0: continue
                circularity = 4 * np.pi * (area / (perimeter * perimeter))
                # যদি শেপটি আঁকাবাঁকা হয় (এআই জেনারেটেড ভাঙা আইকন)
                if circularity < 0.4:
                    messy_graphics = True
                    break
    
    return has_icons, messy_graphics

def analyze_image(img_array, pil_img, filename):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs, score = [], 100
    
    # ১. স্মার্ট গ্রাফিক্স চেক
    has_icons, is_messy = analyze_smart_graphics(img_array)
    if has_icons:
        if is_messy:
            score -= 45
            logs.append("❌ Deformed UI/Icons: ভাসমান আইকনগুলো ভাঙাচোরা বা অগোছালো।")
        else:
            logs.append("✅ Graphic Integrity: আইকনগুলো নিখুঁত।")

    # ২. রেজোলিউশন চেক
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    if mp < 4.0:
        score -= 40
        logs.append(f"❌ Low Res ({mp:.2f}MP)")

    # ৩. শার্পনেস এবং ফোকাস (প্রফেশনাল স্ট্যান্ডার্ড)
    gh, gw = h//6, w//6
    peak_sharp = max([cv2.Laplacian(gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw], cv2.CV_64F).var() for i in range(6) for j in range(6)])
    if peak_sharp < 45:
        score -= 30
        logs.append("❌ Soft Focus: ছবিটি যথেষ্ট শার্প নয়।")

    # ৪. লোগো ও টেক্সট ডিটেকশন
    try:
        text = pytesseract.image_to_string(pil_img).strip()
        if len(text) > 3:
            score -= 50
            logs.append(f"❌ IP Claim: লোগো বা টেক্সট পাওয়া গেছে।")
    except: pass

    # ৫. সাবজেক্ট (ফাইলের নাম থেকে)
    subject = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')[:20]
    
    return score, logs, subject

if uploaded_files:
    for idx, uploaded_file in enumerate(uploaded_files):
        image = Image.open(uploaded_file).convert('RGB')
        img_array = np.array(image)
        score, logs, subject = analyze_image(img_array, image, uploaded_file.name)
        
        col1, col2, col3, col4 = st.columns([1, 3, 1.5, 1.2])
        with col1:
            thumb = image.copy(); thumb.thumbnail((120, 120))
            st.image(thumb)
        with col2:
            st.write(f"**{uploaded_file.name}**")
            st.caption(f"Context: {subject.title()}")
            for log in logs: st.write(log)
            if not logs: st.write("✅ কোয়ালিটি পারফেক্ট।")
        with col3:
            if score >= 80: st.markdown('<span class="status-pass">ACCEPTED</span>', unsafe_allow_html=True)
            elif score >= 50: st.markdown('<span class="status-risk">RISKY</span>', unsafe_allow_html=True)
            else: st.markdown('<span class="status-fail">REJECTED</span>', unsafe_allow_html=True)
            st.write(f"Score: **{score}%**")
        with col4:
            with st.popover("Master Prompt"):
                q_fix = "perfectly symmetrical geometric icons, clean vector lines, sharp focus" if "UI/Icons" in str(logs) else "ultra-sharp focus, professional lighting"
                m_prompt = f"Professional stock photography of {subject}, {q_fix}, 8k, commercially ready, no logo --v 6.0"
                st.code(m_prompt, language="text")
        st.divider()
