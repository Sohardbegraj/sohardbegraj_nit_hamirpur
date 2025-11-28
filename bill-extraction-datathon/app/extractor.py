import requests
import json
import base64
from pathlib import Path
from pdf2image import convert_from_path
import io
from PIL import Image
from typing import List, Dict
import tempfile
import os

class OllamaBillExtractor:
    def __init__(self, ollama_url="http://localhost:11434", model="llama3.2-vision:11b"):
        """
        Initialize Ollama Bill Extractor for HackRx Datathon
        
        Args:
            ollama_url: URL of Ollama server
            model: Vision model to use
        """
        self.ollama_url = ollama_url
        self.model = model
        self.api_generate = f"{ollama_url}/api/generate"
        
        # Track token usage
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        
    def reset_token_usage(self):
        """Reset token counters"""
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        
    def test_connection(self):
        """Test if Ollama server is accessible"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                available = [m['name'] for m in models]
                print(f"✅ Connected to Ollama. Available models: {available}")
                return True
            return False
        except Exception as e:
            print(f"❌ Cannot connect to Ollama: {e}")
            return False
    
    def download_document(self, url: str) -> str:
        """Download document from URL to temp file"""
        try:
            print(f"📥 Downloading document from URL...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Determine file extension
            content_type = response.headers.get('content-type', '')
            if 'pdf' in content_type or url.lower().endswith('.pdf'):
                ext = '.pdf'
            elif 'png' in content_type or url.lower().endswith('.png'):
                ext = '.png'
            elif 'jpg' in content_type or 'jpeg' in content_type or url.lower().endswith(('.jpg', '.jpeg')):
                ext = '.jpg'
            else:
                ext = '.pdf'  # default
            
            # Save to temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            temp_file.write(response.content)
            temp_file.close()
            
            print(f"✅ Downloaded to {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            print(f"❌ Error downloading document: {e}")
            raise
    
    def convert_to_images(self, file_path: str) -> List[Image.Image]:
        """Convert PDF or image to list of PIL Images"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                # Convert PDF to images
                images = convert_from_path(file_path, dpi=300)
                print(f"✅ Converted PDF to {len(images)} page(s)")
                return images
            else:
                # It's already an image
                img = Image.open(file_path)
                print(f"✅ Loaded image")
                return [img]
                
        except Exception as e:
            print(f"❌ Error converting file: {e}")
            raise
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL image to base64"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')
    
    def determine_page_type(self, page_data: Dict) -> str:
        """Determine page type based on content"""
        # Simple heuristic - you can improve this
        items = page_data.get('bill_items', [])
        
        if not items:
            return "Bill Detail"
        
        # Check for pharmacy-related items
        for item in items:
            item_name = item.get('item_name', '').lower()
            if any(word in item_name for word in ['medicine', 'tablet', 'capsule', 'syrup', 'injection']):
                return "Pharmacy"
        
        # Check if it's a final bill (usually has totals)
        if len(items) < 3:
            return "Final Bill"
        
        return "Bill Detail"
    
    def extract_from_image(self, image: Image.Image, page_num: int) -> Dict:
        """Extract bill data from a single image using Ollama"""
        
        img_base64 = self.image_to_base64(image)
        
        prompt = f"""You are analyzing page {page_num} of a medical/hospital bill. Extract ALL line items with extreme precision.

CRITICAL RULES:
1. Extract EVERY single item with its name, amount, rate, and quantity
2. Do NOT skip any entries
3. Do NOT double-count any items
4. item_name: Extract EXACTLY as written in the bill
5. item_amount: Net amount after discounts (final amount to pay for this item)
6. item_rate: Price per unit as shown
7. item_quantity: Quantity purchased

Return ONLY valid JSON (no markdown, no explanation):
{{
  "page_no": "{page_num}",
  "bill_items": [
    {{
      "item_name": "exact name from bill",
      "item_amount": 100.50,
      "item_rate": 50.25,
      "item_quantity": 2.0
    }}
  ]
}}

If no items found, return empty bill_items array.
Analyze this bill page now:"""

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [img_base64],
                "stream": False,
                "format": "json"
            }
            
            print(f"📤 Processing page {page_num}...")
            response = requests.post(self.api_generate, json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '{}')
                
                # Track token usage (Ollama doesn't provide this, so estimate)
                # Rough estimate: 1 token ≈ 4 characters
                estimated_input = len(prompt) // 4 + len(img_base64) // 1000  # Images ~1 token per KB
                estimated_output = len(response_text) // 4
                
                self.input_tokens += estimated_input
                self.output_tokens += estimated_output
                self.total_tokens += estimated_input + estimated_output
                
                # Parse JSON
                try:
                    extracted_data = json.loads(response_text)
                    print(f"✅ Page {page_num}: Found {len(extracted_data.get('bill_items', []))} items")
                    return extracted_data
                except json.JSONDecodeError:
                    print(f"⚠️  JSON parsing error on page {page_num}")
                    return {"page_no": str(page_num), "bill_items": []}
            else:
                print(f"❌ Ollama API error: {response.status_code}")
                return {"page_no": str(page_num), "bill_items": []}
                
        except Exception as e:
            print(f"❌ Error processing page {page_num}: {e}")
            return {"page_no": str(page_num), "bill_items": []}
    
    def deduplicate_items(self, all_pages: List[Dict]) -> List[Dict]:
        """Remove duplicate items across pages"""
        seen_items = set()
        deduplicated_pages = []
        
        for page in all_pages:
            unique_items = []
            for item in page.get('bill_items', []):
                # Create a unique key for the item
                item_key = (
                    item['item_name'].strip().lower(),
                    float(item['item_amount']),
                    float(item['item_rate'])
                )
                
                if item_key not in seen_items:
                    unique_items.append(item)
                    seen_items.add(item_key)
            
            page['bill_items'] = unique_items
            deduplicated_pages.append(page)
        
        return deduplicated_pages
    
    def extract_bill_data(self, document_url: str) -> Dict:
        """
        Main extraction function - returns data in HackRx format
        
        Args:
            document_url: URL to the bill document
            
        Returns:
            Dict in HackRx API format
        """
        self.reset_token_usage()
        temp_file = None
        
        try:
            print(f"\n{'='*60}")
            print(f"🔍 Processing Bill from URL")
            print(f"{'='*60}\n")
            
            # Download document
            temp_file = self.download_document(document_url)
            
            # Convert to images
            images = self.convert_to_images(temp_file)
            
            # Extract from each page
            pagewise_results = []
            for i, image in enumerate(images, 1):
                page_data = self.extract_from_image(image, i)
                
                if page_data and page_data.get('bill_items'):
                    # Add page type
                    page_data['page_type'] = self.determine_page_type(page_data)
                    pagewise_results.append(page_data)
            
            # Deduplicate items
            pagewise_results = self.deduplicate_items(pagewise_results)
            
            # Count total items
            total_items = sum(len(page.get('bill_items', [])) for page in pagewise_results)
            
            # Build response in HackRx format
            response = {
                "is_success": True,
                "token_usage": {
                    "total_tokens": self.total_tokens,
                    "input_tokens": self.input_tokens,
                    "output_tokens": self.output_tokens
                },
                "data": {
                    "pagewise_line_items": pagewise_results,
                    "total_item_count": total_items
                }
            }
            
            print(f"\n{'='*60}")
            print(f"✅ Extraction Complete!")
            print(f"   Total Pages: {len(images)}")
            print(f"   Total Items: {total_items}")
            print(f"   Token Usage: {self.total_tokens}")
            print(f"{'='*60}\n")
            
            return response
            
        except Exception as e:
            print(f"\n❌ Extraction failed: {e}")
            return {
                "is_success": False,
                "token_usage": {
                    "total_tokens": self.total_tokens,
                    "input_tokens": self.input_tokens,
                    "output_tokens": self.output_tokens
                },
                "data": {
                    "pagewise_line_items": [],
                    "total_item_count": 0
                },
                "error": str(e)
            }
        
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"🗑️  Cleaned up temp file")


# Example usage
if __name__ == "__main__":
    extractor = OllamaBillExtractor(
        ollama_url="http://localhost:11434",
        model="llama3.2-vision:11b"
    )
    
    # Test connection
    if not extractor.test_connection():
        print("Please start Ollama server first!")
        exit(1)
    
    # Test with sample URL
    sample_url = "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png?sv=2025-07-05&spr=https&..."
    
    result = extractor.extract_bill_data(sample_url)
    
    # Print result
    print(json.dumps(result, indent=2))