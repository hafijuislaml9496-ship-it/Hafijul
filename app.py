import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
from scipy.ndimage import variance

# পেজ সেটআপ
st.set_page_config(page_title="AI Master Expert Auditor", layout="wide")

st.markdown("""
    <style>
    .report-card { background-color: #ffffff; padding: 25px; border-radius: 15px; border: 1px solid #cbd5e0; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .score-circle { font-size: 45px; font-weight: bold; text-align: center; color: #2d3748; padding: 20px; border: 6px solid; border-radius: 50%; width: 140px; margin: auto; }
    .error-tag { color: #c53030; font-weight: bold; padding: 5px 0; border-bottom: 1px solid #feb2b2; }
    .master-prompt { background-color: #ebf8ff; border: 2px dashed #4299e1; padding: 20px; border-radius: 10px; font-family: 'Segoe UI', sans-serif; line-height: 1.6; color: #2b6cb0; font-size: 17px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧠 AI Master Expert Auditor (Adobe Stock Edition)")
st.write("এটি আপনার ছবির প্রতিটি সূক্ষ্ম ভুল (আঁকাবাঁকা লাইন, অসম চোখ, বিকৃত আইকন বা টেক্সচার) শনাক্ত করে সরাসরি সমাধানের প্রম্পট দিবে।")

uploaded_file = st.file_uploader("আপনার ছবিটি স্ক্যান করুন...", type=["jpg", "jpeg"])

def audit_everything(img_array, pil_img):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs = []
    score = 100

    # ১. লাইন এবং জিওমেট্রি (আঁকাবাঁকা লাইন ডিটেকশন)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=50, maxLineGap=10)
    if lines is not None:
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            if angle > 2 and angle < 88: # একদম সোজা না এমন লাইন
                angles.append(angle)
        if len(angles) > 100:
            score -= 20
            logs.append("❌ Geometry Error: ছবির স্ট্রাকচারাল লাইনগুলো (যেমন জানালা বা ল্যাপটপ) আঁকাবাঁকা।")

    # ২. সিমেট্রি ও অ্যানাটমি (অসম চোখ বা মুখমণ্ডল)
    left_side = gray[:, :w//2]
    right_side = cv2.flip(gray[:, w//2:], 1)
    right_side = cv2.resize(right_side, (left_side.shape[1], left_side.shape[0]))
    sym_diff = np.abs(left_side.astype(float) - right_side.astype(float)).mean()
    if sym_diff > 45:
        score -= 20
        logs.append("❌ Anatomical Error: মানুষের মুখ বা অবজেক্টের দুই পাশে অসামঞ্জস্যতা (Symmetry issue) আছে।")

    # ৩. আর্টিফ্যাক্টস ও ব্যান্ডিং (Banding/Noise)
    noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
    if noise > 5.5:
        score -= 15
        logs.append(f"❌ Artifacts: পিক্সেল লেভেলে ডিজিটাল নয়েজ বা এআই বিকৃতি পাওয়া গেছে ({noise:.2f})।")

    # ৪. লাইটিং এবং ব্লুউন হাইলাইটস
    over_exposed = np.sum(gray > 252) / (h * w)
    if over_exposed > 0.05:
        score -= 15
        logs.append("❌ Lighting Issue: ছবির কিছু অংশ অতিরিক্ত উজ্জ্বল বা জ্বলে গেছে (Overexposed)।")

    # ৫. লোগো ও টেক্সট ডিটেকশন
    text = pytesseract.image_to_string(pil_img).strip()
    if len(text) > 3:
        score -= 50
        logs.append(f"❌ IP Claim: লোগো বা টেক্সট শনাক্ত হয়েছে: '{text[:15]}'")

    return score, logs

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    img_array = np.array(image)
    
    with st.spinner('AI আপনার ছবির প্রতিটি পিক্সেল এবং বিষয়বস্তু বিশ্লেষণ করছে...'):
        final_score, audit_reports = audit_everything(img_array, image)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True, caption="Uploaded Image")

    with col2:
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        # স্কোর প্রদর্শন
        color = "#2f855a" if final_score >= 80 else "#c05621" if final_score >= 50 else "#c53030"
        st.markdown(f'<div class="score-circle" style="color: {color}; border-color: {color};">{max(final_score, 0)}</div>', unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-weight: bold;'>Acceptance Score: {max(final_score,0)}%</p>", unsafe_allow_html=True)

        st.subheader("📢 অডিট রিপোর্ট (Audit Report)")
        if not audit_reports:
            st.success("✅ অভিনন্দন! আপনার ছবিটি টেকনিক্যালি নিখুঁত।")
            st.balloons()
        else:
            for report in audit_reports:
                st.markdown(f'<div class="error-tag">{report}</div>', unsafe_allow_html=True)

        st.subheader("🎨 Master AI Correction Prompt")
        st.write("এই সব ভুলগুলো সংশোধন করে নিখুঁত ছবি তৈরি করতে এই প্রম্পটটি ব্যবহার করুন:")
        
        # মাস্টার প্রম্পট ইঞ্জিনিয়ারিং
        master_prompt = (
            "Professional stock photography, masterpiece quality, [Insert Subject Name], "
            "anatomically correct, perfectly symmetrical features, razor-sharp focus, "
            "mathematically straight architectural lines, perfectly formed icons and shapes, "
            "clean commercial lighting, zero artifacts, no noise, zero banding, "
            "high-end optics, f/1.8, no text, no logos, commercially ready, 8k resolution --ar 16:9 --v 6.0"
        )
        st.markdown(f'<div class="master-prompt">{master_prompt}</div>', unsafe_allow_html=True)
        st.info("💡 টিপস: [Insert Subject Name] এর জায়গায় ছবির নাম লিখে যেকোনো AI (Midjourney/DALL-E) তে ব্যবহার করুন।")
        st.markdown('</div>', unsafe_allow_html=True)
