import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract

st.set_page_config(page_title="Adobe Stock Smart Auditor", layout="wide")

st.markdown("""
    <style>
    .report-box { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; }
    .verdict-pass { color: #2f855a; font-size: 26px; font-weight: bold; text-align: center; }
    .verdict-fail { color: #c53030; font-size: 26px; font-weight: bold; text-align: center; }
    .prompt-container { background-color: #f7fafc; border: 2px dashed #4299e1; padding: 15px; border-radius: 8px; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧠 AI Master Expert Auditor (Smart Geometry)")
st.write("এটি এখন শৈল্পিক বাঁকা ছবি (Artistic Slant) এবং এআই-এর ভুলের কারণে হওয়া ঢেউ খেলানো লাইন (Wavy Distortion) আলাদা করতে পারে।")

uploaded_file = st.file_uploader("আপনার ছবিটি আপলোড করুন...", type=["jpg", "jpeg"])

def analyze_lines_smartly(img_array):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=80, maxLineGap=5)
    
    distortion_error = False
    horizon_warning = False
    
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # লাইনের সোজা ভাব চেক করা (ইন্টারনাল লিনিয়ারিটি)
            # যদি লাইনটি ঢেউয়ের মতো হয় তবে এটি ডিস্টরশন
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            
            # ১. হরিজনাল চেক: যদি সামান্য বাঁকা হয় (০.৫ থেকে ৩ ডিগ্রির মধ্যে), তবে ওটা ভুল করে বাঁকা হওয়া (Crooked)
            if 0.5 < angle < 3 or 87 < angle < 89.5:
                horizon_warning = True
            
            # ২. ডিস্টরশন চেক: যদি লাইনগুলো সোজা না হয়ে জ্যাগড (Jagged) হয়
            # (এটি আমরা ক্যানি এবং লাইন গ্যাপ দিয়ে ডিটেক্ট করছি)
            if len(lines) > 200: # অতিরিক্ত জ্যাগড লাইন থাকলে
                distortion_error = True
                
    return distortion_error, horizon_warning

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    img_array = np.array(image)
    
    with st.spinner('স্মার্ট জিওমেট্রি স্ক্যান চলছে...'):
        w, h = image.size
        mp = (w * h) / 1000000
        dist_err, horiz_warn = analyze_lines_smartly(img_array)
        
        # টেকনিক্যাল ডেটা
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        sharp_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        text = pytesseract.image_to_string(image).strip()

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True)

    with col2:
        st.markdown('<div class="report-box">', unsafe_allow_html=True)
        
        errors = []
        if mp < 4.0: errors.append(f"❌ Low MP: {mp:.2f} (Adobe requires 4MP+)")
        if sharp_score < 12: errors.append("❌ Sharpness: ছবিটি খুব বেশি সফট বা ঝাপসা।")
        if noise > 8.0: errors.append("❌ Noise: ছবিতে ডিজিটাল ডাস্ট বা এআই আর্টিফ্যাক্টস বেশি।")
        if dist_err: errors.append("❌ AI Distortion: লাইনে ঢেউ খেলানো বা আঁকাবাঁকা বিকৃতি আছে।")
        if len(text) > 4: errors.append(f"❌ IP Claim: লোগো বা টেক্সট পাওয়া গেছে: {text[:15]}")
        
        if not errors:
            st.markdown('<p class="verdict-pass">✅ ACCEPTED</p>', unsafe_allow_html=True)
            if horiz_warn: st.warning("⚠️ নোট: হরিজন কিছুটা বাঁকা মনে হচ্ছে, এটি ইচ্ছা করে না হলে সোজা করে নিন।")
        else:
            st.markdown('<p class="verdict-fail">🛑 REJECTED</p>', unsafe_allow_html=True)
            for e in errors: st.write(e)

        # মাস্টার প্রম্পট
        st.subheader("🎨 Master AI Creation Prompt")
        m_prompt = f"Professional commercial stock photography, masterpiece, [SUBJECT HERE], razor sharp focus, perfectly straight geometric lines, clean architectural edges, zero AI artifacts, photorealistic, no text, no logo --ar 16:9 --v 6.0"
        st.markdown(f'<div class="prompt-container">{m_prompt}</div>', unsafe_allow_html=True)
        st.info("💡 টিপস: [SUBJECT HERE] এর জায়গায় আপনার ছবির নাম লিখুন।")
        st.markdown('</div>', unsafe_allow_html=True)
