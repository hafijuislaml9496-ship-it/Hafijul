import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma

# পেজ সেটআপ
st.set_page_config(page_title="Adobe Stock Validator", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .status-box { padding: 20px; border-radius: 10px; margin-bottom: 20px; font-size: 20px; font-weight: bold; text-align: center; }
    .solution-box { background-color: #fff3cd; padding: 15px; border-left: 5px solid #ffc107; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 Adobe Stock Acceptance Checker")

uploaded_file = st.file_uploader("আপনার ছবি এখানে দিন...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    # ১. রেজোলিউশন চেক
    width, height = image.size
    mp = (width * height) / 1_000_000
    
    # ২. শার্পনেস চেক
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
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
    sharpness = get_max_sharpness(gray)
    
    # ৩. নয়েজ চেক
    noise = np.mean(estimate_sigma(img_array, channel_axis=-1))

    # --- সরাসরি সিদ্ধান্ত (Direct Verdict) ---
    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True)

    with col2:
        st.subheader("📢 চূড়ান্ত ফলাফল (Final Verdict)")
        
        errors = []
        if mp < 4.0:
            errors.append(f"❌ ছবির সাইজ ছোট। বর্তমানে {mp:.2f} MP আছে, কিন্তু Adobe-এ অন্তত ৪ MP লাগে।")
        if sharpness < 25:
            errors.append("❌ ছবির মেইন সাবজেক্ট ঝাপসা (Out of focus)।")
        if noise > 6.5:
            errors.append("❌ ছবিতে অনেক বেশি দানা (Noise/Grain) আছে।")

        if not errors:
            st.markdown('<div class="status-box" style="background-color: #d4edda; color: #155724;">✅ এই ছবিটি Adobe Stock-এ দেওয়ার জন্য ১০০% প্রস্তুত!</div>', unsafe_allow_html=True)
            st.success("সবকিছু ঠিক আছে। আপনি নির্দ্বিধায় আপলোড করতে পারেন।")
        else:
            st.markdown('<div class="status-box" style="background-color: #f8d7da; color: #721c24;">⚠️ ছবিটি রিজেক্ট হওয়ার সম্ভাবনা আছে।</div>', unsafe_allow_html=True)
            for err in errors:
                st.write(err)

        # --- সরাসরি সমাধান (Direct Solutions) ---
        st.subheader("🛠️ কিভাবে সমাধান করবেন? (Direct Fix)")
        if mp < 4.0:
            st.warning(f"👉 **সমাধান ১:** কোনো AI Image Upscaler দিয়ে ছবিটির সাইজ অন্তত ২০০% বাড়িয়ে নিন।")
        if sharpness < 25:
            st.warning("👉 **সমাধান ২:** ফটোশপে গিয়ে 'Unsharp Mask' ব্যবহার করুন অথবা সাবজেক্টের শার্পনেস বাড়ান। যদি বেশি ঝাপসা হয় তবে এই ছবি বাদ দিন।")
        if noise > 6.5:
            st.warning("👉 **সমাধান ৩:** Lightroom বা ফটোশপে 'Noise Reduction' স্লাইডারটি ব্যবহার করে ছবির দানা কমিয়ে ফেলুন।")
        
        if not errors:
            st.info("💡 আপলোডের আগে ছবিতে কোনো কোম্পানির লোগো বা মানুষের নাম থাকলে তা মুছে দিন।")
