import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract

st.set_page_config(page_title="Adobe Stock Pro Validator", layout="wide")

st.markdown("""
    <style>
    .pass-box { background-color: #d4edda; border: 2px solid #28a745; padding: 15px; border-radius: 10px; color: #155724; font-weight: bold; text-align: center; }
    .warn-box { background-color: #fff3cd; border: 2px solid #ffc107; padding: 15px; border-radius: 10px; color: #856404; }
    .prompt-container { background-color: #f1f3f5; padding: 15px; border-radius: 8px; font-family: monospace; border: 1px solid #dee2e6; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚖️ Adobe Stock Quality Matcher")
st.write("এই টুলটি এখন Adobe-এর আসল একসেপ্টেন্স লেভেলের সাথে ক্যালিব্রেট করা হয়েছে।")

uploaded_file = st.file_uploader("আপনার ছবি আপলোড করুন...", type=["jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    with st.spinner('বিশ্লেষণ চলছে...'):
        # টেকনিক্যাল ডেটা
        w, h = image.size
        mp = (w * h) / 1000000
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # স্মার্ট শার্পনেস (খুবই নমনীয় রাখা হয়েছে প্রফেশনাল ছবির জন্য)
        sharp_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # নয়েজ ক্যালকুলেশন
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        
        # টেক্সট স্ক্যান
        text = pytesseract.image_to_string(image).strip()

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True)

    with col2:
        st.subheader("📢 অডিট রিপোর্ট")
        
        critical_errors = []
        warnings = []

        # ১. রেজোলিউশন (এটি অ্যাডোবির হার্ড রুল)
        if mp < 4.0:
            critical_errors.append(f"❌ রেজোলিউশন কম ({mp:.2f} MP)। অন্তত ৪ MP লাগবে।")

        # ২. শার্পনেস (অ্যাডোবি স্ট্যান্ডার্ড অনুযায়ী অ্যাডজাস্ট করা)
        if sharp_score < 12: # ১৫ এর নিচে হলে সত্যিই খুব ঝাপসা
            critical_errors.append("❌ ছবি অনেক বেশি ঝাপসা।")
        elif sharp_score < 25:
            warnings.append("⚠️ ছবি কিছুটা সফট, তবে অ্যাডোবি এটি গ্রহণ করতে পারে।")

        # ৩. নয়েজ (অ্যাডজাস্ট করা)
        if noise > 8.0:
            critical_errors.append("❌ ছবিতে অতিরিক্ত নয়েজ (Grain)।")
        elif noise > 5.0:
            warnings.append("⚠️ সামান্য নয়েজ আছে, তবে এটি গ্রহণযোগ্য।")

        # ৪. লোগো
        if len(text) > 3:
            critical_errors.append(f"❌ লোগো বা টেক্সট ডিটেক্ট হয়েছে: '{text[:15]}'")

        # ফলাফল প্রদর্শন
        if not critical_errors:
            st.markdown('<div class="pass-box">✅ ছবিটি Adobe Stock-এর স্ট্যান্ডার্ড অনুযায়ী উপযুক্ত!</div>', unsafe_allow_html=True)
            if warnings:
                st.write("### ছোট কিছু বিষয় লক্ষ্য করুন:")
                for w in warnings: st.warning(w)
        else:
            st.error("🛑 রিজেকশন রিস্ক আছে!")
            for e in critical_errors: st.write(e)

        # মাস্টার প্রম্পট জেনারেটর
        if critical_errors or warnings:
            st.subheader("🎨 AI Re-Creation Master Prompt")
            st.write("এই ছবিটিকে পারফেক্ট করার জন্য এই প্রম্পটটি এআই-তে ব্যবহার করুন:")
            
            # সাবজেক্ট ডিটেকশন সিমুলেশন
            p_text = f"Masterpiece stock photography, [INPUT_SUBJECT_HERE], cinematic lighting, ultra-sharp focus, 8k resolution, photorealistic, clean composition, no logos, no text, zero noise, high clarity, commercially ready --ar 16:9 --v 6.0"
            
            st.markdown(f'<div class="prompt-container">{p_text}</div>', unsafe_allow_html=True)
            st.caption("নির্দেশ: [INPUT_SUBJECT_HERE] এর জায়গায় আপনার ছবির নাম লিখুন।")
