import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import easyocr

# AI মডেল লোড করা (একবারই হবে)
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

reader = load_ocr()

st.set_page_config(page_title="Adobe Stock Pro Validator", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .verdict-box { padding: 20px; border-radius: 10px; margin-bottom: 20px; font-size: 22px; font-weight: bold; text-align: center; border: 2px solid; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Adobe Stock Acceptance Checker (AI Scanner)")

uploaded_file = st.file_uploader("আপনার ছবি এখানে দিন...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    with st.spinner('AI আপনার ছবি স্ক্যান করছে, দয়া করে অপেক্ষা করুন...'):
        # ১. টেকনিক্যাল চেক (MP, Sharpness, Noise)
        width, height = image.size
        mp = (width * height) / 1_000_000
        
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
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))

        # ২. লোগো এবং টেক্সট স্ক্যানার (OCR)
        ocr_results = reader.readtext(img_array)
        detected_texts = [res[1] for res in ocr_results]

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True, caption="Uploaded Image")

    with col2:
        st.subheader("📢 চূড়ান্ত ফলাফল (Final Verdict)")
        
        errors = []
        if mp < 4.0:
            errors.append(f"❌ ছবির সাইজ ছোট ({mp:.2f} MP)। অন্তত ৪ MP লাগবে।")
        if sharpness < 25:
            errors.append("❌ সাবজেক্ট ফোকাস নেই (Blurry)।")
        if noise > 6.5:
            errors.append("❌ ছবিতে দানা (Noise) বেশি।")
        if detected_texts:
            errors.append(f"❌ ব্র্যান্ড লোগো বা টেক্সট পাওয়া গেছে: {', '.join(detected_texts)}")

        if not errors:
            st.markdown('<div class="verdict-box" style="background-color: #d4edda; border-color: #28a745; color: #155724;">✅ সবকিছু পারফেক্ট! Adobe Stock-এ আপলোড করতে পারেন।</div>', unsafe_allow_html=True)
            st.success("ছবিতে কোনো লোগো বা টেক্সট পাওয়া যায়নি এবং টেকনিক্যাল কোয়ালিটি চমৎকার।")
        else:
            st.markdown('<div class="verdict-box" style="background-color: #f8d7da; border-color: #dc3545; color: #721c24;">⚠️ রিজেক্ট হওয়ার সম্ভাবনা আছে!</div>', unsafe_allow_html=True)
            for err in errors:
                st.write(err)

        st.subheader("🛠️ আপনার করণীয় (Action Plan)")
        if detected_texts:
            st.warning(f"👉 **লোগো রিমুভ করুন:** ছবিতে '{', '.join(detected_texts)}' লেখা বা লোগো দেখা যাচ্ছে। এটি ফটোশপের Content-Aware Fill দিয়ে মুছে ফেলুন।")
        if mp < 4.0:
            st.warning("👉 **সাইজ বাড়ান:** ছবিটির রেজোলিউশন কোনো AI Upscaler দিয়ে বাড়িয়ে নিন।")
        if not errors:
            st.info("💡 সব ঠিক আছে, এখন আপনি নিশ্চিন্তে আপলোড করতে পারেন।")
