import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract

# কনফিগারেশন
st.set_page_config(page_title="Adobe Stock Auditor + Solver", layout="wide")

st.markdown("""
    <style>
    .solve-prompt { 
        background-color: #f0f7ff; 
        border-left: 5px solid #007bff; 
        padding: 15px; 
        margin-top: 10px; 
        font-family: 'Courier New', Courier, monospace;
        color: #0056b3;
    }
    .problem-box { color: #d9534f; font-weight: bold; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Adobe Stock Auditor & AI Solver")
st.write("ছবি আপলোড করুন। সমস্যা থাকলে আমরা সেটির সরাসরি সমাধানের জন্য এআই প্রম্পট দিয়ে দেব।")

uploaded_file = st.file_uploader("আপনার ছবিটি আপলোড করুন...", type=["jpg", "jpeg"])

# ফেস ডিটেকশন মডেল
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.py')

def analyze_and_solve(img_array, pil_img):
    analysis = []
    
    # ১. রেজোলিউশন
    w, h = pil_img.size
    mp = (w * h) / 1000000
    if mp < 4.0:
        analysis.append({
            "problem": f"রেজোলিউশন অত্যন্ত কম ({mp:.2f}MP)।",
            "fix": "Photoshop/AI Prompt: 'Upscale this image by 200% using Preserve Details 2.0 or AI Super Resolution to reach 4000px width.'"
        })

    # ২. শার্পনেস ও ফোকাস
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
    if sharpness < 35:
        analysis.append({
            "problem": "ছবিটি সামান্য ঝাপসা (Out of Focus)।",
            "fix": "Lightroom/Photoshop Prompt: 'Apply Unsharp Mask: Amount 100%, Radius 1.0, Threshold 0' OR use 'Topaz Sharpen AI' to recover focus."
        })

    # ৩. নয়েজ ডিটেকশন
    noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
    if noise > 5.0:
        analysis.append({
            "problem": "ছবিতে নয়েজ বা দানা (Grain) বেশি পাওয়া গেছে।",
            "fix": "Lightroom Prompt: 'Increase Luminance Noise Reduction to 40, Detail to 50, and Contrast to 10.'"
        })

    # ৪. লোগো ও টেক্সট ডিটেকশন
    text = pytesseract.image_to_string(pil_img).strip()
    if len(text) > 2:
        analysis.append({
            "problem": f"ছবিতে টেক্সট বা লোগো পাওয়া গেছে: '{text[:20]}...'",
            "fix": f"Photoshop Generative Fill Prompt: 'Select the area with text \"{text[:10]}\" and use Generative Fill with: \"Remove the logo and text, fill with background content-aware blend\".'"
        })

    # ৫. ক্রোম্যাটিক অ্যাবারেশন (Lens Fringe)
    b, g, r = cv2.split(img_array)
    if np.mean(cv2.absdiff(r, g)) > 18:
        analysis.append({
            "problem": "কালার ফ্রিঞ্জিং (বেগুনি বর্ডার) পাওয়া গেছে।",
            "fix": "Camera Raw Prompt: 'Go to Optics Tab -> Defringe -> Increase Purple Amount to 5 and Green Amount to 5.'"
        })

    return analysis

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    with st.spinner('🔍 এআই প্রতিটি পিক্সেল বিশ্লেষণ করছে...'):
        results = analyze_and_solve(img_array, image)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, use_column_width=True, caption="স্ক্যান করা ছবি")

    with col2:
        st.subheader("📢 অডিট রিপোর্ট ও সমাধান")
        
        if not results:
            st.success("✅ অভিনন্দন! ছবিতে কোনো সমস্যা পাওয়া যায়নি। এটি সরাসরি আপলোড করতে পারেন।")
            st.balloons()
        else:
            st.error(f"🛑 {len(results)}টি সমস্যা পাওয়া গেছে। নিচে সমাধানের প্রম্পট দেওয়া হলো:")
            
            for item in results:
                st.markdown(f'<div class="problem-box">{item["problem"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="solve-prompt"><b>Solve Prompt:</b><br>{item["fix"]}</div>', unsafe_allow_html=True)
                st.button(f"Copy Prompt for: {item['problem'][:15]}", on_click=lambda t=item['fix']: st.write(f"Copied: {t}")) # সিম্পল কপি ইন্ডিকেশন

    st.divider()
    st.info("💡 টিপস: উপরের প্রম্পটগুলো কপি করে আপনার এডিটিং সফটওয়্যারে ব্যবহার করলে রিজেকশন রিস্ক ০% হয়ে যাবে।")
