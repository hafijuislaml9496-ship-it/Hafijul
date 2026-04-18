import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import os

# পেজ সেটআপ
st.set_page_config(page_title="Adobe Stock Pro Auditor", layout="wide")

st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .status-risk { color: #856404; background-color: #fff3cd; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Adobe Stock Expert Auditor (Graphics Integrity Mode)")
st.write("এই টুলটি এখন ছবির আইকন এবং গ্রাফিক্সের খুঁত (Deformed Shapes) শনাক্ত করতে সক্ষম।")

uploaded_files = st.file_uploader("আপনার ছবিগুলো আপলোড করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

def analyze_graphics_integrity(img_array):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    # এজ ডিটেকশন দিয়ে আইকনগুলোর গঠন দেখা
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    messy_count = 0
    for cnt in contours:
        perimeter = cv2.arcLength(cnt, True)
        area = cv2.contourArea(cnt)
        if area > 10:
            # যদি শেপ খুব বেশি জটিল বা আঁকাবাঁকা হয় (নন-স্মুথ আইকন)
            circularity = 4 * np.pi * (area / (perimeter * perimeter))
            if circularity < 0.3: # এটি নির্দেশ করে শেপটি ভাঙাচোরা বা অগোছালো
                messy_count += 1
    return messy_count

def analyze_image(img_array, pil_img, filename):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs, score = [], 100
    
    # ১. আইকন ইন্টিগ্রিটি চেক (আসল সাবজেক্টের ভুল ধরা)
    messy_shapes = analyze_graphics_integrity(img_array)
    if messy_shapes > 25:
        score -= 40
        logs.append(f"❌ Deformed Graphics: আইকনগুলো ভাঙাচোরা বা অগোছালো।")

    # ২. শার্পনেস এবং ফোকাস
    gh, gw = h//6, w//6
    peak_sharp = max([cv2.Laplacian(gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw], cv2.CV_64F).var() for i in range(6) for j in range(6)])
    if peak_sharp < 45:
        score -= 30
        logs.append("❌ Soft Focus: গ্রাফিক্সগুলো ঝাপসা।")

    # ৩. টেক্সট এবং লোগো
    try:
        text = pytesseract.image_to_string(pil_img).strip()
        if len(text) > 3:
            score -= 50
            logs.append(f"❌ Logo/Text Detected: '{text[:10]}'")
    except: pass
    
    # ৪. রেজোলিউশন
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    if mp < 4.0:
        score -= 40
        logs.append(f"❌ Low Res ({mp:.2f}MP)")

    # সাবজেক্টের নাম (ফাইলের নাম থেকে)
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
            st.caption(f"Category: {subject.title()}")
            if logs:
                for log in logs: st.write(log)
            else:
                st.write("✅ কোয়ালিটি অ্যাডোবি স্ট্যান্ডার্ড অনুযায়ী নিখুঁত।")
        with col3:
            if score >= 80: st.markdown('<span class="status-pass">ACCEPTED</span>', unsafe_allow_html=True)
            elif score >= 50: st.markdown('<span class="status-risk">RISKY</span>', unsafe_allow_html=True)
            else: st.markdown('<span class="status-fail">REJECTED</span>', unsafe_allow_html=True)
            st.write(f"Score: **{score}%**")
        with col4:
            with st.popover("Master Prompt"):
                q_fix = "ultra-sharp vector icons, perfectly symmetrical shapes, clean geometric lines"
                m_prompt = f"Professional commercial stock photography of {subject}, {q_fix}, photorealistic, no text, no logo, commercially ready --ar 16:9 --v 6.0"
                st.code(m_prompt, language="text")
        st.divider()
