"""
Adobe Stock Extreme Quality Auditor
Senior Python Developer & AI Image Specialist
Strict Calibration - Zero Tolerance for Adobe Rejection Triggers
"""

import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import pytesseract
import re
import io
import base64
from skimage import exposure, filters, measure
from skimage.morphology import disk
from skimage.filters.rank import entropy
import pandas as pd
from datetime import datetime
import json
import os
import tempfile
from collections import defaultdict
import hashlib

# Configure Tesseract path (update for your OS)
# Windows: r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Mac: '/usr/local/bin/tesseract'
# Linux: '/usr/bin/tesseract'
try:
    if os.name == 'nt':  # Windows
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    else:  # Mac/Linux
        pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'
except:
    st.warning("Tesseract OCR not found. Install from https://github.com/tesseract-ocr/tesseract")

# Page configuration
st.set_page_config(
    page_title="Adobe Stock Extreme Auditor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional UI
st.markdown("""
<style>
    /* Main container */
    .main {
        background-color: #0e1117;
    }
    
    /* Status tags */
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
    
    /* Cards and containers */
    .audit-card {
        background-color: #1e1e2e;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #ffffff;
    }
    
    /* Metrics */
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        color: #ffffff;
    }
    
    .metric-label {
        font-size: 12px;
        color: #888888;
    }
    
    /* Table styling */
    .stDataFrame {
        background-color: #1e1e2e;
    }
    
    /* Button styling */
    .stButton button {
        background-color: #ff4b4b;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 8px 16px;
    }
    
    .stButton button:hover {
        background-color: #ff6b6b;
    }
</style>
""", unsafe_allow_html=True)

class AdobeStockExtremeAuditor:
    """Strict Adobe Stock image auditor with zero tolerance for quality issues"""
    
    # Adobe Stock minimum requirements (stricter than official)
    MIN_MEGAPIXELS = 4.0  # 4 MP absolute minimum
    MIN_WIDTH = 1920
    MIN_HEIGHT = 1080
    
    # Sharpness thresholds (extreme strictness)
    LAPLACIAN_ACCEPTED = 60.0   # Very sharp
    LAPLACIAN_RISKY = 30.0      # Soft but maybe acceptable
    LAPLACIAN_REJECTED = 30.0    # Below this = blurry reject
    
    # Artifact detection thresholds
    WAXY_SKIN_THRESHOLD = 0.85   # High smoothness = waxy
    ENTROPY_THRESHOLD = 4.5      # Low entropy = over-smoothing
    
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
        """Check resolution meets 4MP minimum"""
        h, w = self.image.shape[:2]
        megapixels = (w * h) / 1_000_000
        self.results['metrics']['megapixels'] = round(megapixels, 2)
        self.results['metrics']['dimensions'] = f"{w}x{h}"
        
        if megapixels < self.MIN_MEGAPIXELS:
            self.results['errors'].append(f"❌ Low Resolution: {megapixels:.2f}MP (< {self.MIN_MEGAPIXELS}MP)")
            return False
        elif megapixels < 5.0:
            self.results['warnings'].append(f"⚠️ Borderline Resolution: {megapixels:.2f}MP")
        return True
    
    def check_sharpness_laplacian(self):
        """
        Extremely strict sharpness check using 10x10 grid analysis
        Rejects soft focus images aggressively
        """
        h, w = self.gray.shape
        grid_h = h // 10
        grid_w = w // 10
        
        variances = []
        for i in range(10):
            for j in range(10):
                y1, y2 = i * grid_h, (i + 1) * grid_h
                x1, x2 = j * grid_w, (j + 1) * grid_w
                cell = self.gray[y1:y2, x1:x2]
                if cell.size > 0:
                    laplacian = cv2.Laplacian(cell, cv2.CV_64F)
                    variance = laplacian.var()
                    variances.append(variance)
        
        avg_variance = np.mean(variances) if variances else 0
        min_variance = np.min(variances) if variances else 0
        
        self.results['metrics']['sharpness_score'] = round(avg_variance, 2)
        self.results['metrics']['min_sharpness'] = round(min_variance, 2)
        
        if avg_variance < self.LAPLACIAN_REJECTED:
            self.results['errors'].append(f"❌ Blurry / Soft Focus: Sharpness={avg_variance:.1f} (< {self.LAPLACIAN_REJECTED})")
            return False
        elif avg_variance < self.LAPLACIAN_ACCEPTED:
            self.results['warnings'].append(f"⚠️ Risky Sharpness: {avg_variance:.1f} (Acceptable: {self.LAPLACIAN_ACCEPTED}+)")
            return 'risky'
        return True
    
    def detect_gibberish_ai_text(self):
        """
        Critical: Detect AI-generated gibberish text using OCR
        Looks for nonsense symbols, random character combinations
        """
        try:
            # Preprocess for better OCR
            _, thresh = cv2.threshold(self.gray, 150, 255, cv2.THRESH_BINARY_INV)
            
            # OCR configuration for strict detection
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            text = pytesseract.image_to_string(thresh, config=custom_config)
            
            # Patterns of AI gibberish
            gibberish_patterns = [
                r'[^a-zA-Z0-9\s]{3,}',  # 3+ non-alphanumeric in a row
                r'[A-Z]{5,}',           # 5+ uppercase letters (likely fake text)
                r'[a-z]{8,}',           # 8+ lowercase without spaces
                r'\b[A-Za-z0-9]{15,}\b', # Long random strings
                r'[0-9]{6,}',           # Long number sequences
                r'[^\x00-\x7F]+'        # Non-ASCII characters
            ]
            
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) < 3:
                    continue
                    
                for pattern in gibberish_patterns:
                    if re.search(pattern, line):
                        # Additional check: if it doesn't look like real words
                        words = re.findall(r'[A-Za-z]+', line)
                        if words:
                            # Check if words have weird vowel-consonant patterns
                            for word in words:
                                if len(word) > 6:
                                    # AI often creates repetitive or impossible patterns
                                    if len(set(word)) < len(word) * 0.3:
                                        self.results['errors'].append(f"❌ Gibberish AI Text Found: '{line[:50]}'")
                                        return False
                                    
                        if len(line) > 5:
                            self.results['errors'].append(f"❌ Gibberish AI Text Found: '{line[:50]}'")
                            return False
            
            # Check for random character clusters (common in AI images of screens)
            char_clusters = re.findall(r'[A-Za-z0-9]{4,}', text)
            for cluster in char_clusters:
                if cluster.isupper() and len(cluster) > 8:
                    self.results['errors'].append(f"❌ Suspicious Text Pattern: '{cluster}'")
                    return False
                    
            return True
            
        except Exception as e:
            st.warning(f"OCR error: {str(e)}")
            return True  # Don't reject if OCR fails, but log warning
    
    def detect_waxy_skin_and_artifacts(self):
        """
        Detect over-smoothing (waxy skin effect) and artifacts
        Common in AI-generated images
        """
        # Calculate local entropy (low entropy = over-smoothed)
        entropy_img = entropy(self.gray, disk(5))
        avg_entropy = np.mean(entropy_img)
        
        self.results['metrics']['entropy'] = round(avg_entropy, 2)
        
        if avg_entropy < self.ENTROPY_THRESHOLD:
            self.results['errors'].append(f"❌ Waxy Skin / Over-Smoothing: Entropy={avg_entropy:.2f}")
            return False
        
        # Check for JPEG artifacts
        _, jpeg_encoded = cv2.imencode('.jpg', self.image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        jpeg_size = len(jpeg_encoded)
        original_size = self.image.nbytes
        
        compression_ratio = original_size / jpeg_size
        if compression_ratio > 20:
            self.results['warnings'].append("⚠️ High Compression Artifacts Detected")
        
        # Detect unnatural gradients (AI artifact)
        gray_float = self.gray.astype(np.float32) / 255.0
        gradient_x = np.abs(np.gradient(gray_float, axis=1))
        gradient_y = np.abs(np.gradient(gray_float, axis=0))
        gradient_anomaly = np.std(gradient_x) / (np.mean(gradient_x) + 1e-6)
        
        if gradient_anomaly > 5.0:
            self.results['warnings'].append("⚠️ Unnatural Gradients (Possible AI Artifact)")
        
        return True
    
    def detect_logos_and_branding(self):
        """
        Detect potential logos, watermarks, and brand text using OCR
        """
        try:
            # Enhanced preprocessing for text detection
            _, thresh = cv2.threshold(self.gray, 100, 255, cv2.THRESH_BINARY)
            text = pytesseract.image_to_string(thresh).lower()
            
            # Common brand patterns
            brand_patterns = [
                r'\b(?:nike|adidas|apple|google|microsoft|amazon|facebook|instagram|twitter|youtube|disney|sony|samsung|lg|hp|dell|ibm|cisco|oracle|salesforce|adobe|canon|nikon|fujifilm|panasonic|philips|ge|honeywell|siemens|bosch|mercedes|bmw|audi|tesla|ford|toyota|honda)\b',
                r'®',
                r'™',
                r'©',
                r'\ball rights reserved\b',
                r'watermark',
                r'copyright'
            ]
            
            for pattern in brand_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    self.results['errors'].append(f"❌ Logo/Brand Detected: '{matches[0]}'")
                    return False
            
            # Check for watermarks in corner regions (common placement)
            h, w = self.gray.shape
            corners = [
                self.gray[0:h//8, 0:w//8],           # Top-left
                self.gray[0:h//8, -w//8:],            # Top-right
                self.gray[-h//8:, 0:w//8],            # Bottom-left
                self.gray[-h//8:, -w//8:]             # Bottom-right
            ]
            
            for corner in corners:
                _, corner_thresh = cv2.threshold(corner, 200, 255, cv2.THRESH_BINARY)
                corner_text = pytesseract.image_to_string(corner_thresh).lower()
                if any(keyword in corner_text for keyword in ['stock', 'photo', 'shutterstock', 'getty', 'adobe']):
                    self.results['errors'].append("❌ Stock Watermark Detected")
                    return False
                    
            return True
            
        except Exception as e:
            return True  # Don't reject on OCR error
    
    def extract_subject_from_filename(self):
        """Intelligent subject extraction from filename"""
        filename = os.path.basename(self.image_path)
        name_without_ext = os.path.splitext(filename)[0]
        
        # Clean and parse filename
        name_clean = re.sub(r'[_-]+', ' ', name_without_ext)
        words = name_clean.lower().split()
        
        # Subject mapping (common Adobe Stock subjects)
        subjects = {
            'doctor': 'Female Doctor',
            'nurse': 'Nurse',
            'patient': 'Patient',
            'business': 'Business Professional',
            'woman': 'Woman',
            'man': 'Man',
            'person': 'Person',
            'tablet': 'Tablet User',
            'laptop': 'Laptop User',
            'phone': 'Smartphone User',
            'computer': 'Computer User',
            'office': 'Office Worker',
            'medical': 'Medical Professional',
            'healthcare': 'Healthcare Worker'
        }
        
        for key, value in subjects.items():
            if key in name_clean.lower():
                self.results['subject'] = value
                return value
        
        self.results['subject'] = 'Person'  # Default
        return 'Person'
    
    def generate_master_prompt(self):
        """
        Generate ultra-detailed AI master prompt for recreation
        Includes all detected issues to avoid them
        """
        subject = self.results['subject']
        metrics = self.results['metrics']
        
        # Base prompt structure
        base_prompt = f"Master Prompt for {subject}:\n\n"
        
        # Quality specifications
        quality_specs = [
            "8K resolution, ultra-sharp focus, crystal clear details",
            "Cinematic lighting, professional studio quality",
            "Natural skin texture, no smoothing or waxy appearance",
            "Clean, readable text (no gibberish characters)",
            "No logos, watermarks, or branded elements",
            "Natural gradients, no AI artifacts"
        ]
        
        # Add specific corrections based on detected issues
        corrections = []
        if 'Blurry' in str(self.results['errors']):
            corrections.append("CRITICAL: Ensure razor-sharp focus, no softness")
        if 'Waxy' in str(self.results['errors']):
            corrections.append("CRITICAL: Natural skin texture, visible pores, no smoothing")
        if 'Gibberish' in str(self.results['errors']):
            corrections.append("CRITICAL: Only use real, readable English text")
        if 'Logo' in str(self.results['errors']):
            corrections.append("CRITICAL: No branding or logos anywhere")
        
        # Scene description
        scene = f"A professional {subject.lower()} in a modern healthcare/office environment"
        
        # Technical specs
        technical = "Shot on ARRI Alexa 65, Zeiss Master Prime lenses, f/2.8, ISO 800, natural skin preservation"
        
        # Compile full prompt
        full_prompt = f"""{base_prompt}
SUBJECT: {scene}

QUALITY REQUIREMENTS:
{chr(10).join(f'• {req}' for req in quality_specs)}

CORRECTIONS NEEDED:
{chr(10).join(f'• {corr}' for corr in corrections) if corrections else '• None - image meets basic standards'}

TECHNICAL SPECIFICATIONS:
• {technical}
• Resolution: 8K+ (7680x4320 minimum)
• Aspect Ratio: 16:9 or 3:2
• Sharpness: Laplacian variance > 60
• No post-processing smoothing

COMPOSITION:
• Eye-level angle
• Professional attire
• Natural expressions
• Clean, uncluttered background
• Authentic environment

RENDERING INSTRUCTIONS:
Generate with extreme attention to texture authenticity, text readability, and natural lighting. Avoid all AI-typical artifacts (waxy skin, gibberish text, deformed geometry)."""
        
        self.results['master_prompt'] = full_prompt
        return full_prompt
    
    def calculate_audit_score(self):
        """Calculate overall audit score (0-100)"""
        score = 100
        score -= len(self.results['errors']) * 25  # Major deduction per error
        score -= len(self.results['warnings']) * 10  # Minor deduction per warning
        
        # Sharpness bonus/penalty
        sharpness = self.results['metrics'].get('sharpness_score', 0)
        if sharpness > 80:
            score += 10
        elif sharpness < 30:
            score -= 30
            
        # Resolution bonus
        megapixels = self.results['metrics'].get('megapixels', 0)
        if megapixels > 8:
            score += 5
        elif megapixels < 4.5:
            score -= 15
            
        return max(0, min(100, score))
    
    def run_full_audit(self):
        """Execute complete audit pipeline"""
        if not self.load_image():
            self.results['passed'] = False
            self.results['score'] = 0
            return self.results
        
        # Run all checks (order matters for dependency)
        checks = [
            ('Resolution', self.check_resolution),
            ('Sharpness', self.check_sharpness_laplacian),
            ('Gibberish Text', self.detect_gibberish_ai_text),
            ('Artifacts', self.detect_waxy_skin_and_artifacts),
            ('Logos', self.detect_logos_and_branding)
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            result = check_func()
            if result is False:
                all_passed = False
            elif result == 'risky' and all_passed:
                all_passed = 'risky'
        
        # Determine final status
        if all_passed is True and len(self.results['errors']) == 0:
            self.results['passed'] = True
            status = "ACCEPTED"
        elif all_passed == 'risky' or len(self.results['warnings']) > 0:
            self.results['passed'] = False
            status = "RISKY"
        else:
            self.results['passed'] = False
            status = "REJECTED"
        
        # Extract subject and generate prompt
        self.extract_subject_from_filename()
        self.generate_master_prompt()
        
        # Calculate final score
        self.results['score'] = self.calculate_audit_score()
        self.results['status'] = status
        
        return self.results

def create_thumbnail(image_path, size=(100, 100)):
    """Create base64 thumbnail for display"""
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
    st.title("🔍 Adobe Stock Extreme Quality Auditor")
    st.markdown("*Professional AI-Powered Image Audit for Stock Photography*")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Audit Settings")
        st.markdown("**Extreme Strict Mode: ON**")
        st.markdown("""
        - ✅ Minimum 4.0 Megapixels
        - ✅ Sharpness threshold: 60+
        - ✅ AI gibberish detection
        - ✅ Waxy skin analysis
        - ✅ Logo/brand scanning
        """)
        
        st.markdown("---")
        st.markdown("### 📊 Audit Standards")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Accepted", "60+", "Sharpness")
        with col2:
            st.metric("Risky", "30-60", "Soft Focus")
        with col3:
            st.metric("Rejected", "<30", "Blurry")
        
        st.markdown("---")
        st.markdown("### 📋 Instructions")
        st.info("""
        1. Upload JPG/JPEG images
        2. Wait for automatic audit
        3. Review detailed results
        4. Copy AI master prompts
        5. Fix issues and re-upload
        """)
    
    # Main content
    uploaded_files = st.file_uploader(
        "📤 Upload Images for Audit",
        type=['jpg', 'jpeg', 'JPG', 'JPEG'],
        accept_multiple_files=True,
        help="Multiple images allowed. Strict Adobe Stock standards applied."
    )
    
    if uploaded_files:
        # Save uploaded files temporarily
        temp_dir = tempfile.mkdtemp()
        image_paths = []
        
        for uploaded_file in uploaded_files:
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            image_paths.append(temp_path)
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Audit each image
        audit_results = []
        
        for idx, img_path in enumerate(image_paths):
            status_text.text(f"Auditing {os.path.basename(img_path)}...")
            
            auditor = AdobeStockExtremeAuditor(img_path)
            results = auditor.run_full_audit()
            
            # Add thumbnail and filename
            results['filename'] = os.path.basename(img_path)
            results['thumbnail'] = create_thumbnail(img_path)
            results['file_size'] = os.path.getsize(img_path) / 1024  # KB
            
            audit_results.append(results)
            
            progress_bar.progress((idx + 1) / len(image_paths))
        
        status_text.text("Audit complete!")
        progress_bar.empty()
        
        # Display results dashboard
        st.markdown("## 📊 Audit Results Dashboard")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        accepted = sum(1 for r in audit_results if r['status'] == "ACCEPTED")
        risky = sum(1 for r in audit_results if r['status'] == "RISKY")
        rejected = sum(1 for r in audit_results if r['status'] == "REJECTED")
        
        with col1:
            st.metric("Total Images", len(audit_results))
        with col2:
            st.metric("✅ Accepted", accepted, delta=f"{accepted/len(audit_results)*100:.0f}%")
        with col3:
            st.metric("⚠️ Risky", risky)
        with col4:
            st.metric("❌ Rejected", rejected)
        
        st.markdown("---")
        
        # Detailed results table
        st.markdown("### 📋 Detailed Audit Report")
        
        # Prepare dataframe
        df_data = []
        for res in audit_results:
            df_data.append({
                'File': res['filename'],
                'Score': f"{res['score']}/100",
                'Status': res['status'],
                'Megapixels': res['metrics'].get('megapixels', 'N/A'),
                'Sharpness': res['metrics'].get('sharpness_score', 'N/A'),
                'Errors': len(res['errors']),
                'Warnings': len(res['warnings'])
            })
        
        df = pd.DataFrame(df_data)
        
        # Color-coded status display
        def color_status(val):
            if val == 'ACCEPTED':
                return 'background-color: #00ff9d20; color: #00ff9d'
            elif val == 'RISKY':
                return 'background-color: #ffb44320; color: #ffb443'
            else:
                return 'background-color: #ff444420; color: #ff4444'
        
        st.dataframe(
            df.style.applymap(color_status, subset=['Status']),
            use_container_width=True,
            height=400
        )
        
        st.markdown("---")
        
        # Detailed results for each image
        st.markdown("### 🔬 Individual Image Analysis")
        
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
                            <td style="width: 120px; vertical-align: top;">
                                <img src="{res['thumbnail']}" style="border-radius: 8px;" />
                            </td>
                            <td style="vertical-align: top;">
                                <h3>{res['filename']}</h3>
                                <span class="status-{'accepted' if res['status'] == 'ACCEPTED' else 'risky' if res['status'] == 'RISKY' else 'rejected'}">
                                    {res['status']}
                                </span>
                                <span style="margin-left: 10px;">Score: <strong>{res['score']}/100</strong></span>
                                <br><br>
                                <strong>📐 Resolution:</strong> {res['metrics'].get('dimensions', 'N/A')} ({res['metrics'].get('megapixels', 0)} MP)<br>
                                <strong>🔍 Sharpness:</strong> {res['metrics'].get('sharpness_score', 'N/A')} (Min: {res['metrics'].get('min_sharpness', 'N/A')})<br>
                                <strong>🎨 Entropy:</strong> {res['metrics'].get('entropy', 'N/A')} (Natural texture indicator)<br>
                            </td>
                        </tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
                
                # Error log
                if res['errors']:
                    st.error("**❌ REJECTION REASONS:**")
                    for error in res['errors']:
                        st.write(f"• {error}")
                
                # Warning log
                if res['warnings']:
                    st.warning("**⚠️ RISK WARNINGS:**")
                    for warning in res['warnings']:
                        st.write(f"• {warning}")
                
                # Master prompt
                if res['master_prompt']:
                    with st.expander("🎨 View Master AI Prompt for Perfect Recreation"):
                        st.code(res['master_prompt'], language='markdown')
                        
                        # Copy button functionality
                        col1, col2 = st.columns([1, 5])
                        with col1:
                            if st.button("📋 Copy Prompt", key=f"copy_{res['filename']}"):
                                st.write("✅ Copied to clipboard!")
                                st.markdown(f"""
                                <script>
                                navigator.clipboard.writeText({repr(res['master_prompt'])});
                                </script>
                                """, unsafe_allow_html=True)
                
                st.markdown("---")
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    else:
        # Empty state
        st.info("👆 Upload JPG/JPEG images to begin the extreme quality audit")
        
        # Show example of what the tool detects
        with st.expander("📖 What this tool detects (Adobe Stock standards)"):
            st.markdown("""
            ### ✅ Pass Criteria:
            - Resolution > 4.0 Megapixels
            - Sharpness score > 60 (Laplacian variance)
            - Natural skin texture (entropy > 4.5)
            - No text or readable real text only
            - No logos, watermarks, or branding
            - Natural gradients and lighting
            
            ### ❌ Auto-Reject Triggers:
            - **Soft focus / blurry** (Sharpness < 30)
            - **AI gibberish text** (nonsensical characters)
            - **Waxy skin effect** (over-smoothing)
            - **Logos or brand names** (OCR detected)
            - **Watermarks** in corners
            - **Low resolution** (< 4 MP)
            - **High compression artifacts**
            
            ### 🎯 AI Master Prompts:
            For each rejected image, the tool generates an ultra-detailed prompt (8K, cinematic, sharp) to recreate the image perfectly without any detected errors.
            """)

if __name__ == "__main__":
    main()
