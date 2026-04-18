"""
Adobe Stock Auditor with Individual Master Prompts
প্রতিটি ইমেজের জন্য আলাদা AI Prompt জেনারেট করে
"""

import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io
import base64
import tempfile
import os
import shutil
import re
from datetime import datetime

st.set_page_config(
    page_title="Adobe Stock Pro Auditor",
    page_icon="🎨",
    layout="wide"
)

st.markdown("""
<style>
.status-accepted {
    background-color: #00ff9d;
    color: #000;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: bold;
    display: inline-block;
}
.status-risky {
    background-color: #ffb443;
    color: #000;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: bold;
    display: inline-block;
}
.status-rejected {
    background-color: #ff4444;
    color: #fff;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: bold;
    display: inline-block;
}
</style>
""", unsafe_allow_html=True)

class AdobeStockAuditor:
    def __init__(self, image_path):
        self.image_path = image_path
        self.image = None
        self.gray = None
        self.results = {
            'status': 'PENDING',
            'score': 0,
            'errors': [],
            'warnings': [],
            'metrics': {},
            'master_prompt': '',
            'recreation_prompt': ''
        }
        
    def load_image(self):
        try:
            self.image = cv2.imread(self.image_path)
            if self.image is None:
                raise ValueError("Cannot load image")
            self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
            self.h, self.w = self.image.shape[:2]
            return True
        except Exception as e:
            self.results['errors'].append(f"Load error: {str(e)}")
            return False
    
    def analyze(self):
        megapixels = (self.w * self.h) / 1_000_000
        self.results['metrics']['megapixels'] = round(megapixels, 2)
        self.results['metrics']['dimensions'] = f"{self.w}x{self.h}"
        
        if megapixels < 4.0:
            self.results['errors'].append("Low resolution: " + str(megapixels) + "MP (need 4MP+)")
        
        laplacian = cv2.Laplacian(self.gray, cv2.CV_64F)
        sharpness = laplacian.var()
        self.results['metrics']['sharpness'] = round(sharpness, 2)
        
        if sharpness < 40:
            self.results['errors'].append("Blurry image: " + str(round(sharpness, 1)))
        elif sharpness < 60:
            self.results['warnings'].append("Soft focus: " + str(round(sharpness, 1)))
        
        blur = cv2.GaussianBlur(self.gray, (5, 5), 0)
        noise = np.mean(np.abs(self.gray.astype(float) - blur.astype(float)))
        self.results['metrics']['noise'] = round(noise, 2)
        
        if noise > 10:
            self.results['errors'].append("Too noisy: " + str(round(noise, 1)))
        elif noise > 6:
            self.results['warnings'].append("Visible grain: " + str(round(noise, 1)))
        
        brightness = np.mean(self.gray)
        self.results['metrics']['brightness'] = round(brightness, 2)
        
        if brightness < 80:
            self.results['errors'].append("Too dark (underexposed)")
        elif brightness > 200:
            self.results['errors'].append("Too bright (overexposed)")
        
        score = 100
        score -= len(self.results['errors']) * 15
        score -= len(self.results['warnings']) * 5
        
        if sharpness > 100:
            score += 10
        elif sharpness < 50:
            score -= 20
            
        if megapixels > 12:
            score += 10
        elif megapixels < 5:
            score -= 15
            
        self.results['score'] = max(0, min(100, score))
        
        if self.results['score'] >= 80 and len(self.results['errors']) == 0:
            self.results['status'] = 'ACCEPTED'
        elif self.results['score'] >= 60:
            self.results['status'] = 'RISKY'
        else:
            self.results['status'] = 'REJECTED'
        
        return self.results
    
    def extract_subject(self):
        filename = os.path.basename(self.image_path)
        name = os.path.splitext(filename)[0]
        name_clean = re.sub(r'[_-]+', ' ', name).lower()
        
        if 'doctor' in name_clean:
            return 'medical professional'
        elif 'nurse' in name_clean:
            return 'healthcare worker'
        elif 'patient' in name_clean:
            return 'patient'
        elif 'business' in name_clean:
            return 'business professional'
        elif 'woman' in name_clean:
            return 'woman'
        elif 'man' in name_clean:
            return 'man'
        elif 'tablet' in name_clean:
            return 'person using tablet'
        elif 'laptop' in name_clean:
            return 'person using laptop'
        elif 'phone' in name_clean:
            return 'person using smartphone'
        elif 'office' in name_clean:
            return 'office worker'
        else:
            return 'person'
    
    def generate_prompts(self):
        subject = self.extract_subject()
        errors = self.results['errors']
        
        fixes = []
        for err in errors:
            err_lower = err.lower()
            if 'resolution' in err_lower:
                fixes.append("- Generate at 8MP minimum (3840x2160)")
            if 'blurry' in err_lower or 'soft' in err_lower:
                fixes.append("- Ensure crystal clear sharp focus")
            if 'noisy' in err_lower or 'grain' in err_lower:
                fixes.append("- Use ISO 100, no visible noise")
            if 'dark' in err_lower:
                fixes.append("- Proper exposure, well-lit scene")
            if 'bright' in err_lower:
                fixes.append("- Balanced exposure, no blown highlights")
        
        if not fixes:
            fixes.append("- Maintain current quality")
        
        # Master prompt - using simple string concatenation
        master_prompt = ""
        master_prompt += "=" * 50 + "\n"
        master_prompt += "MASTER PROMPT FOR ADOBE STOCK\n"
        master_prompt += "=" * 50 + "\n\n"
        master_prompt += "Original File: " + os.path.basename(self.image_path) + "\n"
        master_prompt += "Subject: " + subject.title() + "\n"
        master_prompt += "Current Score: " + str(self.results['score']) + "/100\n"
        master_prompt += "Issues Found: " + str(len(errors)) + "\n\n"
        master_prompt += "=" * 50 + "\n"
        master_prompt += "COPY THIS PROMPT TO AI IMAGE GENERATOR\n"
        master_prompt += "=" * 50 + "\n\n"
        master_prompt += '"Ultra-realistic stock photo of ' + subject + ' in professional environment. '
        master_prompt += '8K resolution, crystal clear sharp focus. '
        master_prompt += 'Natural skin texture with visible pores, no waxy appearance. '
        master_prompt += 'Professional commercial photography quality. '
        master_prompt += 'Clean background, no logos or watermarks. '
        master_prompt += 'Perfect exposure, natural lighting. '
        master_prompt += 'Shot on Sony A7R IV, 85mm lens, f/2.8, ISO 100. '
        master_prompt += 'Editorial quality, Adobe Stock ready."\n\n'
        master_prompt += "=" * 50 + "\n"
        master_prompt += "FIXES NEEDED FOR THIS IMAGE\n"
        master_prompt += "=" * 50 + "\n\n"
        
        for fix in fixes:
            master_prompt += fix + "\n"
        
        master_prompt += "\n" + "=" * 50 + "\n"
        master_prompt += "TECHNICAL REQUIREMENTS\n"
        master_prompt += "=" * 50 + "\n\n"
        master_prompt += "- Resolution: 8MP minimum (3840x2160)\n"
        master_prompt += "- Sharpness: Laplacian variance > 80\n"
        master_prompt += "- Noise: Under 5.0\n"
        master_prompt += "- Format: JPEG, sRGB\n"
        master_prompt += "- Aspect Ratio: 4:3, 3:2, or 16:9\n"
        master_prompt += "- Max File Size: 45MB\n\n"
        master_prompt += "=" * 50 + "\n"
        master_prompt += "AVOID THESE\n"
        master_prompt += "=" * 50 + "\n\n"
        master_prompt += "- Blurry or soft focus\n"
        master_prompt += "- Excessive noise or grain\n"
        master_prompt += "- Waxy/plastic skin texture\n"
        master_prompt += "- Logos, watermarks, brands\n"
        master_prompt += "- Over/under exposure\n"
        master_prompt += "- AI artifacts\n\n"
        master_prompt += "=" * 50 + "\n"
        master_prompt += "Generated: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n"
        master_prompt += "=" * 50
        
        # Simple prompt
        simple_prompt = '"Ultra-realistic stock photo of ' + subject + ', 8K, crystal clear sharp focus, natural skin texture, clean background, no logos, professional lighting, Adobe Stock quality"'
        
        self.results['master_prompt'] = master_prompt
        self.results['recreation_prompt'] = simple_prompt
        
        return master_prompt, simple_prompt

