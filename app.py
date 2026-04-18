import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io
import base64
import tempfile
import os
import re
from datetime import datetime

st.set_page_config(page_title="Adobe Stock Auditor + Auto Sharpen", page_icon="✅", layout="wide")

st.markdown("""
<style>
.badge-pass { background-color: #00ff9d; color: #000; padding: 4px 12px; border-radius: 20px; font-weight: bold; display: inline-block; }
.badge-fail { background-color: #ff4444; color: #fff; padding: 4px 12px; border-radius: 20px; font-weight: bold; display: inline-block; }
</style>
""", unsafe_allow_html=True)

def auto_sharpen_image(img):
    """Sharpen image without any external software"""
    # Unsharp mask
    blurred = cv2.GaussianBlur(img, (0, 0), 3.0)
    sharpened = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)
    # High-pass filter
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]]) / 1.0
    final = cv2.filter2D(sharpened, -1, kernel)
    # Fix brightness if too high
    lab = cv2.cvtColor(final, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    mean_l = np.mean(l)
    if mean_l > 160:
        l = cv2.add(l, -15)
    lab = cv2.merge((l, a, b))
    final = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    return final

def analyze_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = img.shape[:2]
    mp = (w * h) / 1_000_000
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = lap.var()
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    noise = np.mean(np.abs(gray.astype(float) - blur.astype(float)))
    brightness = np.mean(gray)
    return mp, sharpness, noise, brightness

st.title("✅ Adobe Stock Auditor + Auto Sharpen")
st.markdown("### আপলোড করুন, আমি নিজেই ইমেজ শার্প করে দিচ্ছি (Photoshop ছাড়া)")

uploaded = st.file_uploader("ইমেজ আপলোড করুন", type=['jpg','jpeg'], accept_multiple_files=True)

if uploaded:
    temp_dir = tempfile.mkdtemp()
    results = []
    for file in uploaded:
        path = os.path.join(temp_dir, file.name)
        with open(path, 'wb') as f:
            f.write(file.getbuffer())
        img = cv2.imread(path)
        # Auto sharpen
        sharpened = auto_sharpen_image(img)
        # Save sharpened version
        sharp_path = os.path.join(temp_dir, "sharp_" + file.name)
        cv2.imwrite(sharp_path, sharpened, [cv2.IMWRITE_JPEG_QUALITY, 100])
        # Analyze sharpened image
        mp, sharp, noise, bright = analyze_image(sharpened)
        # Score
        score = 100
        errors = []
        if mp < 4.5:
            errors.append(f"Resolution {mp:.1f}MP (need 4.5+)")
            score -= 20
        if sharp < 60:
            errors.append(f"Sharpness {sharp:.1f} (need 60+)")
            score -= 25
        if noise > 5:
            errors.append(f"Noise {noise:.1f} (need <5)")
            score -= 15
        if bright < 100 or bright > 180:
            errors.append(f"Brightness {bright:.0f} (need 100-180)")
            score -= 10
        score = max(0, min(100, score))
        status = "ACCEPTED" if (score >= 80 and len(errors)==0) else "REJECTED"
        # Thumbnail
        thumb = Image.open(sharp_path)
        thumb.thumbnail((100,100))
        buf = io.BytesIO()
        thumb.save(buf, format="JPEG")
        thumb_b64 = base64.b64encode(buf.getvalue()).decode()
        results.append({
            "name": file.name,
            "score": score,
            "status": status,
            "mp": round(mp,1),
            "sharp": round(sharp,1),
            "noise": round(noise,1),
            "bright": round(bright),
            "errors": errors,
            "thumb": f"data:image/jpeg;base64,{thumb_b64}"
        })
    # Show results
    st.subheader("Results after Auto-Sharpen")
    for r in results:
        col1, col2 = st.columns([1,3])
        with col1:
            st.image(r["thumb"], width=100)
        with col2:
            st.write(f"**{r['name']}**")
            if r["status"] == "ACCEPTED":
                st.markdown('<span class="badge-pass">✅ ACCEPTED (Adobe will approve)</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="badge-fail">❌ REJECTED</span>', unsafe_allow_html=True)
            st.write(f"Score: {r['score']}/100 | Sharpness: {r['sharp']} | Noise: {r['noise']} | Brightness: {r['bright']} | MP: {r['mp']}")
            if r["errors"]:
                st.warning("Problems: " + ", ".join(r["errors"]))
        st.divider()
    shutil.rmtree(temp_dir, ignore_errors=True)
else:
    st.info("👆 ইমেজ আপলোড করুন। আমি নিজে শার্প করে দিচ্ছি।")
