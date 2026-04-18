import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract

st.set_page_config(page_title="Adobe Stock Real Auditor", layout="wide")

st.markdown("""
    <style>
    .pass-box { background-color: #d4edda; color: #155724; padding: 20px; border-radius: 10px; border: 2px solid #28a745; text-align: center; font-size: 24px; font-weight: bold; }
    .risk-box { background-color: #fff3cd; color: #856404; padding: 20px; border-radius: 10px; border: 2px solid #ffc107; text-align: center; font-size: 24px; font-weight: bold; }
    .fail-box { background-color: #f8d7da; color: #721c24; padding: 20px; border-radius: 10px; border: 2px solid #dc3545; text-align: center; font-size: 24px; font-weight: bold; }
    .prompt-box { background-color: #f1f3f5; border: 2px dashed #007bff; padding: 20px; border-radius: 10px; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Adobe Stock Real Auditor (Strict Mode)")
st.write("এটি এখন অ্যাডোবির 'কোয়ালিটি রিজেকশন' এড়াতে ১০০% জুম লেভেলের কোয়ালিটি চেক করবে।")

uploaded_file = st.file_uploader("আপনার ছবিটি এখানে দিন...", type=["jpg", "jpeg"])

def analyze_quality(img_array, pil_img):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # ১. হাই-রেজোলিউশন শার্পনেস অ্যানালাইসিস (Strict)
    # আমরা ছবিকে বড় গ্রিডে ভাগ করে সর্বোচ্চ শার্পনেস মেপে দেখব
    h, w = gray.shape
    gh, gw = h//4, w//4
    max_sharp = 0
    for i in range(4):
        for j in range(4):
            grid = gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw]
            score = cv2.Laplacian(grid, cv2.CV_64F).var()
            if score > max_sharp: max_sharp = score
    
    # ২. এক্সপোজার চেক (Highlights check)
    over_exposed = np.sum(gray > 250) / (h * w)
    
    # ৩. নয়েজ এবং ফিল্টারিং চেক (Artifacts)
    noise_sigma = np.mean(estimate_sigma(img_array, channel_axis=-1))
    
    # ৪. টেক্সট/লোগো
    text = pytesseract.image_to_string(pil_img).strip()
    
    # ৫. রেজোলিউশন
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    
    return mp, max_sharp, noise_sigma, over_exposed, text

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    img_array = np.array(image)
    
    with st.spinner('অ্যাডোবি গাইডলাইন অনুযায়ী ছবি বিশ্লেষণ করা হচ্ছে...'):
        mp, sharp, noise, expo, text = analyze_quality(img_array, image)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True)

    with col2:
        st.subheader("📢 চূড়ান্ত অডিট রিপোর্ট")
        
        errors = []
        warnings = []
        
        # কঠোর নিয়মাবলি (Strict Adobe Rules)
        if mp < 4.0:
            errors.append(f"🛑 রেজোলিউশন কম ({mp:.2f} MP)। অন্তত ৪ MP হতে হবে।")
        
        if sharp < 45.0: # আগে এটি ১০ ছিল, এখন ৪৫ করা হয়েছে কারণ অ্যাডোবি খুব শার্প ছবি চায়
            errors.append(f"🛑 Soft Focus: ছবিটি যথেষ্ট শার্প নয়। জুম করলে ডিটেইলস হারিয়ে যাচ্ছে।")
        elif sharp < 70.0:
            warnings.append("⚠️ সামান্য ঝাপসা (Soft focus risk)। রিজেক্ট হওয়ার সম্ভাবনা আছে।")
            
        if expo > 0.05: # যদি ছবির ৫% এর বেশি অংশ পুড়ে যায় (Overexposed)
            errors.append("🛑 Exposure Issue: ছবির কিছু অংশ অতিরিক্ত উজ্জ্বল বা জ্বলে গেছে।")
            
        if noise > 6.0:
            errors.append(f"🛑 Excessive Filtering/Noise: ছবিতে ডিজিটাল ত্রুটি বা ওয়াক্সি টেক্সচার আছে।")
            
        if len(text) > 4:
            errors.append(f"🛑 লোগো বা টেক্সট ডিটেক্ট হয়েছে: '{text[:15]}'")

        # ফলাফল প্রদর্শন
        if not errors and not warnings:
            st.markdown('<div class="pass-box">✅ এই ছবিটি Adobe Stock-এ ACCEPTED হওয়ার যোগ্য।</div>', unsafe_allow_html=True)
            st.success("টেকনিক্যাল কোয়ালিটি নিখুঁত।")
            st.balloons()
        elif not errors and warnings:
            st.markdown('<div class="risk-box">⚠️ সতর্কবার্তা: রিজেকশন রিস্ক আছে!</div>', unsafe_allow_html=True)
            for w in warnings: st.warning(w)
        else:
            st.markdown('<div class="fail-box">❌ এই ছবিটি REJECTED হবে।</div>', unsafe_allow_html=True)
            for e in errors: st.error(e)

        # মাস্টার প্রম্পট
        st.subheader("🎨 Full Master AI Prompt (To fix issues)")
        st.write("এই ভুলগুলো সংশোধন করে নতুন ছবি বানাতে এই প্রম্পটটি ব্যবহার করুন:")
        m_prompt = f"Professional stock photography of [Insert Subject], photorealistic, razor sharp focus on eyes, perfect exposure, balanced lighting, zero noise, high detail skin texture, shot on Sony A7R IV, 8k, commercially clean --ar 16:9 --v 6.0"
        st.markdown(f'<div class="prompt-box">{m_prompt}</div>', unsafe_allow_html=True)
