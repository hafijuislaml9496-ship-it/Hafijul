import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma

# পেজ সেটআপ
st.set_page_config(page_title="Adobe Stock Quality Pro", layout="wide", page_icon="📸")

st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Adobe Stock Contributor Validator")
st.write("এই টুলটি Adobe Stock-এর অফিশিয়াল কোয়ালিটি স্ট্যান্ডার্ড অনুযায়ী আপনার ছবি চেক করবে।")

uploaded_file = st.file_uploader("আপনার ছবিটি এখানে আপলোড করুন...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    col1, col2 = st.columns([1, 1])

    with col1:
        st.image(image, caption='Uploaded Image', use_column_width=True)
        
    with col2:
        st.subheader("🔍 Technical Quality Report")
        
        # ১. মেগাপিক্সেল চেক (Adobe Rule: Min 4MP)
        width, height = image.size
        mp = (width * height) / 1_000_000
        
        if mp >= 4.0:
            st.success(f"✅ Resolution: {mp:.2f} MP (Passed)")
        else:
            st.error(f"❌ Resolution: {mp:.2f} MP (Failed: Adobe requires at least 4MP)")

        # ২. সাবজেক্ট শার্পনেস চেক (Smart Focus Detection)
        # আমরা এখন পুরো ছবির গড় না দেখে, ছবির সবচেয়ে শার্প অংশটি খুঁজব।
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # ছবিকে ছোট ছোট গ্রিডে ভাগ করে শার্পনেস চেক করা (যাতে ব্যাকগ্রাউন্ড ব্লার থাকলেও সমস্যা না হয়)
        def get_max_sharpness(img):
            h, w = img.shape
            quad_h, quad_w = h//3, w//3
            max_v = 0
            for i in range(3):
                for j in range(3):
                    section = img[i*quad_h:(i+1)*quad_h, j*quad_w:(j+1)*quad_w]
                    v = cv2.Laplacian(section, cv2.CV_64F).var()
                    if v > max_v: max_v = v
            return max_v

        sharpness_score = get_max_sharpness(gray)
        
        # Adobe Standard অনুযায়ী থ্রেশহোল্ড এডজাস্ট করা
        if sharpness_score > 40: # ল্যাপ্লাসিয়ান ভ্যালু ৪০+ মানে সাবজেক্টে ফোকাস আছে
            st.success(f"✅ Subject Focus: {sharpness_score:.2f} (Sharp & Focused)")
        elif sharpness_score > 15:
            st.warning(f"⚠️ Subject Focus: {sharpness_score:.2f} (Acceptable but soft)")
        else:
            st.error(f"❌ Subject Focus: {sharpness_score:.2f} (Too Blurry/Out of focus)")

        # ৩. নয়েজ ডিটেকশন (Grain Check)
        noise_sigma = estimate_sigma(img_array, channel_axis=-1)
        avg_noise = np.mean(noise_sigma)
        
        if avg_noise < 4.0:
            st.success(f"✅ Noise/Grain: {avg_noise:.2f} (Clean - Low Noise)")
        elif avg_noise < 7.0:
            st.warning(f"⚠️ Noise/Grain: {avg_noise:.2f} (Slight Noise - Might need Denoise)")
        else:
            st.error(f"❌ Noise/Grain: {avg_noise:.2f} (Too Noisy - High chance of rejection)")

    # ৪. বাড়তি নির্দেশনা (Adobe-Specific Reminders)
    st.divider()
    st.subheader("💡 Adobe Stock Submission Tips:")
    
    t1, t2, t3 = st.columns(3)
    with t1:
        st.info("**IP & Logos:** আপনার ছবিতে কি কোনো ব্র্যান্ড লোগো বা টেক্সট আছে? থাকলে সেটি রিজেক্ট হবে। এডিট করে মুছে ফেলুন।")
    with t2:
        st.info("**Chromatic Aberration:** ছবির ধারের দিকে বেগুনি বা সবুজ বর্ডার থাকলে সেটি সরিয়ে ফেলুন।")
    with t3:
        st.info("**Artifacts:** ছবি অতিরিক্ত এডিট করবেন না। পিক্সেল ফেটে গেলে (Banding) Adobe তা গ্রহণ করবে না।")

    if mp >= 4.0 and sharpness_score > 30 and avg_noise < 6:
        st.balloons()
        st.success("🌟 এই ছবিটি Adobe Stock-এর টেকনিক্যাল রিকোয়ারমেন্ট পূরণ করেছে! আপলোড করার জন্য ভালো ক্যান্ডিডেট।")
