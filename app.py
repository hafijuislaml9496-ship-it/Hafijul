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

# Simple CSS
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
            self.results['errors'].append("Load error: " + str(e))
            return False
    
    def analyze(self):
        megapixels = (self.w * self.h) / 1000000
        self.results['metrics']['megapixels'] = round(megapixels, 2)
        self.results['metrics']['dimensions'] = str(self.w) + "x" + str(self.h)
        
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
        
        # Master prompt building
        master_prompt_lines = []
        master_prompt_lines.append("=" * 50)
        master_prompt_lines.append("MASTER PROMPT FOR ADOBE STOCK")
        master_prompt_lines.append("=" * 50)
        master_prompt_lines.append("")
        master_prompt_lines.append("Original File: " + os.path.basename(self.image_path))
        master_prompt_lines.append("Subject: " + subject.title())
        master_prompt_lines.append("Current Score: " + str(self.results['score']) + "/100")
        master_prompt_lines.append("Issues Found: " + str(len(errors)))
        master_prompt_lines.append("")
        master_prompt_lines.append("=" * 50)
        master_prompt_lines.append("COPY THIS PROMPT TO AI IMAGE GENERATOR")
        master_prompt_lines.append("=" * 50)
        master_prompt_lines.append("")
        
        main_prompt = '"Ultra-realistic stock photo of ' + subject + ' in professional environment. 8K resolution, crystal clear sharp focus. Natural skin texture with visible pores, no waxy appearance. Professional commercial photography quality. Clean background, no logos or watermarks. Perfect exposure, natural lighting. Shot on Sony A7R IV, 85mm lens, f/2.8, ISO 100. Editorial quality, Adobe Stock ready."'
        master_prompt_lines.append(main_prompt)
        master_prompt_lines.append("")
        master_prompt_lines.append("=" * 50)
        master_prompt_lines.append("FIXES NEEDED FOR THIS IMAGE")
        master_prompt_lines.append("=" * 50)
        master_prompt_lines.append("")
        
        for fix in fixes:
            master_prompt_lines.append(fix)
        
        master_prompt_lines.append("")
        master_prompt_lines.append("=" * 50)
        master_prompt_lines.append("TECHNICAL REQUIREMENTS")
        master_prompt_lines.append("=" * 50)
        master_prompt_lines.append("")
        master_prompt_lines.append("- Resolution: 8MP minimum (3840x2160)")
        master_prompt_lines.append("- Sharpness: Laplacian variance > 80")
        master_prompt_lines.append("- Noise: Under 5.0")
        master_prompt_lines.append("- Format: JPEG, sRGB")
        master_prompt_lines.append("- Aspect Ratio: 4:3, 3:2, or 16:9")
        master_prompt_lines.append("- Max File Size: 45MB")
        master_prompt_lines.append("")
        master_prompt_lines.append("=" * 50)
        master_prompt_lines.append("AVOID THESE")
        master_prompt_lines.append("=" * 50)
        master_prompt_lines.append("")
        master_prompt_lines.append("- Blurry or soft focus")
        master_prompt_lines.append("- Excessive noise or grain")
        master_prompt_lines.append("- Waxy/plastic skin texture")
        master_prompt_lines.append("- Logos, watermarks, brands")
        master_prompt_lines.append("- Over/under exposure")
        master_prompt_lines.append("- AI artifacts")
        master_prompt_lines.append("")
        master_prompt_lines.append("=" * 50)
        master_prompt_lines.append("Generated: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        master_prompt_lines.append("=" * 50)
        
        master_prompt = "\n".join(master_prompt_lines)
        
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
    st.title("Adobe Stock Pro Auditor")
    st.markdown("### প্রতিটি ইমেজের জন্য আলাদা AI Master Prompt + কপি বাটন")
    
    with st.sidebar:
        st.header("কিভাবে ব্যবহার করবেন")
        st.write("1. ইমেজ আপলোড করুন")
        st.write("2. অটো অডিট হবে")
        st.write("3. রিজেক্ট হলে প্রম্পট দেখাবে")
        st.write("4. কপি বাটন চেপে প্রম্পট কপি করুন")
        st.write("5. Midjourney/DALL-E এ পেস্ট করুন")
        st.write("6. নতুন ইমেজ বানান")
        st.divider()
        st.header("চেক করা হয়")
        st.write("- রেজোলিউশন (4MP+)")
        st.write("- শার্পনেস (ব্লার চেক)")
        st.write("- নয়েজ লেভেল")
        st.write("- এক্সপোজার (লাইটিং)")
    
    uploaded_files = st.file_uploader(
        "ইমেজ আপলোড করুন (JPG/JPEG)",
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
        
        st.divider()
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        accepted = sum(1 for r in all_results if r['status'] == 'ACCEPTED')
        risky = sum(1 for r in all_results if r['status'] == 'RISKY')
        rejected = sum(1 for r in all_results if r['status'] == 'REJECTED')
        
        with col1:
            st.metric("Total Images", len(all_results))
        with col2:
            st.metric("Accepted", accepted)
        with col3:
            st.metric("Risky", risky)
        with col4:
            st.metric("Rejected", rejected)
        
        st.divider()
        
        # Show each result
        for res in all_results:
            # Status color
            if res['status'] == 'ACCEPTED':
                status_class = "status-accepted"
            elif res['status'] == 'RISKY':
                status_class = "status-risky"
            else:
                status_class = "status-rejected"
            
            # Display image card
            st.image(res['thumbnail'], width=100)
            st.markdown("**" + res['filename'] + "**")
            st.markdown('<span class="' + status_class + '">' + res['status'] + '</span>', unsafe_allow_html=True)
            st.write("Score: " + str(res['score']) + "/100")
            st.write("Resolution: " + str(res['metrics'].get('megapixels', 'N/A')) + " MP")
            st.write("Sharpness: " + str(res['metrics'].get('sharpness', 'N/A')))
            st.write("Noise: " + str(res['metrics'].get('noise', 'N/A')))
            st.write("Brightness: " + str(res['metrics'].get('brightness', 'N/A')))
            
            # Errors
            if res['errors']:
                with st.expander("কেন রিজেক্ট হয়েছে", expanded=True):
                    for err in res['errors']:
                        st.error(err)
            
            # Warnings
            if res['warnings']:
                with st.expander("সতর্কতা"):
                    for warn in res['warnings']:
                        st.warning(warn)
            
            # Prompts for rejected/risky images
            if res['status'] != 'ACCEPTED':
                st.divider()
                st.subheader("এই ইমেজ ঠিক করে বানানোর জন্য AI Prompt")
                
                # Full prompt
                st.code(res['master_prompt'], language='markdown')
                
                # Copy button
                if st.button("পুরো প্রম্পট কপি করুন", key="full_" + res['filename']):
                    st.success("প্রম্পট কপি হয়েছে!")
                
                # Simple prompt
                st.info(res['recreation_prompt'])
                
                if st.button("সহজ প্রম্পট কপি করুন", key="simple_" + res['filename']):
                    st.success("সহজ প্রম্পট কপি হয়েছে!")
            
            st.divider()
        
        # Download all prompts
        rejected_images = [r for r in all_results if r['status'] != 'ACCEPTED']
        if rejected_images:
            all_text = ""
            for r in rejected_images:
                all_text += "="*60 + "\n"
                all_text += "File: " + r['filename'] + "\n"
                all_text += "Status: " + r['status'] + "\n"
                all_text += "Score: " + str(r['score']) + "/100\n"
                all_text += "="*60 + "\n\n"
                all_text += r['master_prompt'] + "\n\n"
                all_text += "Simple Prompt:\n" + r['recreation_prompt'] + "\n\n"
            
            st.download_button(
                label="সব প্রম্পট ডাউনলোড করুন (TXT)",
                data=all_text,
                file_name="adobe_prompts_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".txt",
                mime="text/plain"
            )
        
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    else:
        st.info("উপরে ইমেজ আপলোড করুন")
        
        with st.expander("উদাহরণ দেখুন"):
            st.write("আপলোড করুন: doctor_tablet.jpg")
            st.write("রিজেক্ট করলে প্রম্পট দেখাবে:")
            st.code('"Ultra-realistic stock photo of medical professional, 8K, crystal clear sharp focus, natural skin texture, clean background, no logos, professional lighting, Adobe Stock quality"')
            st.write("কপি করে Midjourney/DALL-E এ পেস্ট করুন -> নতুন ইমেজ বানান -> Adobe Stock এ আপলোড করুন")

if __name__ == "__main__":
    main()
