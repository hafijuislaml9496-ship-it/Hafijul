import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import os

# ১. পেজ কনফিগারেশন
st.set_page_config(page_title="Adobe Stock Master Auditor", layout="wide")

# ২. সিএসএস স্টাইল (স্ট্যাটাস এবং রিপোর্টের জন্য)
st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; border: 1px solid #28a745; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; border: 1px solid #dc3545; }
    .log-text { font-size: 13px; margin-bottom: 2px; color: #555; }
    </style>
    """, unsafe_allow_html=True)

# ৩. অডিট ইঞ্জিন (স্মার্ট এবং রিল্যাক্সড লজিক)
def run_expert_audit(img_array, pil_img, filename):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs = []
    critical_fail = False
    
    # --- মেগাপিক্সেল চেক ---
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    if mp < 4.0:
        critical_fail = True
        logs.append(f"❌ Low Res: {mp:.2f}MP (Need 4MP+)")

    # --- স্মার্ট শার্পনেস (১০x১০ গ্রিড) ---
    gh, gw = h//10, w//10
    peak_sharp = 0
    for i in range(10):
        for j in range(10):
            section = gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw]
            if section.size > 0:
                s = cv2.Laplacian(section, cv2.CV_64F).var()
                if s > peak_sharp: peak_sharp = s
    
    # অ্যাডোবি স্ট্যান্ডার্ড অনুযায়ী লিমিট (১২.০ এর নিচে হলে রিজেক্ট)
    if peak_sharp < 10.0:
        critical_fail = True
        logs.append(f"❌ Too Blurry: ({peak_sharp:.1f})")
    elif peak_sharp < 25.0:
        logs.append(f"⚠️ Soft Focus Risk: ({peak_sharp:.1f})")

    # --- লোগো এবং টেক্সট স্ক্যান ---
    try:
        text = pytesseract.image_to_string(pil_img).strip()
        if len(text) > 4:
            critical_fail = True
            logs.append(f"❌ Logo/Text Detected: '{text[:10]}'")
    except:
        pass

    # সাবজেক্ট নাম (ফাইলের নাম থেকে)
    subject = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')[:25]
    
    return critical_fail, logs, subject, peak_sharp

# ৪. মেইন অ্যাপ ইন্টারফেস
st.title("🛡️ Adobe Stock Professional Master Auditor")
st.write("একসাথে অনেক ছবি আপলোড করুন। এটি এখন আপনার এপ্রুভড ছবির সাথে সামঞ্জস্য রেখে রিপোর্ট দেবে।")

uploaded_files = st.file_uploader("আপনার ছবিগুলো একসাথে সিলেক্ট করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    st.subheader(f"📊 অডিট রিপোর্ট: {len(uploaded_files)} টি ছবি")
    
    for uploaded_file in uploaded_files:
        try:
            # ছবি লোড
            image = Image.open(uploaded_file).convert('RGB')
            img_array = np.array(image)
            
            # অডিট চালানো
            is_rejected, audit_logs, subject_name, s_score = run_expert_audit(img_array, image, uploaded_file.name)
            
            # ৪টি কলামে ফলাফল প্রদর্শন
            col1, col2, col3, col4 = st.columns([1, 3, 1.5, 1.2])
            
            with col1:
                thumb = image.copy()
                thumb.thumbnail((120, 120))
                st.image(thumb)
                
            with col2:
                st.write(f"**{uploaded_file.name}**")
                st.caption(f"Subject: {subject_name.title()}")
                if not audit_logs:
                    st.markdown('<p style="color:green; font-size:13px;">✅ কোয়ালিটি পারফেক্ট।</p>', unsafe_allow_html=True)
                else:
                    for log in audit_logs:
                        st.markdown(f'<p class="log-text">{log}</p>', unsafe_allow_html=True)
                        
            with col3:
                if not is_rejected:
                    st.markdown('<span class="status-pass">✅ ACCEPTED</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-fail">🛑 REJECTED</span>', unsafe_allow_html=True)
                st.write(f"Sharpness: {s_score:.1f}")
                
            with col4:
                with st.popover("AI Prompt"):
                    st.write("**Master AI Prompt:**")
                    q_fix = "razor sharp focus, cinematic lighting, masterpiece"
                    if s_score < 30: q_fix += ", extreme details, photorealistic texture"
                    
                    full_p = f"Professional stock photography of {subject_name}, {q_fix}, 8k, commercially ready, no text, no logo --v 6.0"
                    st.code(full_p, language="text")
            
            st.divider()

        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")

st.success("সব ছবির অডিট সম্পন্ন হয়েছে।")