def create_thumbnail(image_path, size=(100, 100)):
    try:
        img = Image.open(image_path)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return "data:image/jpeg;base64," + img_str
    except:
        return None

def main():
    st.title("🎨 Adobe Stock Pro Auditor")
    st.markdown("### প্রতিটি ইমেজের জন্য আলাদা AI Master Prompt + কপি বাটন")
    
    with st.sidebar:
        st.header("⚙️ কিভাবে ব্যবহার করবেন")
        st.markdown("1. ইমেজ আপলোড করুন")
        st.markdown("2. অটো অডিট হবে")
        st.markdown("3. রিজেক্ট হলে প্রম্পট দেখাবে")
        st.markdown("4. কপি বাটন চেপে প্রম্পট কপি করুন")
        st.markdown("5. Midjourney/DALL-E এ পেস্ট করুন")
        st.markdown("6. নতুন ইমেজ বানান")
        st.markdown("---")
        st.markdown("### ✅ চেক করা হয়")
        st.markdown("- রেজোলিউশন (4MP+)")
        st.markdown("- শার্পনেস (ব্লার চেক)")
        st.markdown("- নয়েজ লেভেল")
        st.markdown("- এক্সপোজার (লাইটিং)")
    
    uploaded_files = st.file_uploader(
        "📤 ইমেজ আপলোড করুন (JPG/JPEG)",
        type=['jpg', 'jpeg', 'JPG', 'JPEG'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        temp_dir = tempfile.mkdtemp()
        all_results = []
        
        progress_bar = st.progress(0)
        
        for idx, file in enumerate(uploaded_files):
            temp_path = os.path.join(temp_dir, file.name)
            with open(temp_path, 'wb') as f:
                f.write(file.getbuffer())
            
            auditor = AdobeStockAuditor(temp_path)
            auditor.load_image()
            results = auditor.analyze()
            auditor.generate_prompts()
            
            results['filename'] = file.name
            results['thumbnail'] = create_thumbnail(temp_path)
            results['master_prompt'] = auditor.results['master_prompt']
            results['recreation_prompt'] = auditor.results['recreation_prompt']
            
            all_results.append(results)
            progress_bar.progress((idx + 1) / len(uploaded_files))
        
        progress_bar.empty()
        
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        accepted = 0
        risky = 0
        rejected = 0
        
        for r in all_results:
            if r['status'] == 'ACCEPTED':
                accepted += 1
            elif r['status'] == 'RISKY':
                risky += 1
            else:
                rejected += 1
        
        with col1:
            st.metric("📸 Total", len(all_results))
        with col2:
            st.metric("✅ Accepted", accepted)
        with col3:
            st.metric("⚠️ Risky", risky)
        with col4:
            st.metric("❌ Rejected", rejected)
        
        st.markdown("---")
        
        for res in all_results:
            status_color = "accepted"
            if res['status'] == 'RISKY':
                status_color = "risky"
            elif res['status'] == 'REJECTED':
                status_color = "rejected"
            
            st.markdown(
                '<div style="background-color: #1e1e2e; border-radius: 10px; padding: 15px; margin: 10px 0;">'
                '<table style="width: 100%;">'
                '<tr>'
                '<td style="width: 110px;">'
                '<img src="' + res['thumbnail'] + '" style="border-radius: 8px; width: 100px;" />'
                '</td>'
                '<td style="vertical-align: top;">'
                '<h3>' + res['filename'] + '</h3>'
                '<span class="status-' + status_color + '">' + res['status'] + '</span>'
                '<span style="margin-left: 10px;">Score: <strong>' + str(res['score']) + '/100</strong></span>'
                '<br/><br/>'
                '<strong>Resolution:</strong> ' + str(res['metrics'].get('megapixels', 'N/A')) + ' MP<br/>'
                '<strong>Sharpness:</strong> ' + str(res['metrics'].get('sharpness', 'N/A')) + '<br/>'
                '<strong>Noise:</strong> ' + str(res['metrics'].get('noise', 'N/A')) + '<br/>'
                '<strong>Brightness:</strong> ' + str(res['metrics'].get('brightness', 'N/A'))
                '</td>'
                '</tr>'
                '</table>'
                '</div>',
                unsafe_allow_html=True
            )
            
            if res['errors']:
                with st.expander("❌ কেন রিজেক্ট হয়েছে", expanded=True):
                    for err in res['errors']:
                        st.error(err)
            
            if res['warnings']:
                with st.expander("⚠️ সতর্কতা"):
                    for warn in res['warnings']:
                        st.warning(warn)
            
            if res['status'] != 'ACCEPTED':
                st.markdown("---")
                st.markdown("### 🎨 এই ইমেজ ঠিক করে বানানোর জন্য AI Prompt")
                
                st.code(res['master_prompt'], language='markdown')
                
                btn_key = "copy_" + res['filename'] + "_" + str(idx)
                if st.button("📋 পুরো প্রম্পট কপি করুন", key=btn_key):
                    st.success("✅ প্রম্পট কপি হয়েছে!")
                    st.markdown(
                        '<script>navigator.clipboard.writeText("' + res['master_prompt'].replace('"', '\\"') + '");</script>',
                        unsafe_allow_html=True
                    )
                
                st.markdown("### 📝 সহজ ভার্সন (এক লাইনে)")
                st.info(res['recreation_prompt'])
                
                btn_key2 = "copy_simple_" + res['filename'] + "_" + str(idx)
                if st.button("📋 সহজ প্রম্পট কপি করুন", key=btn_key2):
                    st.success("✅ সহজ প্রম্পট কপি হয়েছে!")
            
            st.markdown("---")
        
        rejected_images = [r for r in all_results if r['status'] != 'ACCEPTED']
        if rejected_images:
            st.markdown("### 📥 সব প্রম্পট একসাথে ডাউনলোড")
            
            all_text = ""
            for r in rejected_images:
                all_text += "\n" + "="*60 + "\n"
                all_text += "File: " + r['filename'] + "\n"
                all_text += "Status: " + r['status'] + "\n"
                all_text += "Score: " + str(r['score']) + "/100\n"
                all_text += "="*60 + "\n\n"
                all_text += r['master_prompt']
                all_text += "\n\nSimple Prompt:\n"
                all_text += r['recreation_prompt']
                all_text += "\n"
            
            st.download_button(
                label="📥 ডাউনলোড করুন (TXT)",
                data=all_text,
                file_name="adobe_prompts_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".txt",
                mime="text/plain"
            )
        
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    else:
        st.info("👆 উপরে ইমেজ আপলোড করুন")
        
        with st.expander("📖 উদাহরণ"):
            st.markdown("**আপলোড করুন:** doctor_tablet.jpg")
            st.markdown("")
            st.markdown("**রিজেক্ট করলে প্রম্পট দেখাবে:**")
            st.code('"Ultra-realistic stock photo of medical professional, 8K, crystal clear sharp focus, natural skin texture, clean background, no logos, professional lighting, Adobe Stock quality"', language='markdown')
            st.markdown("**কপি করে Midjourney/DALL-E এ পেস্ট করুন → নতুন ইমেজ বানান → Adobe Stock এ আপলোড করুন**")

if __name__ == "__main__":
    main()
