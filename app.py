import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract

# কনফিগারেশন
st.set_page_config(page_title="Adobe Stock Master Intelligence", layout="wide")

st.markdown("""
    <style>
    .pass-card { background-color: #e6fffa; border: 2px solid #38b2ac; padding: 20px; border-radius: 15px; color: #234e52; text-align: center; }
    .fail-card { background-color: #fff5f5; border: 2px solid #e53e3e; padding: 20px; border-radius: 15px; color: #742a2a; text-align: center; }
    .prompt-box { background-color: #f7fafc; border: 1px dashed #4a5568; padding: 15px; border-radius: 10px; font-family: monospace; color: #2d3748; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧠 Adobe Stock Master Auditor (Pro AI)")
st.write("এই টুলটি এখন প্রফেশনাল বোকেহ (Bokeh), নাইট শট এবং কমার্শিয়াল গ্রাফিক্স শনাক্ত করতে সক্ষম।")

uploaded_file = st.file_uploader("আপনার ছবিটি আপলোড করুন...", type=["jpg", "jpeg"])

def advanced_audit(img_array, pil_img):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    w, h = pil_img.size
    mp = (w * h) / 1000000
    
    # ১. স্মার্ট শার্পনেস (১০x১০ গ্রিড অ্যানালাইসিস)
    # প্রফেশনাল ছবিতে শুধু সাবজেক্ট শার্প থাকে। আমরা পুরো ছবির সেরা ৫% শার্পনেস দেখব।
    gh, gw = gray.shape[0]//10, gray.shape[1]//10
    scores = []
    for i in range(10):
        for j in range(10):
            section = gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw]
            scores.append(cv2.Laplacian(section, cv2.CV_64F).var())
    
    peak_sharpness = sorted(scores, reverse=True)[5] # সেরা ৫ম গ্রিড স্কোর
    
    # ২. ডাইনামিক নয়েজ চেক (আলোর ওপর ভিত্তি করে)
    avg_brightness = np.mean(gray)
    noise_lvl = np.mean(estimate_sigma(img_array, channel_axis=-1))
    
    # রাতের ছবির জন্য নয়েজ লিমিট বেশি হবে
    noise_threshold = 9.0 if avg_brightness < 50 else 6.0
    
    # ৩. লোগো/টেক্সট চেক
    text = pytesseract.image_to_string(pil_img).strip()
    
    return mp, peak_sharpness, noise_lvl, noise_threshold, text

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    with st.spinner('বিশ্লেষণ চলছে...'):
        mp, sharp, noise, n_limit, text = advanced_audit(img_array, image)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True)

    with col2:
        st.subheader("📊 টেকনিক্যাল রিপোর্ট")
        
        fail_reasons = []
        if mp < 4.0: fail_reasons.append(f"রেজোলিউশন কম ({mp:.2f}MP)")
        if sharp < 12: fail_reasons.append("ছবিটি অতিরিক্ত ঝাপসা (No focal point)")
        if noise > n_limit: fail_reasons.append(f"অতিরিক্ত নয়েজ/গ্রেইন ({noise:.2f})")
        if len(text) > 4: fail_reasons.append(f"লোগো বা টেক্সট ডিটেক্ট হয়েছে: {text[:10]}")

        if not fail_reasons:
            st.markdown('<div class="pass-card">✅ এই ছবিটি Adobe Stock-এ অ্যাপ্রুভ হওয়ার জন্য একদম পারফেক্ট!</div>', unsafe_allow_html=True)
            st.balloons()
        else:
            st.markdown('<div class="fail-card">🛑 রিজেকশন রিস্ক আছে!</div>', unsafe_allow_html=True)
            for r in fail_reasons: st.write(f"- {r}")

        st.subheader("🎨 Master Re-Creation AI Prompt")
        st.write("এই স্টাইলের পারফেক্ট ছবি আবার জেনারেট করতে এই প্রম্পটটি ব্যবহার করুন:")
        
        # স্মার্ট প্রম্পট জেনারেটর
        style = "night photography, cinematic lighting, high contrast" if n_limit > 7 else "commercial stock photography, clean studio lighting, sharp focus, 8k"
        m_prompt = f"Professional {style}, [SUBJECT HERE], high-end optics, f/1.8, master composition, no text, no logo, commercially ready --ar 16:9 --v 6.0"
        
        st.markdown(f'<div class="prompt-box">{m_prompt}</div>', unsafe_allow_html=True)
        st.caption("নির্দেশ: [SUBJECT HERE] এর জায়গায় ছবির মূল বিষয়বস্তু লিখুন।")
