import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import os

# ১. পেজ এবং স্টাইল কনফিগারেশন
st.set_page_config(page_title="Professional Adobe Stock Auditor", layout="wide")

st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; border: 1px solid #28a745; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; border: 1px solid #dc3545; }
    .log-text { font-size: 13px; margin-bottom: 2px; color: #555; }
    </style>
    """, unsafe_allow_html=True)

# ২. মেইন অডিট ফাংশন
def expert_audit(img_array, pil_img, filename):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs = []
    critical_fail = False # যদি বড় কোনো ভুল থাকে
    
    # --- মেগাপিক্সেল (Hard Rule) ---
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    if mp < 4.0:
        critical_fail = True
        logs.append(f"❌ Low Res: {mp:.2f}MP (Need 4MP+)")

    # --- স্মার্ট শার্পনেস (অ্যাডোবি স্ট্যান্ডার্ডে ম্যাচ করা) ---
    # আমরা ছবিকে ১০x১০ গ্রিডে ভাগ করে সর্বোচ্চ শার্পনেস পয়েন্ট খুঁজব
    gh, gw = h//10, w//10
    peak_sharp = 0
    for i in range(10):
        for j in range(10):
            section = gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw]
            if section.size > 0:
                s = cv2.Laplacian(section, cv2.CV_64F).var()
                if s > peak_sharp: peak_sharp = s
    
    # আগে এটি ৪২ ছিল, এখন ১৫ করা হয়েছে যাতে প্রফেশনাল ছবিগুলো পাস হয়
    if peak_sharp < 12.0:
        critical_fail = True
        logs.append("❌ Critical Blur: ছবিটি অনেক বেশি ঝাপসা।")
    elif peak_sharp < 25.0:
        logs.append("⚠️ Soft Focus: ছবি কিছুটা সফট (Acceptable).")

    # --- আইকন/গ্রাফিক্স চেক (শুধুমাত্র গ্রাফিক্সের ক্ষেত্রে) ---
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) > 10:
        messy = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 15:
                peri = cv2.arcLength(cnt, True)
                if peri > 0:
                    circularity = 4 * np.pi * (area / (peri * peri))
                    if circularity < 0.25: messy += 1
        if messy > 25:
            logs.append("⚠️ Graphic Artifacts: আইকনগুলোতে খুঁত থাকতে পারে।")

    # --- লোগো এবং টেক্সট স্ক্যান ---
    try:
        text = pytesseract.image_to_string(pil_img).strip()
        if len(text) > 4:
            critical_fail = True
            logs.append(f"❌ Logo/Text: '{text[:10]}...' পাওয়া গেছে।")
    except: pass

    # --- সাবজেক্ট এবং প্রম্পট লজিক ---
    subject = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')[:25]
    
    return critical_fail, logs, subject, peak_sharp

# ৩. মেইন ইন্টারফেস
st.title("🛡️ Adobe Stock Professional Master Auditor")
st.write("বাল্ক ফটো অডিট। আপনার এপ্রুভড ছবির কোয়ালিটির সাথে এটি এখন সামঞ্জস্যপূর্ণ।")

uploaded_files = st.file_uploader("আপনার ছবিগুলো আপলোড করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    st.subheader(f"📊 অডিট রিপোর্ট: {len(uploaded_files)} টি ছবি")
    
    for uploaded_file in uploaded_files:
        try:
            image = Image.open(uploaded_file).convert('RGB')
            img_array = np.array(image)
            
            # অডিট চালানো
            is_rejected, audit_logs, subject_name, s_score = expert_audit(img_array, image, uploaded_file.name)
            
            # ডিসপ্লে কলাম
            col1, col2, col3, c
