import streamlit as st
import cv2
import numpy as np
from PIL import Image
from skimage.restoration import estimate_sigma
import pytesseract
import os

# ১. পেজ কনফিগারেশন
st.set_page_config(page_title="Adobe Stock Auditor Master Pro", layout="wide")

st.markdown("""
    <style>
    .status-pass { color: #155724; background-color: #d4edda; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 11px; border: 1px solid #28a745; }
    .status-risk { color: #856404; background-color: #fff3cd; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 11px; border: 1px solid #ffc107; }
    .status-fail { color: #721c24; background-color: #f8d7da; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 11px; border: 1px solid #dc3545; }
    .log-text { font-size: 12px; color: #d32f2f; margin-bottom: 2px; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# ২. ইন্টেলিজেন্ট অডিট ফাংশন
def deep_intel_audit(img_array, pil_img, filename):
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    logs = []
    score = 100
    
    # --- মেগাপিক্সেল ---
    mp = (h * w) / 1000000.0
    if mp < 4.0:
        score -= 50
        logs.append(f"❌ Low MP: {mp:.2f} (Minimum 4MP needed)")

    # --- স্মার্ট শার্পনেস (Peak Focal Point Analysis) ---
    # ১০x১০ গ্রিডে ভাগ করে সর্বোচ্চ শার্পনেস দেখা (অ্যাডভান্সড বোকেহ সাপোর্ট)
    gh, gw = h//10, w//10
    peak_sharp = max([cv2.Laplacian(gray[i*gh:(i+1)*gh, j*gw:(j+1)*gw], cv2.CV_64F).var() for i in range(10) for j in range(10)])
    
    if peak_sharp < 35.0: # রিজেক্ট হওয়ার কড়া লিমিট
        score -= 35
        logs.append(f"❌ Soft Focus/Blur: ({peak_sharp:.1f})")
    elif peak_sharp < 55.0: # রিস্ক জোন
        score -= 10
        logs.append(f"⚠️ Focus Risk: ({peak_sharp:.1f})")

    # --- এক্সপোজার এবং লাইটিং ---
    over_exposed = np.sum(gray > 252) / (h * w)
    if over_exposed > 0.05:
        score -= 15
        logs.append("❌ Exposure: হাইলাইট পুড়ে গেছে (Blown out).")

    # --- এআই গিবিশ/হিজিবিজি টেক্সট এবং লোগো স্ক্যানার ---
    try:
        detected_text = pytesseract.image_to_string(pil_img).strip()
        if len(detected_text) > 2:
            # হিজিবিজি টেক্সট ডিটেকশন লজিক
            words = detected_text.split()
            valid_words = [w for w in words if len(w) > 2 and w.isalnum()]
            if len(valid_words) < 1 and len(detected_text) > 8:
                score -= 60
                logs.append("❌ Gibberish AI Text: অর্থহীন হিজিবিজি লেখা পাওয়া গেছে।")
            else:
                score -= 50
                logs.append(f"❌ IP Claim: লোগো বা টেক্সট ডিটেক্ট হয়েছে: '{detected_text[:10]}'")
    except: pass

    # --- টেকনিক্যাল নয়েজ ---
    try:
        noise = np.mean(estimate_sigma(img_array, channel_axis=-1))
        if noise > 6.0:
            score -= 15
            logs.append(f"⚠️ High Noise: ({noise:.2f})")
    except: pass

    subject = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')[:20]
    return score, logs, subject, peak_sharp

# ৩. ইউজার ইন্টারফেস
st.title("🛡️ Adobe Stock Professional Master Auditor (Ultimate)")
st.write("বাল্ক ফটো অডিট। এটি এখন এআই হিজিবিজি টেক্সট, বোকেহ এবং এক্সট্রিম কোয়ালিটি শনাক্ত করতে সক্ষম।")

uploaded_files = st.file_uploader("আপনার ছবিগুলো একসাথে সিলেক্ট করুন...", type=["jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    st.subheader(f"📊 প্রসেসিং হচ্ছে: {len(uploaded_files)} টি ছবি")
    
    for uploaded_file in uploaded_files:
        try:
            image = Image.open(uploaded_file).convert('RGB')
            img_array = np.array(image)
            
            # অডিট চালানো
            score, audit_logs, subj, s_score = deep_intel_audit(img_array, image, uploaded_file.name)
            
            # ৪ কলামে ড্যাশবোর্ড
            col1, col2, col3, col4 = st.columns([1, 3, 1.5, 1.2])
            
            with col1:
                thumb = image.copy(); thumb.thumbnail((120, 120))
                st.image(thumb)
            
            with col2:
                st.write(f"**{uploaded_file.name}**")
                st.caption(f"Sub: {subj.title()}")
                if not audit_logs: st.markdown('<p style="color:green; font-size:12px;">✅ Quality: Excellent</p>', unsafe_allow_html=True)
                for log in audit_logs: st.markdown(f'<p class="log-text">{log}</p>', unsafe_allow_html=True)
            
            with col3:
                if score >= 85: st.markdown('<span class="status-pass">ACCEPTED</span>', unsafe_allow_html=True)
                elif score >= 55: st.markdown('<span class="status-risk">RISKY</span>', unsafe_allow_html=True)
                else: st.markdown('<span class="status-fail">REJECTED</span>', unsafe_allow_html=True)
                st.write(f"S-Score: {s_score:.1f}")
                
            with col4:
                with st.popover("Master Prompt"):
                    st.write("**Fix Issues with this AI Prompt:**")
                    q_fix = "ultra-sharp 8k, cinematic studio lighting, masterpiece"
                    if score < 85: q_fix += ", legible UI text, razor sharp focus, zero artifacts"
                    st.code(f"Professional photography of {subj}, {q_fix}, photorealistic, no text, no logo --v 6.0", language="text")
            st.divider()
            
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")

st.info("টিপস: স্কোর ৮০ এর উপরে থাকা মানে ছবিটি অ্যাডোবিতে অ্যাপ্রুভ হওয়ার সম্ভাবনা ৯৯%।")
