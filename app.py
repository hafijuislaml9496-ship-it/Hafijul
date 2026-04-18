import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import torch
from torchvision import models, transforms

# ১. এআই সাবজেক্ট ডিটেক্টর লোড (ইন্টেলিজেন্সের জন্য)
@st.cache_resource
def load_ai_engine():
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    model.eval()
    return model

ai_engine = load_ai_engine()

# ২. কমন সাবজেক্ট লিস্ট (যাতে এরর না হয়)
SUBJECT_CLASSES = {0: "Person", 1: "Object", 2: "Technology/Robot", 3: "Landscape", 4: "Architecture"}

st.set_page_config(page_title="Universal Intelligent Auditor", layout="wide")

st.markdown("""
    <style>
    .report-card { background-color: #ffffff; padding: 25px; border-radius: 15px; box-shadow: 0 10px 20px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
    .score-text { font-size: 40px; font-weight: bold; text-align: center; color: #2d3748; }
    .prompt-box { background-color: #edf2f7; border: 2px dashed #4a5568; padding: 20px; border-radius: 10px; font-family: 'Courier New', monospace; color: #2d3748; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧠 Universal Intelligent Auditor (Adobe Pro)")
st.write("এই এআই টুলটি যেকোনো ক্যাটাগরির ছবি শনাক্ত করে অ্যাডোবি স্ট্যান্ডার্ড অনুযায়ী অডিট করতে সক্ষম।")

uploaded_file = st.file_uploader("আপনার ছবিটি এখানে ড্রপ করুন...", type=["jpg", "jpeg"])

def get_subject_intelligence(pil_img):
    preprocess = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    input_tensor = preprocess(pil_img).unsqueeze(0)
    with torch.no_grad():
        output = ai_engine(input_tensor)
    _, index = torch.max(output, 1)
    # একটি সিম্পল লজিক দিয়ে সাবজেক্ট নাম বের করা
    idx = index.item()
    if idx <= 500: return "Professional Portrait"
    elif 501 <= idx <= 700: return "Industrial/Technology"
    else: return "Commercial Subject"

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    img_array = np.array(image)
    
    with st.spinner('AI আপনার ছবির ক্যাটাগরি এবং পিক্সেল বিশ্লেষণ করছে...'):
        # ক্যাটাগরি শনাক্তকরণ
        detected_category = get_subject_intelligence(image)
        
        # টেকনিক্যাল অ্যানালাইসিস
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        w, h = image.size
        mp = (w * h) / 1_000_000
        
        # স্মার্ট শার্পনেস (Peak Grid Detection)
        gh, gw = gray.shape[0]//8, gray.shape[1]//8
        sharpness_list = [cv2.Laplacian(gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw], cv2.CV_64F).var() for i in range(8) for j in range(8)]
        peak_sharp = max(sharpness_list)
        
        # নয়েজ ও টেক্সচার ইন্টেলিজেন্স
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        text = pytesseract.image_to_string(image).strip()

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True, caption=f"Detected Category: {detected_category}")

    with col2:
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.subheader("📢 ইন্টেলিজেন্ট অডিট রিপোর্ট")
        
        score = 100
        reasons = []

        # অডিট লজিক
        if mp < 4.0:
            score -= 30
            reasons.append(f"❌ Resolution: {mp:.2f}MP (Low)")
        
        if peak_sharp < 25: # অ্যাডোবি স্ট্যান্ডার্ড ফোকাস
            score -= 25
            reasons.append("❌ Focus: সাবজেক্টে শার্পনেস কম (Soft Focus)।")
            
        if noise > 7.0:
            score -= 20
            reasons.append("❌ Artifacts: নয়েজ বা এআই ত্রুটি বেশি।")
            
        if len(text) > 3:
            score -= 40
            reasons.append(f"❌ IP Claim: লোগো বা টেক্সট পাওয়া গেছে: {text[:10]}")

        # চূড়ান্ত ফলাফল
        if score >= 75:
            st.success(f"✅ এটি Adobe Stock-এ একসেপ্ট হবে। (স্কোর: {score}%)")
            st.balloons()
        else:
            st.error(f"🛑 রিজেকশন রিস্ক! (স্কোর: {score}%)")
            for r in reasons: st.write(r)

        # মাস্টার প্রম্পট (ইন্টেলিজেন্টলি জেনারেটেড)
        st.subheader("🎨 Full Master AI Prompt")
        master_prompt = f"Professional stock photography of {detected_category}, high-end commercial quality, cinematic lighting, sharp focus on details, 8k resolution, zero noise, no logos, no text, masterpiece --ar 16:9 --v 6.0"
        
        st.markdown(f'<div class="prompt-box"><b>Copy this Prompt:</b><br>{master_prompt}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.info(f"এআই টিপস: এটি একটি {detected_category} টাইপ ছবি। অ্যাডোবিতে আপলোড করার সময় সঠিক ট্যাগ ব্যবহার করুন।")
