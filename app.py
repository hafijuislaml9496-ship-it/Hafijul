import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import os

# ১. পেজ কনফিগারেশন
st.set_page_config(page_title="Adobe Stock Master Auditor", layout="wide")

st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; border: 1px solid #28a745; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; border: 1px solid #dc3545; }
    .status-risk { color: #856404; background-color: #fff3cd; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; border: 1px solid #ffc107; }
    .log-text { font-size: 13px; margin-bottom: 2px; color: #444; }
    </style>
    """, unsafe_allow_html=True)

# ২. নিখুঁত অডিট ইঞ্জিন
def perfect_audit(img_array, pil_img, filename):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs = []
    final_status = "ACCEPTED" # Default
    
    # --- মেগাপিক্সেল ---
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    if mp < 4.0:
        final_status = "REJECTED"
        logs.append(f"❌ Low Res: {mp:.2f}MP (Min 4MP needed)")

    # --- ক্যালিব্রেটেড শার্পনেস ---
    gh, gw = h//8, w//8
    peak_sharp = max([cv2.Laplacian(gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw], cv2.CV_64F).var() for i in range(8) for j in range(8)])
    
    # অ্যাডোবি রিয়েল স্ট্যান্ডার্ড: ২৬.০ এর নিচে রিস্ক, ১৫.০ এর নিচে রিজেক্ট
    if peak_sharp < 15.0:
        final_status = "REJECTED"
        logs.append(f"❌ Blurry/Artifacts: ({peak_sharp:.1f})")
    elif peak_sharp < 30.0:
        if final_status != "REJECTED": final_status = "RISKY"
        logs.append(f"⚠️ Soft Focus: ({peak_sharp:.1f})")

    # --- এআই গ্রাফিক্স এবং আইকন চেক ---
    edges = cv2.Canny(gray, 100, 200)
    edge_density = np.sum(edges > 0) / (h * w)
    if edge_density > 0.05: # যদি ছবি খুব বেশি অগোছালো হয়
        if peak_sharp < 40:
            final_status = "REJECTED"
            logs.append("❌ Technical Quality: Jagged edges/AI Artifacts.")

    # --- লোগো এবং টেক্সট ---
    try:
        text = pytesseract.image_to_string(pil_img).strip()
        if len(text) > 4:
            final_status = "REJECTED"
            logs.append(f"❌ Logo Found: '{text[:10]}'")
    except: pass

    subject = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')[:25]
    return final_status, logs, subject, peak_sharp

# ৩. মেইন অ্যাপ
st.title("🛡️ Adobe Stock Expert Auditor (Balanced Mode)")
uploaded_files = st.file_uploader("আপনার ছবিগুলো একসাথে ড্রপ করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            image = Image.open(uploaded_file).convert('RGB')
            img_array = np.array(image)
            status, audit_logs, subject_name, s_score = perfect_audit(img_array, image, uploaded_file.name)
            
            col1, col2, col3, col4 = st.columns([1, 3, 1.5, 1.2])
            with col1:
                thumb = image.copy(); thumb.thumbnail((120, 120))
                st.image(thumb)
            with col2:
                st.write(f"**{uploaded_file.name}**")
                st.caption(f"Subject: {subject_name.title()}")
                if not audit_logs: st.markdown('<p style="color:green; font-size:12px;">✅ Quality: Excellent</p>', unsafe_allow_html=True)
                for log in audit_logs: st.markdown(f'<p class="log-text">{log}</p>', unsafe_allow_html=True)
            with col3:
                if status == "ACCEPTED": st.markdown('<span class="status-pass">ACCEPTED</span>', unsafe_allow_html=True)
                elif status == "RISKY": st.markdown('<span class="status-risk">RISKY</span>', unsafe_allow_html=True)
                else: st.markdown('<span class="status-fail">REJECTED</span>', unsafe_allow_html=True)
                st.write(f"Sharpness: {s_score:.1f}")
            with col4:
                with st.popover("Master Prompt"):
                    q_fix = "razor sharp focus, 8k, cinematic lighting"
                    if status != "ACCEPTED": q_fix += ", extreme detail, ultra-high resolution texture"
                    m_prompt = f"Professional photography of {subject_name}, {q_fix}, photorealistic, no text, no logo --v 6.0"
                    st.code(m_prompt, language="text")
            st.divider()
        except Exception as e:
            st.error(f"Error: {e}")
