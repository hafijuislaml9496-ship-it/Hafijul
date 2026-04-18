import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import torch
from torchvision import models, transforms

# সাবজেক্ট ডিটেকশন মডেল
@st.cache_resource
def load_expert_model():
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    model.eval()
    return model

expert_ai = load_expert_model()

# লেবেল লোড করা
import json
import requests
LABELS_URL = "https://raw.githubusercontent.com/pytorch/hub/master/imagenet_class_index.json"
labels = requests.get(LABELS_URL).json()

st.set_page_config(page_title="Professional Adobe Stock Auditor", layout="wide")

# স্টাইল সেটআপ
st.markdown("""
    <style>
    .verdict-yes { background-color: #d4edda; color: #155724; padding: 20px; border-radius: 10px; border: 2px solid #28a745; text-align: center; font-size: 24px; font-weight: bold; }
    .verdict-no { background-color: #f8d7da; color: #721c24; padding: 20px; border-radius: 10px; border: 2px solid #dc3545; text-align: center; font-size: 24px; font-weight: bold; }
    .ai-prompt { background-color: #f1f3f5; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6; font-family: 'Courier New', monospace; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Professional Adobe Stock Auditor")
st.write("অ্যাডোবি স্টকের আসল রিভিউ স্ট্যান্ডার্ড অনুযায়ী ছবি বিশ্লেষণ করা হচ্ছে।")

uploaded_file = st.file_uploader("আপনার ছবিটি এখানে দিন...", type=["jpg", "jpeg"])

def get_expert_verdict(img_array, pil_img):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # ১. স্মার্ট শার্পনেস (Peak Focal Analysis)
    # আমরা ছবিকে ১৬টি ভাগে ভাগ করে দেখব কোনো একটি ভাগও কি প্রফেশনাল লেভেলের শার্প?
    h, w = gray.shape
    gh, gw = h//4, w//4
    max_sharp = 0
    for i in range(4):
        for j in range(4):
            grid = gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw]
            score = cv2.Laplacian(grid, cv2.CV_64F).var()
            if score > max_sharp: max_sharp = score
            
    # ২. নয়েজ অ্যানালাইসিস
    noise_sigma = np.mean(estimate_sigma(img_array, channel_axis=-1))
    
    # ৩. সাবজেক্ট আইডেন্টিফিকেশন
    preprocess = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    input_batch = preprocess(pil_img).unsqueeze(0)
    with torch.no_grad():
        output = expert_ai(input_batch)
    _, index = torch.max(output, 1)
    subject = labels[str(index.item())][1].replace('_', ' ')
    
    # ৪. টেক্সট/লোগো ডিটেকশন
    text = pytesseract.image_to_string(pil_img).strip()
    
    return max_sharp, noise_sigma, subject, text

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    img_array = np.array(image)
    
    with st.spinner('🔍 অ্যাডোবি স্ট্যান্ডার্ড স্ক্যান চলছে...'):
        max_sharp, noise, subject, text = get_expert_verdict(img_array, image)
        width, height = image.size
        mp = (width * height) / 1_000_000

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True)

    with col2:
        st.subheader("📢 রিভিউ ফলাফল (Reviewer Verdict)")
        
        reasons = []
        if mp < 4.0: reasons.append(f"রেজোলিউশন খুব কম ({mp:.2f} MP)। অন্তত ৪ MP হতে হবে।")
        if max_sharp < 15.0: reasons.append("ছবির কোনো অংশই শার্প নয় (Soft Focus)। সাবজেক্টে ফোকাস থাকতে হবে।")
        if noise > 8.5: reasons.append(f"অতিরিক্ত টেকনিক্যাল নয়েজ/গ্রেইন ({noise:.2f})।")
        if len(text) > 4: reasons.append(f"লোগো বা টেক্সট ডিটেক্ট হয়েছে: '{text[:15]}'")

        if not reasons:
            st.markdown('<div class="verdict-yes">✅ এই ছবিটি Adobe Stock-এ ACCEPTED হবে।</div>', unsafe_allow_html=True)
            st.success(f"সবকিছু নিখুঁত। আপনার {subject} এর ছবিটির টেকনিক্যাল কোয়ালিটি চমৎকার।")
        else:
            st.markdown('<div class="verdict-no">🛑 এই ছবিটি REJECTED হতে পারে।</div>', unsafe_allow_html=True)
            for r in reasons: st.warning(r)

        # মাস্টার প্রম্পট জেনারেশন
        st.subheader("🎨 Full AI Master Prompt (Subject-Based)")
        st.write("এই বিষয়বস্তু দিয়ে নিখুঁত ছবি তৈরির প্রম্পট:")
        
        full_prompt = f"Professional stock photography of {subject}, high clarity, cinematic studio lighting, f/1.8, 85mm, incredibly detailed, sharp focus on subject, clean background, no text, no logo, commercially ready, 8k resolution --ar 16:9 --v 6.0"
        
        st.markdown(f'<div class="ai-prompt">{full_prompt}</div>', unsafe_allow_html=True)
        st.button("Copy Prompt", on_click=lambda: st.write("Prompt Copied to Clipboard!"))
