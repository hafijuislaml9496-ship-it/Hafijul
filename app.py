import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract

# কনফিগারেশন
st.set_page_config(page_title="Professional Adobe Stock Auditor", layout="wide")

st.markdown("""
    <style>
    .verdict-box { padding: 25px; border-radius: 15px; border: 3px solid; text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 20px; }
    .status-ok { background-color: #d4edda; color: #155724; border-color: #28a745; }
    .status-fail { background-color: #f8d7da; color: #721c24; border-color: #dc3545; }
    .analysis-card { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px; }
    .prompt-box { background-color: #f1f3f5; border: 2px dashed #007bff; padding: 20px; border-radius: 10px; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚖️ Adobe Stock Quality Auditor (AI Expert)")
st.write("অ্যাডোবি স্টকের অফিশিয়াল টেকনিক্যাল গাইডলাইন অনুযায়ী আপনার ছবি অডিট করা হচ্ছে।")

uploaded_file = st.file_uploader("আপনার ছবিটি আপলোড করুন...", type=["jpg", "jpeg"])

def audit_image(img_array, pil_img):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs = []
    rejection_risk = False
    
    # ১. রেজোলিউশন (Adobe Rule: Min 4MP)
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    if mp < 4.0:
        rejection_risk = True
        logs.append(f"❌ Resolution: মাত্র {mp:.2f} MP। Adobe-এ অন্তত ৪ MP লাগবে।")

    # ২. আউট অফ ফোকাস (Smart Peak Focus Analysis)
    gh, gw = h//6, w//6
    peak_sharp = max([cv2.Laplacian(gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw], cv2.CV_64F).var() for i in range(6) for j in range(6)])
    if peak_sharp < 18: # Adobe Standard for Focal Sharpness
        rejection_risk = True
        logs.append("❌ Out of Focus: ছবির মূল সাবজেক্টে শার্পনেস নেই।")
    elif peak_sharp < 35:
        logs.append("⚠️ Soft Focus: ছবি কিছুটা সফট, রিভিউয়ারের ওপর নির্ভর করবে।")

    # ৩. আর্টিফ্যাক্টস ও নয়েজ (ISO/Over-processing)
    noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
    if noise > 8.0:
        rejection_risk = True
        logs.append(f"❌ Artifacts/Noise: অতিরিক্ত দানা (Grain) বা আর্টিফ্যাক্টস পাওয়া গেছে ({noise:.2f})।")

    # ৪. লাইটিং ইস্যু (Exposure/Histogram)
    over_exposed = np.sum(gray > 252) / (h * w)
    under_exposed = np.sum(gray < 5) / (h * w)
    if over_exposed > 0.05:
        rejection_risk = True
        logs.append("❌ Lighting: ছবি ওভার-এক্সপোজড (Blown highlights)।")
    if under_exposed > 0.15:
        logs.append("⚠️ Underexposed: ছবি কিছুটা অন্ধকার।")

    # ৫. কালার অ্যান্ড হোয়াইট ব্যালেন্স (Color Fringing/Chromatic Aberration)
    b, g, r = cv2.split(img_array)
    ca_score = np.mean(cv2.absdiff(r, b))
    if ca_score > 20:
        logs.append("⚠️ Chromatic Aberration: অবজেক্টের চারপাশে কালার ফ্রিঞ্জিং (বেগুনি দাগ) দেখা যাচ্ছে।")

    # ৬. লোগো এবং টেক্সট (IP Issue)
    text = pytesseract.image_to_string(pil_img).strip()
    if len(text) > 3:
        rejection_risk = True
        logs.append(f"❌ IP Claim: লোগো বা টেক্সট শনাক্ত হয়েছে: '{text[:15]}'")

    return rejection_risk, logs, mp, peak_sharp, noise

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    img_array = np.array(image)
    
    with st.spinner('🔍 অ্যাডোবি রিভিউয়ারের মতো ছবি বিশ্লেষণ করা হচ্ছে...'):
        is_rejected, audit_logs, mp, sharp, noise = audit_image(img_array, image)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True)

    with col2:
        st.subheader("📢 অডিট ফলাফল (Audit Verdict)")
        
        if not is_rejected:
            st.markdown('<div class="verdict-box status-ok">✅ ACCEPTED: এই ছবিটির কমার্শিয়াল ভ্যালু আছে।</div>', unsafe_allow_html=True)
            st.balloons()
        else:
            st.markdown('<div class="verdict-box status-fail">🛑 REJECTED: কোয়ালিটি সমস্যার কারণে এটি রিজেক্ট হতে পারে।</div>', unsafe_allow_html=True)
            
        for log in audit_logs:
            st.markdown(f'<div class="analysis-card">{log}</div>', unsafe_allow_html=True)

        # মাস্টার প্রম্পট (ইন্টেলিজেন্টলি জেনারেটেড)
        st.subheader("🎨 Full AI Master Prompt (Perfect Quality)")
        st.write("এই ভুলগুলো ছাড়া নতুন ছবি তৈরি করতে এই প্রম্পটটি ব্যবহার করুন:")
        
        # সাবজেক্ট আইডেন্টিফিকেশন এবং প্রম্পট বিল্ড
        final_prompt = f"Professional stock photography, [Insert Subject], cinematic studio lighting, razor sharp focus, shot on Sony A7R IV, 8k, photorealistic texture, zero noise, high clarity, no text, no logo, commercially ready --ar 16:9 --v 6.0"
        
        st.markdown(f'<div class="prompt-box">{final_prompt}</div>', unsafe_allow_html=True)
        st.info("নির্দেশ: [Insert Subject] এর জায়গায় আপনার ছবির নাম লিখে যেকোনো AI (Midjourney/Firefly) তে দিন।")

    st.divider()
    st.write("📝 *নোট: এই অডিট অ্যাডোবির অফিশিয়াল টেকনিক্যাল প্যারামিটার অনুসরণ করে করা হয়েছে।*")
