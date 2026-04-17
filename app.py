import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma

# পেজ সেটআপ
st.set_page_config(page_title="Adobe Stock Quality Checker", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 Adobe Stock Quality Inspector")
st.write("আপনার ছবি আপলোড করে দেখুন এটি Adobe Stock-এর জন্য উপযুক্ত কি না।")

uploaded_file = st.file_uploader("একটি ছবি সিলেক্ট করুন...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # ছবি ওপেন করা
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    col1, col2 = st.columns([1, 1])

    with col1:
        st.image(image, caption='Uploaded Image', use_column_width=True)
        
    with col2:
        st.subheader("📊 Analysis Report")
        
        # ১. রেজোলিউশন চেক (Megapixel)
        width, height = image.size
        mp = (width * height) / 1_000_000
        
        if mp >= 4.0:
            st.success(f"✅ Resolution: {mp:.2f} MP (Passed)")
        else:
            st.error(f"❌ Resolution: {mp:.2f} MP (Too Low! Minimum 4MP required)")

        # ২. শার্পনেস ডিটেকশন
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        sharpness_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        if sharpness_score > 100:
            st.success(f"✅ Sharpness: {sharpness_score:.2f} (Good)")
        else:
            st.warning(f"⚠️ Sharpness: {sharpness_score:.2f} (Image might be blurry)")

        # ৩. নয়েজ ডিটেকশন
        noise_sigma = estimate_sigma(img_array, channel_axis=-1)
        avg_noise = np.mean(noise_sigma)
        
        if avg_noise < 5:
            st.success(f"✅ Noise Level: {avg_noise:.2f} (Clean)")
        else:
            st.error(f"❌ Noise Level: {avg_noise:.2f} (Grainy/Noisy)")

    # চূড়ান্ত মন্তব্য
    st.divider()
    if mp >= 4.0 and sharpness_score > 80 and avg_noise < 8:
        st.balloons()
        st.success("🌟 এই ছবিটি Adobe Stock-এ অ্যাপ্রুভ হওয়ার অনেক ভালো সম্ভাবনা আছে!")
    else:
        st.error("❗ ছবিতে কিছু সমস্যা আছে। আপলোড করার আগে আরেকবার চেক করুন।")
