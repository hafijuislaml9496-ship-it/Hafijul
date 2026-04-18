import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import os

# পেজ কনফিগারেশন
st.set_page_config(page_title="Adobe Contributor Master Tool", layout="wide")

st.markdown("""
    <style>
    .pass-tag { color: #155724; background-color: #d4edda; padding: 4px 10px; border-radius: 15px; font-weight: bold; font-size: 11px; }
    .fail-tag { color: #721c24; background-color: #f8d7da; padding: 4px 10px; border-radius: 15px; font-weight: bold; font-size: 11px; }
    .log-text { font-size: 12px; color: #d32f2f; margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

def run_adobe_audit(img_array, pil_img, filename):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs = []
    score = 100
    
    # ১. রেজোলিউশন চেক (কমা ছাড়া সংখ্যা ব্যবহার করা হয়েছে যাতে এরর না হয়)
    mp = (h * w) / 1000000.0
    if mp < 4.0:
        score -= 50
        logs.append(f"❌ রেজোলিউশন অত্যন্ত কম ({mp:.2f} MP)। ৪ এমপি লাগবে।")

    # ২. ফোকাল শার্পনেস (Bokeh/Focal Point Support)
    gh, gw = h//8, w//8
    max_sharp = 0
    for i in range(8):
        for j in range(8):
            section = gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw]
            if section.size > 0:
                s = cv2.Laplacian(section, cv2.CV_64F).var()
                if s > max_sharp: max_sharp = s
    
    if max_sharp < 12.0:
        score -= 40
        logs.append(f"❌ Out of Focus: ছবির কোনো অংশই শার্প নয়।")
    elif max_sharp < 28.0:
        score -= 10
        logs.append("⚠️ Soft Focus: সাবজেক্ট সামান্য ঝাপসা।")

    # ৩. এক্সপোজার (Lighting Issue)
    over_exposed = np.sum(gray > 250) / (h * w)
    if over_exposed > 0.05:
        score -= 20
        logs.append("❌ Lighting: হাইলাইট পুড়ে গেছে (Blown highlights)।")

    # ৪. আর্টিফ্যাক্টস এবং নয়েজ
    try:
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        if noise > 7.0:
            score -= 15
            logs.append("⚠️ Technical Artifacts: নয়েজ বা দানা বেশি।")
    except:
        noise = 0

    # ৫. লোগো এবং টেক্সট (IP Violation)
    try:
        text = pytesseract.image_to_string(pil_img).strip()
        if len(text) > 3:
            score -= 60
            logs.append(f"❌ Logo/Text: ছবিতে ব্র্যান্ডিং পাওয়া গেছে।")
    except:
        pass

    subject = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')[:20]
    return score, logs, subject, max_sharp

# মেইন ইউজার ইন্টারফেস
st.title("🛡️ Adobe Stock Expert Auditor (Stable)")
st.write("বাল্ক মোডে ছবি অডিট করুন। এটি এখন বোকেহ এবং মোশন ব্লার শনাক্ত করতে পারে।")

uploaded_files = st.file_uploader("আপনার ছবিগুলো ড্রপ করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            # ইমেজ প্রসেসিং
            image = Image.open(uploaded_file).convert('RGB')
            img_array = np.array(image)
            
            # অডিট চালানো
            score, audit_logs, subj, s_score = run_adobe_audit(img_array, image, uploaded_file.name)
            
            col1, col2, col3, col4 = st.columns([1, 3, 1.5, 1.2])
            
            with col1:
                thumb = image.copy(); thumb.thumbnail((120, 120))
                st.image(thumb)
            
            with col2:
                st.write(f"**{uploaded_file.name}**")
                st.caption(f"Category: {subj.title()}")
                if not audit_logs: st.markdown('<p style="color:green; font-size:12px;">✅ Quality: Excellent</p>', unsafe_allow_html=True)
                for log in audit_logs: st.markdown(f'<p class="log-text">{log}</p>', unsafe_allow_html=True)
            
            with col3:
                if score >= 80: st.markdown('<span class="pass-tag">✅ ACCEPTED</span>', unsafe_allow_html=True)
                else: st.markdown('<span class="fail-tag">🛑 REJECTED</span>', unsafe_allow_html=True)
                st.write(f"Sharpness: {s_score:.1f}")
                
            with col4:
                with st.popover("Master Prompt"):
                    st.write("**Fix & Re-Create Prompt:**")
                    q_fix = "ultra-sharp, cinematic lighting, photorealistic texture"
                    if score < 80: q_fix += ", razor sharp focus, zero artifacts, 8k resolution"
                    st.code(f"Professional photography of {subj}, {q_fix}, commercially ready --ar 16:9 --v 6.0", language="text")
            
            st.divider()
        except Exception as e:
            st.error(f"Error on {uploaded_file.name}: {e}")

st.info("নির্দেশ: যে ছবিগুলো 'Accepted' দেখাবে, সেগুলো অ্যাডোবি স্টকে দেওয়ার জন্য নিরাপদ।")
