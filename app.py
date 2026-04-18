import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import os

# ১. পেজ কনফিগারেশন
st.set_page_config(page_title="Adobe Stock Master Auditor Pro", layout="wide")

st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 11px; border: 1px solid #28a745; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 11px; border: 1px solid #dc3545; }
    .status-risk { color: #856404; background-color: #fff3cd; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 11px; border: 1px solid #ffc107; }
    .log-text { font-size: 12px; color: #d32f2f; margin-bottom: 2px; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# ২. মেইন অডিট ইঞ্জিন (আগের সব ফিচার + নতুন গিবিশ টেক্সট ডিটেক্টর)
def run_final_audit(img_array, pil_img, filename):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs = []
    score = 100
    
    # --- মেগাপিক্সেল চেক (Stable Fix) ---
    mp = (h * w) / 1000000.0
    if mp < 4.0:
        score -= 50
        logs.append(f"❌ Low Res: {mp:.2f}MP (Adobe needs 4MP+)")

    # --- স্মার্ট ফোকাল শার্পনেস (Bokeh/Focal Point Support) ---
    gh, gw = h//10, w//10
    max_sharp = 0
    for i in range(10):
        for j in range(10):
            section = gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw]
            if section.size > 0:
                s = cv2.Laplacian(section, cv2.CV_64F).var()
                if s > max_sharp: max_sharp = s
    
    if max_sharp < 12.0:
        score -= 40
        logs.append(f"❌ Soft Focus: মূল সাবজেক্ট ঝাপসা ({max_sharp:.1f})")
    elif max_sharp < 28.0:
        logs.append(f"⚠️ Soft Focus Risk: ({max_sharp:.1f})")

    # --- নতুন ফিচার: এআই হিজিবিজি টেক্সট ও ইউআই চেক (Gibberish Detection) ---
    try:
        # OCR দিয়ে টেক্সট পড়ার চেষ্টা করা
        detected_text = pytesseract.image_to_string(pil_img).strip()
        # যদি অনেক ছোট ছোট টেক্সট পাওয়া যায় যা কোনো অর্থ তৈরি করে না
        if len(detected_text) > 3:
            # যদি টেক্সটের ভেতর অসংলগ্ন ক্যারেক্টার থাকে (এআই হিজিবিজি)
            words = detected_text.split()
            real_word_count = len([w for w in words if len(w) > 2])
            if real_word_count < 2 and len(detected_text) > 10:
                score -= 60
                logs.append("❌ Gibberish AI Text: স্ক্রিনে অর্থহীন হিজিবিজি লেখা পাওয়া গেছে।")
            else:
                score -= 60
                logs.append(f"❌ IP Claim: লোগো বা টেক্সট ডিটেক্ট হয়েছে: '{detected_text[:10]}'")
    except:
        pass

    # --- নয়েজ এবং এআই আর্টিফ্যাক্টস ---
    try:
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        if noise > 6.5:
            score -= 20
            logs.append(f"❌ Technical Artifacts: হাই নয়েজ বা এআই ত্রুটি।")
    except: pass

    # সাবজেক্ট নাম (ফাইলের নাম থেকে)
    subject = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')[:20]
    
    return score, logs, subject, max_sharp

# ৩. মেইন ইউজার ইন্টারফেস
st.title("🛡️ Bulk Adobe Stock Master Auditor (Pro)")
st.write("সব ধরণের ফিচার যুক্ত মাস্টার টুল। এটি এখন এআই-এর হিজিবিজি লেখাও শনাক্ত করতে পারে।")

uploaded_files = st.file_uploader("ছবিগুলো একসাথে ড্রপ করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            image = Image.open(uploaded_file).convert('RGB')
            img_array = np.array(image)
            
            # অডিট চালানো
            score, audit_logs, subj, s_score = run_final_audit(img_array, image, uploaded_file.name)
            
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
                if score >= 80: st.markdown('<span class="status-pass">✅ ACCEPTED</span>', unsafe_allow_html=True)
                elif score >= 50: st.markdown('<span class="status-risk">⚠️ RISKY</span>', unsafe_allow_html=True)
                else: st.markdown('<span class="status-fail">🛑 REJECTED</span>', unsafe_allow_html=True)
                st.write(f"S-Score: {s_score:.1f}")
                
            with col4:
                with st.popover("Master Prompt"):
                    st.write("**Fix & Re-Create Prompt:**")
                    q_fix = "ultra-sharp, cinematic lighting, photorealistic texture"
                    if score < 80: q_fix += ", razor sharp focus, zero artifacts, legible UI text"
                    # ইউনিক প্রম্পট
                    st.code(f"Professional photography of {subj}, {q_fix}, 8k, commercially ready --ar 16:9 --v 6.0", language="text")
            
            st.divider()
        except Exception as e:
            st.error(f"Error on {uploaded_file.name}: {e}")

st.info("টিপস: স্ক্রিনের ভেতরের টেক্সট যদি হিজিবিজি হয়, তবে তা ফটোশপ দিয়ে ব্লার করে দিন।")
