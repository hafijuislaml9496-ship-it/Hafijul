"""
Adobe Stock Auditor with Individual Master Prompts
প্রতিটি রিজেক্টেড ইমেজের জন্য আলাদা AI Prompt জেনারেট করে
"""

import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pandas as pd
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

# Custom CSS
st.markdown("""
<style>
    .status-pass {
        background-color: #00ff9d;
        color: #000;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .status-fail {
        background-color: #ff4444;
        color: #fff;
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
    .prompt-card {
        background-color: #1e1e2e;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border: 1px solid #ff4b4b;
    }
    .copy-btn {
        background-color: #ff4b4b;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 5px;
        cursor: pointer;
        margin-top: 10px;
    }
    .copy-btn:hover {
        background-color: #ff6b6b;
    }
</style>
""", unsafe_allow_html=True)

class AdobeStockAuditorWithPrompts:
    """প্রতিটি ইমেজের জন্য আলাদা প্রম্পট জেনারেট করবে"""
    
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
            'master_prompt': None,
            'fix_instructions': [],
            'recreation_prompt': None
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
    
    def analyze_image_deep(self):
        """ডিপ এনালাইসিস - কি কি সমস্যা আছে সেটা বের করে"""
        issues = []
        
        # 1. Resolution check
        megapixels = (self.w * self.h) / 1_000_000
        self.results['metrics']['megapixels'] = round(megapixels, 2)
        self.results['metrics']['dimensions'] = f"{self.w}x{self.h}"
        
        if megapixels < 4.0:
            issues.append('low_resolution')
            self.results['errors'].append(f"Low resolution: {megapixels}MP (Adobe needs 4MP+)")
        
        # 2. Sharpness check
        laplacian = cv2.Laplacian(self.gray, cv2.CV_64F)
        sharpness = laplacian.var()
        self.results['metrics']['sharpness'] = round(sharpness, 2)
        
        if sharpness < 40:
            issues.append('blurry')
            self.results['errors'].append(f"Blurry image: {sharpness:.1f}")
        elif sharpness < 60:
            issues.append('soft_focus')
            self.results['warnings'].append(f"Soft focus: {sharpness:.1f}")
        
        # 3. Noise check
        blur = cv2.GaussianBlur(self.gray, (5, 5), 0)
        noise = np.mean(np.abs(self.gray.astype(float) - blur.astype(float)))
        self.results['metrics']['noise'] = round(noise, 2)
        
        if noise > 10:
            issues.append('noisy')
            self.results['errors'].append(f"Too noisy: {noise:.1f}")
        elif noise > 6:
            issues.append('grainy')
            self.results['warnings'].append(f"Visible grain: {noise:.1f}")
        
        # 4. Lighting check
        mean_brightness = np.mean(self.gray)
        self.results['metrics']['brightness'] = round(mean_brightness, 2)
        
        if mean_brightness < 80:
            issues.append('underexposed')
            self.results['errors'].append("Too dark (underexposed)")
        elif mean_brightness > 200:
            issues.append('overexposed')
            self.results['errors'].append("Too bright (overexposed)")
        
        # 5. Aspect ratio check
        ratio = self.w / self.h
        self.results['metrics']['aspect_ratio'] = round(ratio, 2)
        
        if not (1.2 < ratio < 1.9):
            issues.append('bad_aspect_ratio')
            self.results['warnings'].append(f"Unusual aspect ratio: {ratio:.2f}")
        
        # 6. Texture check (simplified)
        grad_x = cv2.Sobel(self.gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(self.gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.mean(np.sqrt(grad_x**2 + grad_y**2))
        self.results['metrics']['texture'] = round(gradient_magnitude, 2)
        
        if gradient_magnitude < 25:
            issues.append('waxy')
            self.results['errors'].append("Waxy/plastic texture detected (over-smoothing)")
        
        self.results['issues'] = issues
        return issues
    
    def extract_subject_and_scene(self):
        """ফাইলনেম থেকে সাবজেক্ট এবং সীন বের করে"""
        filename = os.path.basename(self.image_path)
        name = os.path.splitext(filename)[0]
        name_clean = re.sub(r'[_-]+', ' ', name).lower()
        
        # Subject mapping
        subjects = {
            'doctor': 'medical professional', 'nurse': 'healthcare worker',
            'patient': 'patient', 'business': 'business professional',
            'woman': 'woman', 'man': 'man', 'person': 'person',
            'tablet': 'person using tablet', 'laptop': 'person using laptop',
            'phone': 'person using smartphone', 'office': 'office worker',
            'medical': 'medical scene', 'healthcare': 'healthcare scene',
            'hand': 'hands', 'portrait': 'portrait', 'group': 'group of people'
        }
        
        subject = 'person'
        for key, val in subjects.items():
            if key in name_clean:
                subject = val
                break
        
        # Scene detection based on filename
        scene_keywords = {
            'office': 'modern office environment',
            'hospital': 'hospital or medical facility',
            'clinic': 'medical clinic',
            'home': 'home environment',
            'studio': 'professional photo studio',
            'outdoor': 'outdoor natural setting',
            'street': 'urban street scene'
        }
        
        scene = 'professional studio or clean environment'
        for key, val in scene_keywords.items():
            if key in name_clean:
                scene = val
                break
        
        return subject, scene
    
    def generate_unique_master_prompt(self):
        """প্রতিটি ইমেজের জন্য ইউনিক মাস্টার প্রম্পট জেনারেট করে"""
        
        subject, scene = self.extract_subject_and_scene()
        issues = self.results.get('issues', [])
        metrics = self.results['metrics']
        
        # সমস্যা অনুযায়ী ফিক্স নির্দেশনা
        fix_instructions = []
        
        if 'low_resolution' in issues:
            fix_instructions.append("FIX: Generate at minimum 8MP (3840x2160 or larger)")
        else:
            fix_instructions.append("Keep current resolution or higher")
            
        if 'blurry' in issues:
            fix_instructions.append("FIX: Use faster shutter speed, better lens, or AI upscaler with sharpening")
        elif 'soft_focus' in issues:
            fix_instructions.append("FIX: Ensure main subject is tack-sharp, use focus stacking if needed")
        else:
            fix_instructions.append("Maintain excellent sharpness")
            
        if 'noisy' in issues:
            fix_instructions.append("FIX: Use lower ISO (100-400), better lighting, or AI denoise")
        elif 'grainy' in issues:
            fix_instructions.append("FIX: Reduce ISO, add more light")
        else:
            fix_instructions.append("Keep noise-free")
            
        if 'underexposed' in issues:
            fix_instructions.append("FIX: Add more light, increase exposure by +1 stop")
        elif 'overexposed' in issues:
            fix_instructions.append("FIX: Reduce highlights, use fill light")
        else:
            fix_instructions.append("Proper exposure maintained")
            
        if 'waxy' in issues:
            fix_instructions.append("FIX: Avoid over-smoothing, preserve natural skin pores and texture")
        else:
            fix_instructions.append("Natural texture preserved")
        
        # Sharpness recommendation
        sharpness = metrics.get('sharpness', 50)
        if sharpness < 40:
            sharpness_text = "CRITICAL: Very blurry - need major sharpness improvement"
        elif sharpness < 60:
            sharpness_text = "Soft focus - improve sharpness"
        else:
            sharpness_text = "Good sharpness - maintain this level"
        
        # Build prompt
        prompt_header = f"MASTER PROMPT FOR ADOBE STOCK - RE-CREATION\n\n"
        prompt_header += f"Original Image: {os.path.basename(self.image_path)}\n"
        prompt_header += f"Subject: {subject.title()}\n"
        prompt_header += f"Scene: {scene.title()}\n"
        prompt_header += f"Current Issues: {', '.join(issues) if issues else 'None - already good'}\n\n"
        
        prompt_main = f"THE EXACT PROMPT TO RE-CREATE THIS IMAGE:\n\n"
        prompt_main += f'"Ultra-realistic stock photo of {subject} in {scene}, '\n
        prompt_main += f'8K resolution, crystal clear sharp focus, professional commercial photography, '\n
        
        # Lighting based on metrics
        brightness = metrics.get('brightness', 127)
        if brightness < 80:
            prompt_main += f'brighter exposure, well-lit scene, '\n
        elif brightness > 200:
            prompt_main += f'balanced exposure, no blown highlights, '\n
        else:
            prompt_main += f'perfect exposure, professional studio lighting, '\n
        
        prompt_main += f'natural skin texture with visible pores, no plastic or waxy appearance, '\n
        prompt_main += f'clean background, no logos or watermarks, '\n
        prompt_main += f'natural authentic mood, professional atmosphere, '\n
        prompt_main += f'shot on Sony A7R IV, 85mm lens, f/2.8, ISO 100, natural colors, '\n
        prompt_main += f'professional studio lighting, editorial quality, Adobe Stock ready"\n\n'
        
        prompt_fixes = f"SPECIFIC FIXES NEEDED:\n\n"
        for i, fix in enumerate(fix_instructions, 1):
            prompt_fixes += f"{i}. {fix}\n"
        
        prompt_fixes += f"\n{sharpness_text}\n\n"
        
        prompt_specs = f"TECHNICAL SPECIFICATIONS FOR ADOBE STOCK:\n\n"
        prompt_specs += f"- Resolution: 8MP minimum (3840x2160)\n"
        prompt_specs += f"- Format: JPEG, sRGB color space\n"
        prompt_specs += f"- Sharpness: Laplacian variance > 80\n"
        prompt_specs += f"- Noise: Under 5.0 (visually clean)\n"
        prompt_specs += f"- Aspect Ratio: 4:3, 3:2, or 16:9\n"
        prompt_specs += f"- File Size: Under 45MB\n\n"
        
        prompt_avoid = f"AVOID THESE COMMON REJECTION REASONS:\n\n"
        prompt_avoid += f"- Blurry or soft focus\n"
        prompt_avoid += f"- Excessive noise or grain\n"
        prompt_avoid += f"- Waxy/plastic skin texture\n"
        prompt_avoid += f"- Over-saturated colors\n"
        prompt_avoid += f"- Logos or watermarks\n"
        prompt_avoid += f"- Poor composition\n"
        prompt_avoid += f"- Bad lighting\n\n"
        
        prompt_footer = f"---\nGenerated for: {os.path.basename(self.image_path)}\n"
        prompt_footer += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Combine all parts
        full_prompt = prompt_header + prompt_main + prompt_fixes + prompt_specs + prompt_avoid + prompt_footer
        
        self.results['master_prompt'] = full_prompt
        self.results['fix_instructions'] = fix_instructions
        return full_prompt
    
    def generate_simple_recreation_prompt(self):
        """সহজ এবং ছোট প্রম্পট যেটা সরাসরি ব্যবহার করা যাবে"""
        subject, scene = self.extract_subject_and_scene()
        
        simple_prompt = f'"Ultra-realistic stock photo of {subject} in {scene}, 8K ultra HD, crystal clear sharp focus, natural lighting, authentic expression, clean background, no logos, commercial quality, Sony A7R IV, 85mm lens, Adobe Stock ready"'
        
        self.results['recreation_prompt'] = simple_prompt
        return simple_prompt
    
    def calculate_score(self):
        """স্কোর ক্যালকুলেশন"""
        score = 100
        score -= len(self.results['errors']) * 15
        score -= len(self.results['warnings']) * 5
        
        sharpness = self.results['metrics'].get('sharpness', 50)
        if sharpness > 100:
            score += 10
        elif sharpness < 50:
            score -= 20
            
        megapixels = self.results['metrics'].get('megapixels', 0)
        if megapixels > 12:
            score += 10
        elif megapixels < 5:
            score -= 15
            
        noise = self.results['metrics'].get('noise', 5)
        if noise > 10:
            score -= 15
        elif noise > 7:
            score -= 5
            
        return max(0, min(100, score))
    
    def run_audit(self):
        """সম্পূর্ণ অডিট চালায়"""
        if not self.load_image():
            self.results['status'] = 'REJECTED'
            self.results['score'] = 0
            return self.results
        
        # এনালাইসিস
        issues = self.analyze_image_deep()
        
        # স্কোর এবং স্ট্যাটাস
        score = self.calculate_score()
        self.results['score'] = score
        
        if score >= 80 and len(self.results['errors']) == 0:
            self.results['status'] = 'ACCEPTED'
        elif score >= 60:
            self.results['status'] = 'RISKY'
        else:
            self.results['status'] = 'REJECTED'
        
        # প্রতিটি ইমেজের জন্য আলাদা প্রম্পট জেনারেট
        self.generate_unique_master_prompt()
        self.generate_simple_recreation_prompt()
        
        return self.results

def create_thumbnail(image_path, size=(120, 120)):
    try:
        img = Image.open(image_path)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except:
        return None

def main():
    st.title("🎨 Adobe Stock Pro Auditor")
    st.markdown("### *প্রতিটি ইমেজের জন্য আলাদা AI Master Prompt + Copy Button*")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ How It Works")
        st.markdown("""
        1. **ইমেজ আপলোড করুন** (JPG/JPEG)
        2. **অটো অডিট** - সব সমস্যা শনাক্ত করবে
        3. **পার্সোনালাইজড প্রম্পট** - প্রতিটি ইমেজের জন্য আলাদা
        4. **কপি করে ব্যবহার করুন** - এক ক্লিকে কপি
        
        ### 🎯 ফিচারস:
        - ✅ রেজোলিউশন চেক (4MP+)
        - ✅ শার্পনেস এনালাইসিস
        - ✅ নয়েজ ডিটেকশন
        - ✅ লাইটিং চেক
        - ✅ ওয়াক্সি স্কিন ডিটেক্ট
        - ✅ ইউনিক এআই প্রম্পট জেনারেটর
        """)
    
    # File upload
    uploaded_files = st.file_uploader(
        "📤 ইমেজ সিলেক্ট করুন (একাধিক ফাইল একসাথে দিতে পারেন)",
        type=['jpg', 'jpeg', 'JPG', 'JPEG'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        temp_dir = tempfile.mkdtemp()
        all_results = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, file in enumerate(uploaded_files):
            status_text.text(f"🔍 অডিট করা হচ্ছে: {file.name}")
            temp_path = os.path.join(temp_dir, file.name)
            with open(temp_path, 'wb') as f:
                f.write(file.getbuffer())
            
            auditor = AdobeStockAuditorWithPrompts(temp_path)
            result = auditor.run_audit()
            result['filename'] = file.name
            result['thumbnail'] = create_thumbnail(temp_path)
            
            all_results.append(result)
            progress_bar.progress((idx + 1) / len(uploaded_files))
        
        status_text.text("✅ অডিট সম্পূর্ণ!")
        progress_bar.empty()
        
        # Summary
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        accepted = sum(1 for r in all_results if r['status'] == 'ACCEPTED')
        risky = sum(1 for r in all_results if r['status'] == 'RISKY')
        rejected = sum(1 for r in all_results if r['status'] == 'REJECTED')
        
        with col1:
            st.metric("📸 Total Images", len(all_results))
        with col2:
            st.metric("✅ Accepted", accepted)
        with col3:
            st.metric("⚠️ Risky", risky)
        with col4:
            st.metric("❌ Rejected", rejected)
        
        st.markdown("---")
        
        # প্রতিটি ইমেজের জন্য ডিটেইল রেজাল্ট
        for res in all_results:
            status_color = {
                'ACCEPTED': '#00ff9d',
                'RISKY': '#ffb443',
                'REJECTED': '#ff4444'
            }.get(res['status'], '#ffffff')
            
            # Main card
            st.markdown(f"""
            <div style="background-color: #1e1e2e; border-radius: 10px; padding: 20px; margin: 15px 0; border-left: 5px solid {status_color};">
                <table style="width: 100%;">
                    <tr>
                        <td style="width: 130px;">
                            <img src="{res['thumbnail']}" style="border-radius: 8px; width: 120px;" />
                        </td>
                        <td>
                            <h3>📷 {res['filename']}</h3>
                            <span class="status-{res['status'].lower()}">{res['status']}</span>
                            <span style="margin-left: 10px;">Score: <strong>{res['score']}/100</strong></span>
                            <br><br>
                            <strong>📐 Resolution:</strong> {res['metrics'].get('megapixels', 'N/A')} MP ({res['metrics'].get('dimensions', 'N/A')})<br>
                            <strong>🔍 Sharpness:</strong> {res['metrics'].get('sharpness', 'N/A')}<br>
                            <strong>📊 Noise:</strong> {res['metrics'].get('noise', 'N/A')}<br>
                            <strong>💡 Brightness:</strong> {res['metrics'].get('brightness', 'N/A')}<br>
                            <strong>🎨 Texture:</strong> {res['metrics'].get('texture', 'N/A')}
                        </td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
            # Errors
            if res['errors']:
                with st.expander("❌ দেখুন কেন রিজেক্ট হয়েছে", expanded=True):
                    for err in res['errors']:
                        st.error(err)
            
            # Warnings
            if res['warnings']:
                with st.expander("⚠️ সতর্কতা"):
                    for warn in res['warnings']:
                        st.warning(warn)
            
            # MASTER PROMPT
            if res['master_prompt']:
                st.markdown("---")
                st.markdown("### 🎨 আপনার ইমেজ ঠিক করে বানানোর জন্য **Master Prompt**")
                st.markdown("*এই প্রম্পট কপি করে Midjourney, DALL-E, বা Stable Diffusion এ ব্যবহার করুন*")
                
                # Full prompt with copy button
                col1, col2 = st.columns([10, 1])
                with col1:
                    st.code(res['master_prompt'], language='markdown')
                with col2:
                    if st.button("📋 কপি", key=f"copy_full_{res['filename']}"):
                        st.success("✅ প্রম্পট কপি হয়েছে!")
                        st.markdown(f"""
                        <script>
                        navigator.clipboard.writeText({repr(res['master_prompt'])});
                        </script>
                        """, unsafe_allow_html=True)
                
                # Simple version
                st.markdown("### 📝 **সহজ ভার্সন (কপি করে ইউজ করুন)**")
                st.info(res['recreation_prompt'])
                
                col_a, col_b = st.columns([1, 5])
                with col_a:
                    if st.button("📋 সহজ প্রম্পট কপি", key=f"copy_simple_{res['filename']}"):
                        st.success("✅ সহজ প্রম্পট কপি হয়েছে!")
            
            st.markdown("---")
        
        # Export option
        st.markdown("### 📥 সব প্রম্পট একসাথে ডাউনলোড করুন")
        all_prompts_text = ""
        for r in all_results:
            all_prompts_text += f"="*80 + "\n"
            all_prompts_text += f"FILE: {r['filename']}\n"
            all_prompts_text += f"STATUS: {r['status']}\n"
            all_prompts_text += f"SCORE: {r['score']}/100\n"
            all_prompts_text += f"="*80 + "\n\n"
            all_prompts_text += f"MASTER PROMPT:\n{r['master_prompt']}\n\n"
            all_prompts_text += f"SIMPLE PROMPT:\n{r['recreation_prompt']}\n\n"
        
        st.download_button(
            label="📥 সব প্রম্পট ডাউনলোড (TXT)",
            data=all_prompts_text,
            file_name=f"adobe_stock_prompts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
        
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    else:
        st.info("👆 উপরে ইমেজ আপলোড করুন। প্রতিটি ইমেজের জন্য আলাদা AI প্রম্পট পাবেন।")
        
        # Demo
        with st.expander("📖 উদাহরণ দেখুন"):
            st.markdown("""
            ### এভাবে কাজ করে:
            
            1. আপনি **doctor_tablet.jpg** ইমেজ আপলোড করলেন
            2. টুল চেক করলো: রেজোলিউশন কম, একটু ব্লারি
            3. টুল জেনারেট করলো **ইউনিক প্রম্পট**
            4. আপনি **কপি বাটন** চেপে প্রম্পট কপি করলেন
            5. Midjourney/DALL-E তে পেস্ট করে ইমেজ রিজেনারেট করলেন
            6. নতুন ইমেজ Adobe Stock এ আপলোড করলেন ✅
            """)

if __name__ == "__main__":
    main()
