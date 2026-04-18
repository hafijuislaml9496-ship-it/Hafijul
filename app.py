
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

st.set_page_config(page_title="Adobe Stock Auditor", page_icon="🎨", layout="wide")

st.markdown("""
<style>
.badge-ok { background-color: #00ff9d; color: #000; padding: 4px 12px; border-radius: 20px; display: inline-block; }
.badge-risky { background-color: #ffb443; color: #000; padding: 4px 12px; border-radius: 20px; display: inline-block; }
.badge-no { background-color: #ff4444; color: #fff; padding: 4px 12px; border-radius: 20px; display: inline-block; }
</style>
""", unsafe_allow_html=True)

class Auditor:
    def __init__(self, path):
        self.path = path
        self.img = None
        self.gray = None
        self.result = {
            'status': '', 
            'score': 0, 
            'errors': [], 
            'warnings': [], 
            'metrics': {}, 
            'prompt': '',
            'simple_prompt': ''
        }
    
    def load(self):
        self.img = cv2.imread(self.path)
        if self.img is None:
            return False
        self.gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        self.h, self.w = self.img.shape[:2]
        return True
    
    def check(self):
        errors = []
        warnings = []
        
        # Resolution check
        mp = (self.w * self.h) / 1000000
        self.result['metrics']['mp'] = round(mp, 2)
        if mp < 4.0:
            errors.append("low_resolution")
        elif mp < 5.0:
            warnings.append("low_resolution_warning")
        
        # Sharpness check
        lap = cv2.Laplacian(self.gray, cv2.CV_64F)
        sharp = lap.var()
        self.result['metrics']['sharp'] = round(sharp, 1)
        if sharp < 40:
            errors.append("blurry")
        elif sharp < 60:
            warnings.append("soft_focus")
        
        # Noise check
        blur = cv2.GaussianBlur(self.gray, (5,5), 0)
        noise = np.mean(np.abs(self.gray.astype(float) - blur.astype(float)))
        self.result['metrics']['noise'] = round(noise, 1)
        if noise > 10:
            errors.append("noisy")
        elif noise > 7:
            warnings.append("grainy")
        
        # Brightness check
        bright = np.mean(self.gray)
        self.result['metrics']['bright'] = round(bright)
        if bright < 80:
            errors.append("underexposed")
        elif bright > 200:
            errors.append("overexposed")
        
        # Texture check (waxy skin)
        grad_x = cv2.Sobel(self.gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(self.gray, cv2.CV_64F, 0, 1, ksize=3)
        texture = np.mean(np.sqrt(grad_x**2 + grad_y**2))
        self.result['metrics']['texture'] = round(texture, 1)
        if texture < 25:
            errors.append("waxy_skin")
        
        self.result['errors'] = errors
        self.result['warnings'] = warnings
        
        # Calculate score
        score = 100
        score -= len(errors) * 15
        score -= len(warnings) * 5
        self.result['score'] = max(0, min(100, score))
        
        # Set status
        if self.result['score'] >= 80 and len(errors) == 0:
            self.result['status'] = 'ACCEPTED'
        elif self.result['score'] >= 60:
            self.result['status'] = 'RISKY'
        else:
            self.result['status'] = 'REJECTED'
        
        return self.result
    
    def get_subject_from_filename(self):
        name = os.path.basename(self.path)
        name = os.path.splitext(name)[0]
        name = name.lower()
        
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
        if 'office' in name:
            return 'office worker'
        if 'medical' in name:
            return 'medical scene'
        if 'hand' in name:
            return 'hands'
        return 'person'
    
    def generate_custom_prompt(self):
        subject = self.get_subject_from_filename()
        errors = self.result['errors']
        warnings = self.result['warnings']
        
        # Build prompt based on actual issues found
        prompt_parts = []
        prompt_parts.append("Ultra-realistic stock photo of " + subject)
        
        # Add quality based on issues
        if 'blurry' in errors:
            prompt_parts.append("crystal clear tack-sharp focus, no motion blur")
        elif 'soft_focus' in warnings:
            prompt_parts.append("sharp focus on main subject")
        else:
            prompt_parts.append("excellent sharpness")
        
        if 'noisy' in errors:
            prompt_parts.append("ISO 100, completely noise-free")
        elif 'grainy' in warnings:
            prompt_parts.append("minimal grain, clean image")
        
        if 'waxy_skin' in errors:
            prompt_parts.append("natural skin texture with visible pores, no plastic or waxy appearance")
        else:
            prompt_parts.append("natural authentic skin texture")
        
        if 'underexposed' in errors:
            prompt_parts.append("bright well-lit scene, proper exposure")
        elif 'overexposed' in errors:
            prompt_parts.append("balanced exposure, no blown highlights")
        else:
            prompt_parts.append("perfect exposure")
        
        if 'low_resolution' in errors:
            prompt_parts.append("8K resolution minimum (7680x4320)")
        
        # Common good practices
        prompt_parts.append("clean uncluttered background")
        prompt_parts.append("no logos watermarks or text")
        prompt_parts.append("professional commercial photography quality")
        prompt_parts.append("shot on Sony A7R IV 85mm lens f/2.8")
        prompt_parts.append("Adobe Stock ready")
        
        # Join all parts
        full_prompt = '"' + ", ".join(prompt_parts) + '"'
        
        # Also create a simple version
        simple_parts = ["Ultra-realistic " + subject]
        if 'blurry' in errors:
            simple_parts.append("crystal clear sharp")
        if 'waxy_skin' in errors:
            simple_parts.append("natural skin texture")
        if 'noisy' in errors:
            simple_parts.append("no noise")
        simple_parts.append("8K")
        simple_parts.append("no logos")
        simple_prompt = '"' + " ".join(simple_parts) + '"'
        
        # Create detailed master prompt with explanation
        master_prompt = "="*60 + "\n"
        master_prompt += "MASTER PROMPT FOR: " + os.path.basename(self.path) + "\n"
        master_prompt += "="*60 + "\n\n"
        master_prompt += "Subject detected: " + subject.title() + "\n"
        master_prompt += "Current score: " + str(self.result['score']) + "/100\n"
        master_prompt += "Issues found: " + ", ".join(errors) if errors else "None\n\n"
        master_prompt += "-"*60 + "\n"
        master_prompt += "COPY THIS PROMPT TO AI GENERATOR:\n"
        master_prompt += "-"*60 + "\n\n"
        master_prompt += full_prompt + "\n\n"
        
        if errors:
            master_prompt += "-"*60 + "\n"
            master_prompt += "SPECIFIC FIXES NEEDED FOR THIS IMAGE:\n"
            master_prompt += "-"*60 + "\n"
            if 'blurry' in errors:
                master_prompt += "• BLURRY: Need crystal clear sharp focus\n"
            if 'noisy' in errors:
                master_prompt += "• NOISY: Use lower ISO, add more light\n"
            if 'waxy_skin' in errors:
                master_prompt += "• WAXY SKIN: Don't over-smooth, keep natural texture\n"
            if 'underexposed' in errors:
                master_prompt += "• TOO DARK: Increase exposure, add fill light\n"
            if 'overexposed' in errors:
                master_prompt += "• TOO BRIGHT: Reduce highlights, balance exposure\n"
            if 'low_resolution' in errors:
                master_prompt += "• LOW RES: Generate at higher resolution\n"
        
        master_prompt += "\n" + "="*60 + "\n"
        master_prompt += "Generated: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n"
        master_prompt += "="*60
        
        self.result['prompt'] = master_prompt
        self.result['simple_prompt'] = simple_prompt
        self.result['full_prompt'] = full_prompt
        
        return master_prompt

def make_thumbnail(path, size=(80, 80)):
    try:
        img = Image.open(path)
        img.thumbnail(size)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except:
        return None

def main():
    st.title("🎨 Adobe Stock Smart Auditor")
    st.markdown("### প্রতিটি ইমেজের সমস্যা অনুযায়ী আলাদা AI Prompt তৈরি করে")
    
    with st.sidebar:
        st.header("কিভাবে কাজ করে")
        st.write("1. ইমেজ আপলোড করুন")
        st.write("2. টুল ইমেজের সমস্যা শনাক্ত করে (ব্লারি? নয়েজি? ডার্ক?)")
        st.write("3. শনাক্ত করা সমস্যা অনুযায়ী কাস্টম প্রম্পট তৈরি করে")
        st.write("4. প্রম্পট কপি করে AI তে ব্যবহার করুন")
        st.divider()
        st.header("শনাক্ত করা হয়")
        st.write("🔍 ব্লারি / সফট ফোকাস")
        st.write("📊 নয়েজ / গ্রেইন")
        st.write("💡 এক্সপোজার (ডার্ক/ব্রাইট)")
        st.write("🎨 ওয়াক্সি স্কিন (ওভার-স্মুথিং)")
        st.write("📐 রেজোলিউশন")
    
    files = st.file_uploader("ইমেজ আপলোড করুন (একাধিক)", type=['jpg','jpeg'], accept_multiple_files=True)
    
    if files:
        temp_dir = tempfile.mkdtemp()
        all_results = []
        
        progress = st.progress(0)
        
        for i, f in enumerate(files):
            path = os.path.join(temp_dir, f.name)
            with open(path, 'wb') as fp:
                fp.write(f.getbuffer())
            
            auditor = Auditor(path)
            auditor.load()
            result = auditor.check()
            auditor.generate_custom_prompt()
            
            result['name'] = f.name
            result['thumb'] = make_thumbnail(path)
            result['prompt'] = auditor.result['prompt']
            result['simple_prompt'] = auditor.result['simple_prompt']
            result['full_prompt'] = auditor.result['full_prompt']
            result['errors_list'] = auditor.result['errors']
            
            all_results.append(result)
            progress.progress((i + 1) / len(files))
        
        progress.empty()
        
        # Summary
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📸 Total", len(all_results))
        c2.metric("✅ Accepted", sum(1 for r in all_results if r['status'] == 'ACCEPTED'))
        c3.metric("⚠️ Risky", sum(1 for r in all_results if r['status'] == 'RISKY'))
        c4.metric("❌ Rejected", sum(1 for r in all_results if r['status'] == 'REJECTED'))
        
        st.divider()
        
        # Show each result
        for idx, r in enumerate(all_results):
            with st.container():
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if r['thumb']:
                        st.image(r['thumb'], width=100)
                
                with col2:
                    st.subheader(r['name'])
                    if r['status'] == 'ACCEPTED':
                        st.markdown('<span class="badge-ok">✅ ACCEPTED</span>', unsafe_allow_html=True)
                    elif r['status'] == 'RISKY':
                        st.markdown('<span class="badge-risky">⚠️ RISKY</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="badge-no">❌ REJECTED</span>', unsafe_allow_html=True)
                    
                    st.write(f"**Score:** {r['score']}/100")
                    st.write(f"**Resolution:** {r['metrics']['mp']} MP")
                    st.write(f"**Sharpness:** {r['metrics']['sharp']}")
                    st.write(f"**Noise:** {r['metrics']['noise']}")
                    st.write(f"**Brightness:** {r['metrics']['bright']}")
                
                # Show detected problems
                if r['errors_list']:
                    st.error("**❌ সমস্যা শনাক্ত:** " + ", ".join(r['errors_list']))
                
                # Show prompts only for rejected/risky
                if r['status'] != 'ACCEPTED':
                    st.divider()
                    st.markdown("### 🎨 এই ইমেজ ঠিক করে বানানোর জন্য কাস্টম প্রম্পট")
                    
                    # Problem description
                    st.info("**শনাক্ত করা সমস্যা অনুযায়ী নিচের প্রম্পট তৈরি করা হয়েছে:**")
                    
                    # Full prompt
                    st.code(r['prompt'], language='markdown')
                    
                    # Copy button
                    if st.button(f"📋 প্রম্পট কপি করুন", key=f"copy_{r['name']}_{idx}"):
                        st.success("✅ প্রম্পট কপি হয়েছে!")
                    
                    # Simple prompt
                    st.markdown("**সহজ ভার্সন (এক লাইনে):**")
                    st.code(r['simple_prompt'], language='markdown')
                    
                    if st.button(f"📋 সহজ প্রম্পট কপি করুন", key=f"copy_simple_{r['name']}_{idx}"):
                        st.success("✅ সহজ প্রম্পট কপি হয়েছে!")
                
                st.divider()
        
        # Download all
        rejected = [r for r in all_results if r['status'] != 'ACCEPTED']
        if rejected:
            all_text = ""
            for r in rejected:
                all_text += "\n" + "="*60 + "\n"
                all_text += "File: " + r['name'] + "\n"
                all_text += "Status: " + r['status'] + "\n"
                all_text += "Score: " + str(r['score']) + "/100\n"
                all_text += "Issues: " + ", ".join(r['errors_list']) + "\n"
                all_text += "="*60 + "\n\n"
                all_text += r['prompt'] + "\n\n"
            
            st.download_button("📥 সব প্রম্পট ডাউনলোড করুন", all_text, "prompts.txt")
        
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    else:
        st.info("👆 ইমেজ আপলোড করুন")
        
        with st.expander("📖 উদাহরণ দেখুন"):
            st.markdown("""
            **যদি আপনি doctor_tablet.jpg আপলোড করেন এবং ইমেজটি ব্লারি ও নয়েজি হয়, তাহলে প্রম্পট হবে:**
            
