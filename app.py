import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import os

# ১. পেজ এবং স্টাইল কনফিগারেশন
st.set_page_config(page_title="Adobe Stock Ultimate Auditor", layout="wide")

st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .status-risk { color: #856404; background-color: #fff3cd; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .log-text { font-size: 13px; margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

# ২. কোর অডিট ইঞ্জিন (সব ফিচার একসাথে)
def master_audit(img_array, pil_img, filename):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs = []
    score = 100
    
    # --- ফিচার ১: রেজোলিউশন চেক ---
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    if mp < 4.0:
        score -= 40
        logs.append(f"❌ Low Res: {mp:.2f}MP (Adobe needs 4MP+)")

    # --- ফিচার ২: স্মার্ট পিক শার্পনেস (Bokeh Support) ---
    gh, gw = h//6, w//6
    sections = [gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw] for i in range(6) for j in range(6)]
    peak_sharp = max([cv2.Laplacian(sec, cv2.CV_64F).var() for sec in sections])
    
    if peak_sharp < 42:
        score -= 30
        logs.append(f"❌ Soft Focus: মূল সাবজেক্ট শার্প নয় ({peak_sharp:.1f})")
    elif peak_sharp < 60:
        score -= 10
        logs.append("⚠️ Slightly Soft: রিজেকশন রিস্ক আছে।")

    # --- ফিচার ৩: স্মার্ট গ্রাফিক্স/আইকন ইন্টিগ্রিটি (Context Aware) ---
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) > 5: # যদি আইকন-জাতীয় কিছু থাকে
        messy_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 10:
                peri = cv2.arcLength(cnt, True)
                circularity = 4 * np.pi * (area / (peri * peri)) if peri > 0 else 0
                if circularity < 0.4: messy_count += 1
        if messy_count > 15:
            score -= 35
            logs.append("❌ Deformed Icons: গ্রাফিক্সগুলো অগোছালো বা ভাঙা।")

    # --- ফিচার ৪: নয়েজ এবং আর্টিফ্যাক্টস (AI Waxy Texture) ---
    try:
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        if noise > 6.5:
            score -= 20
            logs.append(f"❌ High Noise/Artifacts: ({noise:.2f})")
    except: pass

    # --- ফিচার ৫: লোগো এবং টেক্সট স্ক্যানার (OCR) ---
    try:
        text = pytesseract.image_to_string(pil_img).strip()
        if len(text) > 3:
            score -= 50
            logs.append(f"❌ Logo/Text Detected: '{text[:10]}'")
    except: pass

    # --- ফিচার ৬: অটো সাবজেক্ট (ফাইলের নাম থেকে) ---
    subject = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')[:20]
    
    return score, logs, subject

# ৩. মেইন অ্যাপ ইন্টারফেস
st.title("🛡️ Adobe Stock Master Expert Auditor")
st.write("এই একটি টুল আপনার সব ধরণের ছবির (মানুষ, গ্রাফিক্স, ল্যান্ডস্কেপ) মান অ্যাডোবি স্ট্যান্ডার্ডে অডিট করবে।")

uploaded_files = st.file_uploader("আপনার ছবিগুলো একসাথে এখানে দিন...", type=["jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    st.subheader(f"📊 বিশ্লেষণ করা হচ্ছে: {len(uploaded_files)} টি ছবি")
    
    for uploaded_file in uploaded_files:
        image = Image.open(uploaded_file).convert('RGB')
        img_array = np.array(image)
        
        # মাস্টার অডিট চালানো
        score, audit_logs, subject = master_audit(img_array, image, uploaded_file.name)
        
        # ড্যাশবোর্ড কলাম
        col1, col2, col3, col4 = st.columns([1, 3, 1.5, 1.2])
        
        with col1:
            thumb = image.copy(); thumb.thumbnail((120, 120))
            st.image(thumb)
            
        with col2:
            st.write(f"**{uploaded_file.name}**")
            st.caption(f"Subject: {subject.title()}")
            if not audit_logs:
                st.markdown('<p class="log-text" style="color:green;">✅ কোয়ালিটি নিখুঁত।</p>', unsafe_allow_html=True)
            else:
                for log in audit_logs:
                    st.markdown(f'<p class="log-text">{log}</p>', unsafe_allow_html=True)
                    
        with col3:
            if score >= 85: st.markdown('<span class="status-pass">ACCEPTED</span>', unsafe_allow_html=True)
            elif score >= 55: st.markdown('<span class="status-risk">RISKY</span>', unsafe_allow_html=True)
            else: st.markdown('<span class="status-fail">REJECTED</span>', unsafe_allow_html=True)
            st.write(f"Confidence: **{score}%**")
            
        with col4:
            with st.popover("Master Prompt"):
                st.write("**Unique Master Prompt:**")
                q_tags = "razor sharp focus, 8k, cinematic lighting, masterpiece"
                if score < 85: q_tags += ", extreme clarity, ultra-clean textures"
                m_prompt = f"Professional stock photography of {subject}, {q_tags}, photorealistic, no text, no logo, commercially ready --v 6.0"
                st.code(m_prompt, language="text")
        
        st.divider()

st.success("অডিট সম্পন্ন হয়েছে।")
