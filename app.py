import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract

st.set_page_config(page_title="Super-Strict Adobe Auditor", layout="wide")

st.markdown("""
    <style>
    .verdict-box { padding: 30px; border-radius: 15px; border: 4px solid; text-align: center; font-size: 28px; font-weight: bold; margin-bottom: 20px; }
    .pass { background-color: #d4edda; color: #155724; border-color: #28a745; }
    .risk { background-color: #fff3cd; color: #856404; border-color: #ffc107; }
    .fail { background-color: #f8d7da; color: #721c24; border-color: #dc3545; }
    .analysis-card { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Adobe Stock Auditor (Super-Strict Mode)")
st.write("এটি এখন অত্যন্ত কঠোরভাবে প্রতিটি পিক্সেল স্ক্যান করবে। যদি এটি 'Accepted' বলে, তবেই আপনি ১০০% নিশ্চিন্ত হতে পারবেন।")

uploaded_file = st.file_uploader("আপনার ছবিটি আপলোড করুন...", type=["jpg", "jpeg"])

def deep_audit(img_array, pil_img):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs = []
    score = 100
    
    # ১. রেজোলিউশন (Hard Rule)
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    if mp < 4.0:
        score -= 40
        logs.append(f"❌ Resolution: মাত্র {mp:.2f} MP। (Adobe-এ অন্তত ৪ MP লাগে)")

    # ২. সুপার-স্ট্রিক্ট শার্পনেস (Peak Analysis)
    # আমরা ছবিকে ছোট গ্রিডে ভাগ করে সর্বোচ্চ শার্পনেস মেপে দেখব
    gh, gw = h//6, w//6
    peak_sharp = max([cv2.Laplacian(gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw], cv2.CV_64F).var() for i in range(6) for j in range(6)])
    
    if peak_sharp < 40: # অত্যন্ত কঠোর লিমিট
        score -= 35
        logs.append(f"❌ Soft Focus/Blur: জুম করলে ছবিটি ঝাপসা দেখাবে (Sharpness: {peak_sharp:.2f})")
    elif peak_sharp < 65:
        score -= 15
        logs.append(f"⚠️ Acceptable but Soft: রিজেক্ট হওয়ার সম্ভাবনা আছে।")

    # ৩. কন্ট্রাস্ট এবং ফিল্টারিং (Over-processing detection)
    contrast = gray.std()
    if contrast < 35:
        score -= 15
        logs.append("⚠️ Low Contrast: ছবিটা খুব ফ্যাকাশে বা ফ্ল্যাট।")
    if contrast > 90:
        score -= 15
        logs.append("⚠️ Excessive Filtering: ছবিটা অতিরিক্ত এডিট করা মনে হচ্ছে।")

    # ৪. আর্টিফ্যাক্টস এবং নয়েজ
    noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
    if noise > 6.0:
        score -= 20
        logs.append(f"❌ Artifacts/Noise: ছবিতে ডিজিটাল ত্রুটি বা দানা বেশি ({noise:.2f})।")

    # ৫. এক্সপোজার (Highlights clipping)
    over_exposed = np.sum(gray > 250) / (h * w)
    if over_exposed > 0.04:
        score -= 20
        logs.append("❌ Lighting Issue: ছবির গুরুত্বপূর্ণ অংশ অতিরিক্ত উজ্জ্বল (Blown out)।")

    # ৬. লোগো এবং টেক্সট
    text = pytesseract.image_to_string(pil_img).strip()
    if len(text) > 3:
        score -= 60
        logs.append(f"❌ Intellectual Property: লোগো বা টেক্সট পাওয়া গেছে: '{text[:15]}'")

    return score, logs

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    img_array = np.array(image)
    
    with st.spinner('🔍 অ্যাডোবি রিভিউয়ারের মতো কড়াভাবে বিশ্লেষণ করা হচ্ছে...'):
        final_score, audit_logs = deep_audit(img_array, image)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True)

    with col2:
        st.subheader("📢 অডিট স্কোর ও ফলাফল")
        
        # সিদ্ধান্ত প্রদর্শন
        if final_score >= 85:
            st.markdown(f'<div class="verdict-box pass">✅ ACCEPTED ({final_score}%)</div>', unsafe_allow_html=True)
            st.success("এই ছবিটি অ্যাডোবি স্টকের কঠোর কোয়ালিটি স্ট্যান্ডার্ড পূরণ করেছে।")
            st.balloons()
        elif final_score >= 55:
            st.markdown(f'<div class="verdict-box risk">⚠️ RISKY ({final_score}%)</div>', unsafe_allow_html=True)
            st.warning("ছবিটিতে কিছু সমস্যা আছে, রিজেক্ট হতে পারে।")
        else:
            st.markdown(f'<div class="verdict-box fail">🛑 REJECTED ({final_score}%)</div>', unsafe_allow_html=True)
            st.error("এই ছবিটি অ্যাডোবি কোনোভাবেই গ্রহণ করবে না।")
            
        for log in audit_logs:
            st.markdown(f'<div class="analysis-card">{log}</div>', unsafe_allow_html=True)

        # মাস্টার প্রম্পট
        st.subheader("🎨 Full AI Master Prompt (Perfect Quality)")
        m_prompt = f"Professional commercial stock photography, masterpiece, [Insert Subject], razor sharp focus on eyes/details, cinematic lighting, zero artifacts, ultra-realistic texture, 8k, no text, no logo --ar 16:9 --v 6.0"
        st.info(m_prompt)

    st.divider()
    st.write("📝 *টিপস: স্কোর ৮০ এর ওপর না থাকলে Adobe-এ আপলোড করবেন না।*")
