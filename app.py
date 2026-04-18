"""
Adobe Stock Extreme Quality Auditor - FIXED VERSION
No OCR dependency required
"""

import streamlit as st
import cv2
import numpy as np
from PIL import Image
import re
import io
import base64
from skimage import exposure, filters, measure
from skimage.morphology import disk
from skimage.filters.rank import entropy
import pandas as pd
import tempfile
import os
import shutil

# Page configuration
st.set_page_config(
    page_title="Adobe Stock Auditor",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .status-accepted {
        background-color: #00ff9d;
        color: #000000;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 12px;
        display: inline-block;
    }
    .status-risky {
        background-color: #ffb443;
        color: #000000;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 12px;
        display: inline-block;
    }
    .status-rejected {
        background-color: #ff4444;
        color: #ffffff;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 12px;
        display: inline-block;
    }
    .audit-card {
        background-color: #1e1e2e;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid;
    }
    .info-box {
        background-color: #2e2e3e;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

class AdobeStockAuditor:
    """Adobe Stock image auditor with actual Adobe rules"""
    
    # REAL Adobe Stock requirements
    MIN_MEGAPIXELS = 4.0
    MIN_WIDTH = 1920
    MIN_HEIGHT = 1080
    
    # Sharpness thresholds (calibrated for real stock photos)
    LAPLACIAN_ACCEPTED = 50.0   # Sharp enough for stock
    LAPLACIAN_RISKY = 25.0      # Soft but might pass
    LAPLACIAN_REJECTED = 25.0    # Definitely blurry
    
    # Artifact detection
    WAXY_THRESHOLD = 0.80
    ENTROPY_THRESHOLD = 3.5
    
    def __init__(self, image_path):
        self.image_path = image_path
        self.image = None
        self.image_rgb = None
        self.gray = None
        self.results = {
            'passed': False,
            'score': 0,
            'errors': [],
            'warnings': [],
            'metrics': {},
            'subject': None,
            'master_prompt': None
        }
        
    def load_image(self):
        """Load and validate image"""
        try:
            self.image = cv2.imread(self.image_path)
            if self.image is None:
                raise ValueError("Could not load image")
            self.image_rgb = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
            self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
            return True
        except Exception as e:
            self.results['errors'].append(f"Load error: {str(e)}")
            return False
    
    def check_resolution(self):
        """Check Adobe Stock resolution requirement"""
        h, w = self.image.shape[:2]
        megapixels = (w * h) / 1_000_000
        self.results['metrics']['megapixels'] = round(megapixels, 2)
        self.results['metrics']['dimensions'] = f"{w}x{h}"
        
        if megapixels < self.MIN_MEGAPIXELS:
            self.results['errors'].append(f"❌ Low Resolution: {megapixels:.2f}MP (Adobe requires 4MP+)")
            return False
        elif megapixels < 5.0:
            self.results['warnings'].append(f"⚠️ Borderline Resolution: {megapixels:.2f}MP")
        return True
    
    def check_sharpness(self):
        """
        Sharpness analysis - critical for stock photography
        """
        # Laplacian variance method
        laplacian = cv2.Laplacian(self.gray, cv2.CV_64F)
        sharpness_score = laplacian.var()
        
        # Also check edges using Sobel
        sobelx = cv2.Sobel(self.gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(self.gray, cv2.CV_64F, 0, 1, ksize=3)
        edge_strength = np.mean(np.sqrt(sobelx**2 + sobely**2))
        
        self.results['metrics']['sharpness_score'] = round(sharpness_score, 2)
        self.results['metrics']['edge_strength'] = round(edge_strength, 2)
        
        # Adobe Stock interpretation
        if sharpness_score < 20:
            self.results['errors'].append(f"❌ Blurry Image: Sharpness={sharpness_score:.1f} (Adobe rejects blurry photos)")
            return False
        elif sharpness_score < 40:
            self.results['warnings'].append(f"⚠️ Soft Focus: Sharpness={sharpness_score:.1f} (May be rejected if not intentional)")
            return 'risky'
        elif sharpness_score < 60:
            self.results['warnings'].append(f"⚠️ Acceptable Sharpness: {sharpness_score:.1f} (Meets minimum standard)")
            return True
        else:
            return True  # Very sharp
    
    def check_noise_and_artifacts(self):
        """Detect noise, artifacts, and over-processing"""
        # Calculate noise level
        blur = cv2.GaussianBlur(self.gray, (5, 5), 0)
        noise = np.mean(np.abs(self.gray.astype(float) - blur.astype(float)))
        
        self.results['metrics']['noise_level'] = round(noise, 2)
        
        if noise > 15:
            self.results['errors'].append(f"❌ Excessive Noise/Grain: {noise:.1f} (Adobe rejects noisy images)")
            return False
        
        # Check for compression artifacts
        _, jpeg_encoded = cv2.imencode('.jpg', self.image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        compression_ratio = self.image.nbytes / len(jpeg_encoded)
        
        if compression_ratio > 15:
            self.results['warnings'].append("⚠️ High JPEG Compression Artifacts Detected")
        
        # Check for over-smoothing (waxy skin)
        entropy_img = entropy(self.gray, disk(3))
        avg_entropy = np.mean(entropy_img)
        self.results['metrics']['texture_entropy'] = round(avg_entropy, 2)
        
        if avg_entropy < 3.0:
            self.results['errors'].append("❌ Waxy/Plastic Texture (Over-smoothing detected)")
            return False
        
        return True
    
    def detect_logos_and_branding_simple(self):
        """
        Simple logo detection without OCR
        Uses edge density and corner analysis
        """
        h, w = self.gray.shape
        
        # Check corners for potential watermarks
        corners = [
            self.gray[0:h//10, 0:w//10],
            self.gray[0:h//10, -w//10:],
            self.gray[-h//10:, 0:w//10],
            self.gray[-h//10:, -w//10:]
        ]
        
        for corner in corners:
            # High contrast in corners often indicates watermarks
            contrast = np.std(corner)
            if contrast > 60:
                self.results['warnings'].append("⚠️ Possible watermark/logo in corner")
                break
        
        # Check for large uniform areas (potential logo backgrounds)
        uniform_threshold = 15
        uniform_regions = 0
        for i in range(0, h, 50):
            for j in range(0, w, 50):
                patch = self.gray[i:min(i+50, h), j:min(j+50, w)]
                if np.std(patch) < uniform_threshold:
                    uniform_regions += 1
        
        if uniform_regions > 20:
            self.results['warnings'].append("⚠️ Many uniform areas (potential logo placement)")
        
        return True
    
    def extract_subject_from_filename(self):
        """Extract subject from filename intelligently"""
        filename = os.path.basename(self.image_path)
        name_without_ext = os.path.splitext(filename)[0]
        name_clean = re.sub(r'[_-]+', ' ', name_without_ext).lower()
        
        subjects = {
            'doctor': 'Medical Professional',
            'nurse': 'Healthcare Worker',
            'patient': 'Patient',
            'business': 'Business Professional',
            'woman': 'Female Model',
            'man': 'Male Model',
            'person': 'Person',
            'hand': 'Hands',
            'tablet': 'Tablet User',
            'laptop': 'Laptop User',
            'phone': 'Smartphone User',
            'office': 'Office Environment',
            'medical': 'Medical Scene',
            'healthcare': 'Healthcare Scene'
        }
        
        for key, value in subjects.items():
            if key in name_clean:
                self.results['subject'] = value
                return value
        
        self.results['subject'] = 'Stock Photography Subject'
        return 'Stock Photography Subject'
    
    def generate_master_prompt(self):
        """Generate AI master prompt for recreation"""
        subject = self.results['subject']
        
        prompt = f"""# MASTER PROMPT FOR ADOBE STOCK RE-CREATION

## Subject: {subject}

## Technical Requirements:
- Resolution: 4K+ (3840x2160 minimum, 8K preferred)
- Format: High-quality JPEG, minimal compression
- Sharpness: Crisp focus on main subject
- Noise: Minimal to none
- Lighting: Professional studio or natural lighting

## Quality Checklist for Adobe Stock:
✓ No logos, trademarks, or branding visible
✓ No watermarks or text overlays
✓ Natural skin texture (no waxy/plastic appearance)
✓ Proper exposure (no blown highlights or crushed shadows)
✓ Accurate white balance
✓ No chromatic aberration or lens distortion
✓ Clean background (no distractions)

## Style Reference:
Professional stock photography quality, commercially usable, 
natural colors, authentic moments, suitable for editorial or 
commercial use.

## AI Generation Notes:
- Avoid over-smoothing skin
- Ensure readable text if any appears
- No AI artifacts or weird geometry
- Maintain natural depth of field

## Original Filename Context: {os.path.basename(self.image_path)}
"""
        self.results['master_prompt'] = prompt
        return prompt
    
    def calculate_score(self):
        """Calculate overall score 0-100"""
        score = 100
        
        # Deductions based on errors
        score -= len(self.results['errors']) * 20
        score -= len(self.results['warnings']) * 5
        
        # Sharpness adjustment
        sharpness = self.results['metrics'].get('sharpness_score', 50)
        if sharpness > 80:
            score += 10
        elif sharpness < 30:
            score -= 20
            
        # Resolution adjustment
        megapixels = self.results['metrics'].get('megapixels', 0)
        if megapixels > 12:
            score += 10
        elif megapixels < 5:
            score -= 10
            
        # Noise adjustment
        noise = self.results['metrics'].get('noise_level', 5)
        if noise > 10:
            score -= 15
            
        return max(0, min(100, score))
    
    def run_audit(self):
        """Run complete audit"""
        if not self.load_image():
            self.results['passed'] = False
            self.results['score'] = 0
            return self.results
        
        # Run all checks
        resolution_ok = self.check_resolution()
        sharpness_result = self.check_sharpness()
        artifacts_ok = self.check_noise_and_artifacts()
        logos_ok = self.detect_logos_and_branding_simple()
        
        # Determine status
        has_errors = len(self.results['errors']) > 0
        
        if not has_errors and sharpness_result == True:
            self.results['passed'] = True
            self.results['status'] = "ACCEPTED"
        elif sharpness_result == 'risky' or len(self.results['warnings']) > 0:
            self.results['passed'] = False
            self.results['status'] = "RISKY"
        else:
            self.results['passed'] = False
            self.results['status'] = "REJECTED"
        
        # Generate subject and prompt
        self.extract_subject_from_filename()
        self.generate_master_prompt()
        
        # Calculate final score
        self.results['score'] = self.calculate_score()
        
        return self.results

def create_thumbnail(image_path, size=(120, 120)):
    """Create base64 thumbnail"""
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
    st.title("🔍 Adobe Stock Quality Auditor")
    st.markdown("*Professional tool for stock photography quality checking*")
    
    # Adobe Rules Info Box
    with st.expander("📖 **REAL Adobe Stock Rules Explained**", expanded=True):
        st.markdown("""
        ### ✅ What Adobe Stock Accepts:
        - **Resolution:** Minimum 4 MP (3.8 MP sometimes accepted)
        - **Sharpness:** Visually sharp, no motion blur
        - **Noise:** Minimal, acceptable for high-ISO shots
        - **Composition:** Commercially usable, main subject clear
        - **Legal:** No trademarks, logos, or recognizable brands
        - **AI Images:** Must declare as AI-generated
        
        ### ❌ What Gets Rejected:
        - Blurry or out-of-focus images
        - Excessive noise or compression artifacts
        - Visible logos, watermarks, or brands
        - Poor lighting (too dark, blown highlights)
        - Waxy/plastic skin from over-processing
        - Distorted or unnatural AI artifacts
        - Missing model releases for recognizable people
        
        ### 📊 Our Scoring:
        - **ACCEPTED (70-100):** Meets or exceeds Adobe standards
        - **RISKY (40-69):** Might pass, but has minor issues  
        - **REJECTED (0-39):** Would likely be rejected by Adobe
        """)
    
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Audit Settings")
        st.markdown("**Mode: Adobe Stock Standard**")
        st.info("""
        **Checks performed:**
        - Resolution (4MP minimum)
        - Sharpness analysis
        - Noise detection
        - Artifact detection
        - Waxy skin check
        - Logo/watermark scan
        """)
        
        st.markdown("---")
        st.markdown("### 📊 Quality Scale")
        st.metric("Excellent", "60+", "Sharpness")
        st.metric("Acceptable", "40-60", "Soft but OK")
        st.metric("Reject", "<40", "Blurry")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "📤 Upload Images (JPG/JPEG)",
        type=['jpg', 'jpeg', 'JPG', 'JPEG'],
        accept_multiple_files=True,
        help="Upload images to check against Adobe Stock standards"
    )
    
    if uploaded_files:
        temp_dir = tempfile.mkdtemp()
        image_paths = []
        
        for uploaded_file in uploaded_files:
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            image_paths.append(temp_path)
        
        # Progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Audit each image
        audit_results = []
        
        for idx, img_path in enumerate(image_paths):
            status_text.text(f"🔍 Auditing: {os.path.basename(img_path)}...")
            
            auditor = AdobeStockAuditor(img_path)
            results = auditor.run_audit()
            results['filename'] = os.path.basename(img_path)
            results['thumbnail'] = create_thumbnail(img_path)
            
            audit_results.append(results)
            progress_bar.progress((idx + 1) / len(image_paths))
        
        status_text.text("✅ Audit complete!")
        progress_bar.empty()
        
        # Dashboard
        st.markdown("## 📊 Results Dashboard")
        
        col1, col2, col3, col4 = st.columns(4)
        accepted = sum(1 for r in audit_results if r['status'] == "ACCEPTED")
        risky = sum(1 for r in audit_results if r['status'] == "RISKY")
        rejected = sum(1 for r in audit_results if r['status'] == "REJECTED")
        
        with col1:
            st.metric("Total Images", len(audit_results))
        with col2:
            st.metric("✅ Accepted", accepted)
        with col3:
            st.metric("⚠️ Risky", risky)
        with col4:
            st.metric("❌ Rejected", rejected)
        
        st.markdown("---")
        
        # Results table
        df_data = []
        for res in audit_results:
            df_data.append({
                'Image': res['filename'],
                'Score': f"{res['score']}/100",
                'Status': res['status'],
                'MP': res['metrics'].get('megapixels', 'N/A'),
                'Sharpness': res['metrics'].get('sharpness_score', 'N/A'),
                'Issues': len(res['errors'])
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Detailed results
        st.markdown("## 🔬 Detailed Analysis")
        
        for res in audit_results:
            status_color = {
                'ACCEPTED': '#00ff9d',
                'RISKY': '#ffb443',
                'REJECTED': '#ff4444'
            }.get(res['status'], '#ffffff')
            
            with st.container():
                st.markdown(f"""
                <div class="audit-card" style="border-left-color: {status_color};">
                    <table style="width: 100%;">
                        <tr>
                            <td style="width: 130px;">
                                <img src="{res['thumbnail']}" style="border-radius: 8px; width: 120px;" />
                            </td>
                            <td>
                                <h3>{res['filename']}</h3>
                                <span class="status-{res['status'].lower()}">{res['status']}</span>
                                <span style="margin-left: 10px;">Score: <strong>{res['score']}/100</strong></span>
                                <br><br>
                                <strong>📐 Resolution:</strong> {res['metrics'].get('dimensions', 'N/A')} ({res['metrics'].get('megapixels', 0)} MP)<br>
                                <strong>🔍 Sharpness:</strong> {res['metrics'].get('sharpness_score', 'N/A')}<br>
                                <strong>📊 Noise Level:</strong> {res['metrics'].get('noise_level', 'N/A')}<br>
                                <strong>🎨 Texture:</strong> {res['metrics'].get('texture_entropy', 'N/A')}
                            </td>
                        </tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
                
                if res['errors']:
                    st.error("**REJECTION REASONS:**")
                    for err in res['errors']:
                        st.write(f"• {err}")
                
                if res['warnings']:
                    st.warning("**WARNINGS:**")
                    for warn in res['warnings']:
                        st.write(f"• {warn}")
                
                if res['master_prompt']:
                    with st.expander("🎨 AI Master Prompt (for recreation)"):
                        st.code(res['master_prompt'], language='markdown')
                
                st.markdown("---")
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    else:
        st.info("👆 Upload JPG/JPEG images to check against Adobe Stock standards")
        
        # Example
        with st.expander("💡 How to prepare images for Adobe Stock"):
            st.markdown("""
            ### Best Practices:
            1. **Resolution:** Shoot at least 12MP for cropping flexibility
            2. **Sharpness:** Use fast shutter speed, good lens
            3. **Noise:** Keep ISO low (100-400 for stock)
            4. **Editing:** Avoid over-smoothing or heavy noise reduction
            5. **Legal:** Remove all logos, blur license plates
            6. **Model Releases:** Required for recognizable people
            
            ### Common Rejection Reasons:
            - "Image is blurry or out of focus"
            - "Excessive noise or artifacts"
            - "Trademarked or copyrighted content"
            - "Poor lighting or composition"
            """)

if __name__ == "__main__":
    main()
