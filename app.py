import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract

# কনফিগারেশন
st.set_page_config(page_title="Adobe Stock AI Specialist", layout="wide")

st.markdown("""
    <style>
    .verdict-header { font-size: 24px; font-weight: bold; padding: 15px; border-radius: 10px; text-align: center; }
    .fix-box { background-color: #fffaf0; border-left: 5px solid #ed8936; padding: 15px; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Adobe Stock AI-Graphics Auditor")
st.write("এই টুলটি এখন এআই জেনারেটেড ছবির 'আর্টিফ্যাক্টস' এবং 'এজিং' ত্রুটি ধরতে পারে।")

uploaded_file = st.file_uploader("আপনার এআই ছবিটি আপলোড করুন...", type=["jpg", "jpeg"])

def detect_artifacts(img_array):
    # ১. কালার ব্যান্ডিং চেক (Gradients check)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
    gradient_mag = np.sqrt(sobelx**2 + sobely**2)
    banding_score = np.mean(gradient_mag)
    
    # ২. এজ স্মুথনেস (Aliasing check)
    edges = cv2.Canny(gray, 100, 200)
    aliasing_score = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])
    
    return banding_score, aliasing_score

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    with st.spinner('গভীরভাবে বিশ্লেষণ করা হচ্ছে (এটি সময় নিতে পারে)...'):
        w, h = image.size
        mp = (w * h) / 1000000
        banding, aliasing = detect_artifacts(img_array)
        
        # শার্পনেস এবং নয়েজ
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        sharp_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True)

    with col2:
        st.subheader("📢 এআই অডিট রিপোর্ট")
        
        errors = []
        # এআই ছবির জন্য কড়া নিয়ম (Strict Rules)
        if mp < 4.0: errors.append(f"❌ রেজোলিউশন কম ({mp:.2f}MP)")
        if aliasing > 0.05: errors.append("❌ Aliasing Issue: আইকন বা গ্রাফিক্সের ধারগুলো ফাটা (Jagged edges)।")
        if sharp_score < 20: errors.append("❌ Soft Focus: ছবিটি যথেষ্ট শার্প নয়।")
        if noise > 5.5: errors.append("❌ Artifacts: ছবিতে ডিজিটাল নয়েজ বা এআই ত্রুটি আছে।")

        if not errors:
            st.markdown('<div class="verdict-header" style="background-color: #c6f6d5; color: #22543d;">✅ Adobe Stock-এর জন্য উপযুক্ত!</div>', unsafe_allow_html=True)
            st.success("সবকিছু ঠিক আছে।")
        else:
            st.markdown('<div class="verdict-header" style="background-color: #fed7d7; color: #822727;">🛑 রিজেকশন রিস্ক পাওয়া গেছে!</div>', unsafe_allow_html=True)
            for e in errors: st.write(e)
            
            st.subheader("🛠️ এই ছবি ঠিক করার উপায়:")
            if "Aliasing" in str(errors):
                st.info("আপনার এআই টুলে 'Anti-aliasing' বা 'High Definition' মুড অন করে আবার জেনারেট করুন।")
            if "Noise" in str(errors):
                st.info("ফটোশপে গিয়ে 'Noise Reduction' বা 'Denoise' ব্যবহার করুন।")

        # মাস্টার প্রম্পট
        st.subheader("🎨 পারফেক্ট এআই প্রম্পট (সমস্যাহীন)")
        st.code(f"Clean commercial stock graphic of [SUBJECT], minimalistic style, vector-like precision, smooth anti-aliased edges, zero noise, high ISO clarity, photorealistic render, cinematic lighting --ar 16:9 --v 6.0", language="text")
