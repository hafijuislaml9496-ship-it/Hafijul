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
        if megapixels < 4.0:
            issues.append('low_resolution')
            self.results['errors'].append(f"Low resolution: {megapixels}MP")
        
        # 2. Sharpness check
        laplacian = cv2.Laplacian(self.gray, cv2.CV_64F)
        sharpness = laplacian.var()
        self.results['metrics']['sharpness'] = round(sharpness, 2)
        if sharpness < 50:
            issues.append('blurry')
            self.results['errors'].append(f"Blurry image: {sharpness:.1f}")
        elif sharpness < 80:
            issues.append('soft_focus')
            self.results['warnings'].append(f"Soft focus: {sharpness:.1f}")
        
        # 3. Noise check
        blur = cv2.GaussianBlur(self.gray, (5, 5), 0)
        noise = np.mean(np.abs(self.gray.astype(float) - blur.astype(float)))
        self.results['metrics']['noise'] = round(noise, 2)
        if noise > 8:
            issues.append('noisy')
            self.results['errors'].append(f"Too noisy: {noise:.1f}")
        
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
        
        # 6. Texture/Artifact check
        from skimage.filters.rank import entropy
        from skimage.morphology import disk
        try:
            entropy_img = entropy(self.gray, disk(3))
            texture = np.mean(entropy_img)
            self.results['metrics']['texture'] = round(texture, 2)
            if texture < 3.0:
                issues.append('waxy')
                self.results['errors'].append("Waxy/plastic texture detected")
        except:
            pass
        
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
            fix_instructions.append("🔧 **RESOLUTION FIX:** Generate at minimum 8MP (3840x2160 or larger)")
        else:
            fix_instructions.append("✅ Keep current resolution or higher")
            
        if 'blurry' in issues:
            fix_instructions.append("🔧 **SHARPNESS FIX:** Use faster shutter speed, better lens, or AI upscaler with sharpening")
        elif 'soft_focus' in issues:
            fix_instructions.append("🔧 **FOCUS FIX:** Ensure main subject is tack-sharp, use focus stacking if needed")
        else:
            fix_instructions.append("✅ Maintain excellent sharpness")
            
        if 'noisy' in issues:
            fix_instructions.append("🔧 **NOISE FIX:** Use lower ISO (100-400), better lighting, or AI denoise")
        else:
            fix_instructions.append("✅ Keep noise-free")
            
        if 'underexposed' in issues:
            fix_instructions.append("🔧 **EXPOSURE FIX:** Add more light, increase exposure by +1 stop")
        elif 'overexposed' in issues:
            fix_instructions.append("🔧 **EXPOSURE FIX:** Reduce highlights, use fill light")
        else:
            fix_instructions.append("✅ Proper exposure maintained")
            
        if 'waxy' in issues:
            fix_instructions.append("🔧 **TEXTURE FIX:** Avoid over-smoothing, preserve natural skin pores and texture")
        else:
            fix_instructions.append("✅ Natural texture preserved")
        
        # জেনারেটেড প্রম্পট তৈরি
        prompt = f"""# 🎨 MASTER PROMPT FOR ADOBE STOCK - RE-CREATION

## 📸 Original Image Analysis
- **Filename:** {os.path.basename(self.image_path)}
- **Subject:** {subject.title()}
- **Scene:** {scene.title()}
- **Current Issues:** {', '.join(issues) if issues else 'None - already good'}

## 🎯 THE EXACT PROMPT TO RE-CREATE THIS IMAGE
