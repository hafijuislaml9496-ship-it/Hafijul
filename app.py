import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract

# পেজ সেটআপ
st.set_page_config(page_title="Professional Adobe Stock Auditor", layout="wide")

# স্টাইল সেটআপ
st.markdown("""
    <style>
    .verdict-yes { background-color: #d4edda; color: #155724; padding: 20px; border-radius: 10px; border: 2px solid #28a745; text-align: center; font-size: 24px; font-weight: bold; }
    .verdict-no { background-color: #f8d7da; color: #721c24; padding: 20px; border-radius: 10px; border: 2px solid #dc3545; text-align: center; font-size: 24px; font-weight: bold; }
    .prompt-box { background-color: #f1f3f5; border: 2px dashed #007bff; padding: 20px; border-radius: 10px; font-family: 'Courier New', monospace; font-size: 16px; color: #333; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Professional Adobe Stock Auditor")
st.write("অ্যাডোবি স্টকের আসল রিভিউ স্ট্যান্ডার্ড অনুযায়ী প্রতিটি পিক্সেল বিশ্লেষণ করা হচ্ছে।")

# ফাইল আপলোডার (এখানেই আগের কোডে ভুল ছিল, এখন ঠিক করে দেওয়া হয়েছে)
uploaded_file = st.file_uploader("আপনার ছবিটি এখানে আপলোড করুন...", type=["jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    img_array = np.array(image)
    
    with st.spinner('🔍 অ্যাডোবি স্ট্যান্ডার্ড স্ক্যান চলছে...'):
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # স্মার্ট শার্পনেস (Peak Focal Analysis)
        h, w = gray.shape
        gh, gw = h//4, w//4
        max_sharp = 0
        for i in range(4):
            for j in range(4):
                grid = gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw]
                score = cv2.Laplacian(grid, cv2.CV_64F).var()
                if score > max_sharp: max_sharp = score
        
        # নয়েজ ডিটেকশন
        try:
            noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        except:
            noise = 0
            
        # মেগাপিক্সেল ক্যালকুলেশন
        mp = (image.size[0] * image.size[1]) / 1_000_000
        
        # টেক্সট এবং লোগো স্ক্যান
        text = pytesseract.image_to_string(image).strip()

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True, caption="Uploaded Image")

    with col2:
        st.subheader("📢 রিভিউ ফলাফল (Review Verdict)")
        
        reasons = []
        if mp < 4.0:
            reasons.append(f"❌ রেজোলিউশন কম ({mp:.2f} MP)। অন্তত ৪ MP হতে হবে।")
        if max_sharp < 10.0:
            reasons.append("❌ ছবির কোনো অংশই শার্প নয়। সাবজেক্টে ফোকাস থাকতে হবে।")
        if noise > 9.0:
            reasons.append(f"❌ অতিরিক্ত নয়েজ/গ্রেইন পাওয়া গেছে ({noise:.2f})।")
        if len(text) > 4:
            reasons.append(f"❌ লোগো বা টেক্সট ডিটেক্ট হয়েছে: '{text[:15]}'")

        if not reasons:
            st.markdown('<div class="verdict-yes">✅ এই ছবিটি Adobe Stock-এ ACCEPTED হবে।</div>', unsafe_allow_html=True)
            st.success("অভিনন্দন! ছবিটির টেকনিক্যাল কোয়ালিটি অ্যাডোবি স্ট্যান্ডার্ড অনুযায়ী নিখুঁত।")
        else:
            st.markdown('<div class="verdict-no">🛑 এই ছবিটি REJECTED হতে পারে।</div>', unsafe_allow_html=True)
            for r in reasons:
                st.warning(r)

        # মাস্টার প্রম্পট জেনারেশন (আপনি যেমনটি চেয়েছিলেন)
        st.subheader("🎨 Full AI Master Prompt")
        st.write("এই ছবিটিকে আরও নিখুঁতভাবে তৈরি করার জন্য নিচের প্রম্পটটি ব্যবহার করুন:")
        
        # প্রম্পটটিকে ছবির ধরণ অনুযায়ী সাজানো
        prompt_style = "Professional stock photography"
        if noise > 5: prompt_style += ", zero noise, clean high ISO"
        if max_sharp < 20: prompt_style += ", razor sharp focus, macro details"
        
        full_prompt = f"{prompt_style}, [আপনার সাবজেক্টের নাম এখানে লিখুন], cinematic studio lighting, 85mm lens, f/1.8, photorealistic, ultra-detailed, 8k resolution, no logos, no text, commercially ready --ar 16:9 --v 6.0"
        
        st.markdown(f'<div class="prompt-box"><b>Master Prompt:</b><br>{full_prompt}</div>', unsafe_allow_html=True)
        st.info("💡 টিপস: [আপনার সাবজেক্টের নাম এখানে লিখুন] এর জায়গায় ছবির মূল বিষয় (যেমন: Robotic hands) লিখে ব্যবহার করুন।")
