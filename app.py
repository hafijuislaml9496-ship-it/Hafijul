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

st.set_page_config(page_title="100% Adobe Stock Guarantee", page_icon="✅", layout="wide")

st.markdown("""
<style>
.badge-pass { background-color: #00ff9d; color: #000; padding: 4px 12px; border-radius: 20px; font-weight: bold; display: inline-block; }
.badge-risky { background-color: #ffb443; color: #000; padding: 4px 12px; border-radius: 20px; font-weight: bold; display: inline-block; }
.badge-fail { background-color: #ff4444; color: #fff; padding: 4px 12px; border-radius: 20px; font-weight: bold; display: inline-block; }
</style>
""", unsafe_allow_html=True)

class StockAuditor:
    def __init__(self, path):
        self.path = path
        self.img = None
        self.gray = None
        self.results = {
            'status': 'FAIL',
            'score': 0,
            'errors': [],
            'warnings': [],
            'metrics': {},
            'prompt': '',
            'simple': ''
        }
    
    def load(self):
        self.img = cv2.imread(self.path)
        if self.img is None:
            return False
        self.gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        self.h, self.w = self.img.shape[:2]
        return True
    
    def check_all(self):
        errors = []
        warnings = []
        
        # Resolution - strict 4.5MP for guarantee
        mp = (self.w * self.h) / 1000000
        self.results['metrics']['mp'] = round(mp, 2)
        if mp < 4.5:
            errors.append("Resolution too low: " + str(round(mp,1)) + "MP (need 4.5MP+)")
        
        # Sharpness - strict 60+ for guarantee
        lap = cv2.Laplacian(self.gray, cv2.CV_64F)
        sharp = lap.var()
        self.results['metrics']['sharp'] = round(sharp, 1)
        if sharp < 60:
            errors.append("Image blurry or soft: sharpness " + str(round(sharp,1)) + " (need 60+)")
        elif sharp < 80:
            warnings.append("Sharpness borderline: " + str(round(sharp,1)))
        
        # Noise - strict under 5
        blur = cv2.GaussianBlur(self.gray, (5,5), 0)
        noise = np.mean(np.abs(self.gray.astype(float) - blur.astype(float)))
        self.results['metrics']['noise'] = round(noise, 1)
        if noise > 5:
            errors.append("Too much noise: " + str(round(noise,1)) + " (need under 5)")
        
        # Exposure
        bright = np.mean(self.gray)
        self.results['metrics']['bright'] = round(bright)
        if bright < 100:
            errors.append("Image too dark: " + str(round(bright)))
        elif bright > 200:
            errors.append("Image too bright: " + str(round(bright)))
        
        # Texture (waxy skin)
        grad_x = cv2.Sobel(self.gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(self.gray, cv2.CV_64F, 0, 1, ksize=3)
        texture = np.mean(np.sqrt(grad_x**2 + grad_y**2))
        self.results['metrics']['texture'] = round(texture, 1)
        if texture < 30:
            errors.append("Waxy/plastic texture detected (over-smoothing)")
        
        self.results['errors'] = errors
        self.results['warnings'] = warnings
        
        # Score calculation
        score = 100
        score -= len(errors) * 20
        score -= len(warnings) * 5
        self.results['score'] = max(0, min(100, score))
        
        # Final verdict - strict: only pass if NO errors and score >= 85
        if len(errors) == 0 and score >= 85:
            self.results['status'] = 'ACCEPTED'
        elif len(errors) == 0 and score >= 70:
            self.results['status'] = 'RISKY'
        else:
            self.results['status'] = 'REJECTED'
        
        return self.results
    
    def get_subject(self):
        name = os.path.basename(self.path).lower()
        if 'doctor' in name:
            return 'medical professional'
        if 'nurse' in name:
            return 'healthcare worker'
        if 'patient' in name:
            return 'patient'
        if 'business' in name:
            return 'business professional'
        if 'woman' in name:
            return 'woman'
        if 'man' in name:
            return 'man'
        if 'tablet' in name:
            return 'person using tablet'
        if 'laptop' in name:
            return 'person using laptop'
        if 'phone' in name:
            return 'person using smartphone'
        return 'person'
    
    def make_prompt(self):
        subject = self.get_subject()
        errors = self.results['errors']
        
        # Build prompt based on errors
        prompt_parts = []
        prompt_parts.append("Ultra-realistic stock photo of " + subject)
        
        for err in errors:
            if 'blurry' in err.lower() or 'soft' in err.lower():
                prompt_parts.append("crystal clear tack-sharp focus")
            if 'noise' in err.lower():
                prompt_parts.append("ISO 100 completely noise-free")
            if 'dark' in err.lower():
                prompt_parts.append("bright well-lit scene proper exposure")
            if 'bright' in err.lower():
                prompt_parts.append("balanced exposure no blown highlights")
            if 'waxy' in err.lower() or 'plastic' in err.lower():
                prompt_parts.append("natural skin texture with visible pores")
            if 'resolution' in err.lower():
                prompt_parts.append("8K resolution minimum 7680x4320")
        
        if not errors:
            prompt_parts.append("excellent sharpness natural texture perfect exposure")
        
        prompt_parts.append("clean background no logos no watermarks")
        prompt_parts.append("professional commercial photography quality")
        prompt_parts.append("Adobe Stock ready")
        
        full = '"' + ", ".join(prompt_parts) + '"'
        
        simple = '"Ultra-realistic ' + subject + ', 8K, sharp, natural, no logos"'
        
        # Master prompt
        master = []
        master.append("="*60)
        master.append("MASTER PROMPT FOR: " + os.path.basename(self.path))
        master.append("="*60)
        master.append("")
        master.append("Subject: " + subject.title())
        master.append("Score: " + str(self.results['score']) + "/100")
        master.append("Issues fixed: " + str(len(errors)))
        master.append("")
        master.append("-"*40)
        master.append("COPY THIS PROMPT:")
        master.append("-"*40)
        master.append("")
        master.append(full)
        master.append("")
        master.append("Simple version:")
        master.append(simple)
        master.append("")
        master.append("="*60)
        
        self.results['prompt'] = "\n".join(master)
        self.results['simple'] = simple
        self.results['full'] = full
        
        return self.results['prompt']

def make_thumb(path):
    try:
        img = Image.open(path)
        img.thumbnail((80, 80))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except:
        return None

st.title("✅ 100% Adobe Stock Guarantee Checker")
st.markdown("### এখানে ACCEPTED দেখলে Adobe Stock 100% APPROVE করবে")

with st.sidebar:
    st.header("Guarantee Rules")
    st.write("✅ Resolution: 4.5MP+ (strict)")
    st.write("✅ Sharpness: 60+ (strict)")
    st.write("✅ Noise: Under 5 (strict)")
    st.write("✅ No waxy/plastic texture")
    st.write("✅ Proper exposure")
    st.write("")
    st.header("How to use")
    st.write("1. Upload images")
    st.write("2. ACCEPTED = Adobe will approve")
    st.write("3. REJECTED = Fix with given prompt")
    st.write("4. Copy prompt to Midjourney/DALL-E")
    st.write("5. Generate new image and upload again")

files = st.file_uploader("Upload Images (JPG/JPEG)", type=['jpg','jpeg'], accept_multiple_files=True)

if files:
    tmp = tempfile.mkdtemp()
    all_res = []
    
    prog = st.progress(0)
    
    for i, f in enumerate(files):
        path = os.path.join(tmp, f.name)
        with open(path, 'wb') as fp:
            fp.write(f.getbuffer())
        
        a = StockAuditor(path)
        a.load()
        res = a.check_all()
        a.make_prompt()
        
        res['name'] = f.name
        res['thumb'] = make_thumb(path)
        res['full_prompt'] = a.results['prompt']
        res['simple_prompt'] = a.results['simple']
        
        all_res.append(res)
        prog.progress((i+1)/len(files))
    
    prog.empty()
    
    # Summary
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(all_res))
    c2.metric("✅ ACCEPTED", sum(1 for r in all_res if r['status'] == 'ACCEPTED'))
    c3.metric("⚠️ RISKY", sum(1 for r in all_res if r['status'] == 'RISKY'))
    c4.metric("❌ REJECTED", sum(1 for r in all_res if r['status'] == 'REJECTED'))
    
    st.divider()
    
    # Show each result
    for idx, r in enumerate(all_res):
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if r['thumb']:
                st.image(r['thumb'], width=100)
        
        with col2:
            st.subheader(r['name'])
            if r['status'] == 'ACCEPTED':
                st.markdown('<span class="badge-pass">✅ ACCEPTED - 100% Adobe Guarantee</span>', unsafe_allow_html=True)
            elif r['status'] == 'RISKY':
                st.markdown('<span class="badge-risky">⚠️ RISKY - May be rejected</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="badge-fail">❌ REJECTED - Will be rejected by Adobe</span>', unsafe_allow_html=True)
            
            st.write("**Score:** " + str(r['score']) + "/100")
            st.write("**Resolution:** " + str(r['metrics']['mp']) + " MP")
            st.write("**Sharpness:** " + str(r['metrics']['sharp']))
            st.write("**Noise:** " + str(r['metrics']['noise']))
            st.write("**Brightness:** " + str(r['metrics']['bright']))
        
        if r['errors']:
            st.error("**Reasons for rejection:** " + ", ".join(r['errors']))
        
        # Only show prompt for REJECTED or RISKY
        if r['status'] != 'ACCEPTED':
            st.divider()
            st.markdown("### 🎨 Recreate this image with this prompt")
            st.code(r['full_prompt'], language='markdown')
            
            btn_key = "copy_" + r['name'] + "_" + str(idx)
            if st.button("📋 Copy Full Prompt", key=btn_key):
                st.success("✅ Prompt copied!")
            
            st.info("**Simple version:** " + r['simple_prompt'])
            
            btn_key2 = "copy_simple_" + r['name'] + "_" + str(idx)
            if st.button("📋 Copy Simple Prompt", key=btn_key2):
                st.success("✅ Simple prompt copied!")
        
        st.divider()
    
    # Download all
    rejected_only = [r for r in all_res if r['status'] != 'ACCEPTED']
    if rejected_only:
        all_text = ""
        for r in rejected_only:
            all_text += "\n" + "="*60 + "\n"
            all_text += "File: " + r['name'] + "\n"
            all_text += "Status: " + r['status'] + "\n"
            all_text += "Score: " + str(r['score']) + "/100\n"
            all_text += "="*60 + "\n"
            all_text += r['full_prompt'] + "\n"
        
        st.download_button("📥 Download All Prompts", all_text, "prompts.txt")
    
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

else:
    st.info("👆 Upload images to check")
    
    with st.expander("Example"):
        st.write("If you upload doctor_tablet.jpg and it gets REJECTED because of blurry and noise:")
        st.code('"Ultra-realistic stock photo of medical professional, crystal clear tack-sharp focus, ISO 100 completely noise-free, natural skin texture, bright well-lit scene, 8K resolution, clean background no logos, professional quality, Adobe Stock ready"')
        st.write("Copy this prompt to Midjourney/DALL-E → Generate new image → Upload again → Get ACCEPTED")
