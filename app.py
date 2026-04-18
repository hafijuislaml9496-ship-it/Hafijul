import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import torch
from torchvision import models, transforms

# ১. এআই মডেল লোড (স্মার্টলি সাবজেক্ট চেনার জন্য)
@st.cache_resource
def load_expert_ai():
    # সাবজেক্ট চেনার জন্য মোবাইলনেট মডেল
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    model.eval()
    return model

classifier = load_expert_ai()

# ২. ইউনিক প্রম্পট তৈরির ফাংশন (Subject Identify করে)
def generate_master_prompt(image, score, logs):
    preprocess = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    input_tensor = preprocess(image).unsqueeze(0)
    
    with torch.no_grad():
        output = classifier(input_tensor)
    _, index = torch.max(output, 1)
    
    # ইনডেক্স অনুযায়ী সাবজেক্ট ক্যাটাগরি ঠিক করা (যাতে ইন্টারনেট থেকে নাম ডাউনলোড করতে না হয়)
    idx = index.item()
    if idx <= 397: subj = "Professional Portrait/Person"
    elif 398 <= idx <= 500: subj = "Animal/Wildlife"
    elif 501 <= idx <= 900: subj = "Commercial Object/Product"
    else: subj = "Scenic Landscape/Architecture"

    # কোয়ালিটি ট্যাগ যোগ করা
    q_tags = "razor sharp focus, cinematic lighting, masterpiece, highly detailed, 8k resolution"
    if score < 80: q_tags += ", extreme clarity, ultra-clean textures"
    
    prompt = f"Professional stock photography of {subj}, {q_tags}, photorealistic, no text, no logo, commercially ready, shot on Sony A7R IV --ar 16:9 --v 6.0"
    return prompt, subj

# ৩. অ্যাডোবি স্ট্যান্ডার্ড অডিট লজিক
def deep_audit(img_array, pil_img):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs, score = [], 100
    
    # রেজোলিউশন চেক
    mp = (pil_img.size[0] * pil_img.size[1]) / 1_000_000
    if mp < 4.0:
        score -= 40
        logs.append(f"❌ Low MP ({mp:.2f})")
    
    # স্মার্ট শার্পনেস চেক
    gh, gw = h//6, w//6
    peak_sharp = max([cv2.Laplacian(gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw], cv2.CV_64F).var() for i in range(6) for j in range(6)])
    if peak_sharp < 42:
        score -= 35
        logs.append("❌ Soft Focus")
    
    # নয়েজ চেক
    try:
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        if noise > 6.0:
            score -= 20
            logs.append("❌ High Noise")
    except: pass
    
    # লোগো/টেক্সট চেক
    text = pytesseract.image_to_string(pil_img).strip()
    if len(text) > 3:
        score -= 60
        logs.append("❌ Logo Detected")
        
    return score, logs

# ৪. মেইন অ্যাপ ইন্টারফেস
st.set_page_config(page_title="Adobe Stock Master Auditor", layout="wide")

st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Bulk Adobe Stock Master Auditor (Pro)")
uploaded_files = st.file_uploader("আপনার ছবিগুলো আপলোড করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        image = Image.open(uploaded_file).convert('RGB')
        img_array = np.array(image)
        
        score, logs = deep_audit(img_array, image)
        unique_prompt, category = generate_master_prompt(image, score, logs)
        
        col1, col2, col3, col4 = st.columns([1, 3, 1.5, 1])
        with col1:
            thumb = image.copy()
            thumb.thumbnail((120, 120))
            st.image(thumb)
        with col2:
            st.write(f"**{uploaded_file.name}**")
            st.caption(f"Category: {category}")
            st.write(", ".join(logs) if logs else "✅ Quality: Perfect")
        with col3:
            if score >= 85: st.markdown('<span class="status-pass">ACCEPTED</span>', unsafe_allow_html=True)
            else: st.markdown('<span class="status-fail">REJECTED</span>', unsafe_allow_html=True)
            st.write(f"Score: **{score}%**")
        with col4:
            with st.popover("AI Prompt"):
                st.write(f"**Master Prompt for {category}:**")
                st.code(unique_prompt, language="text")
        st.divider()
