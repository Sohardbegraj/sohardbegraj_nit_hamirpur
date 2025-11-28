"""
Test script to download training data and test the API
"""

import requests
import zipfile
import os
from pathlib import Path
import json
import time

# Training data URL
TRAINING_DATA_URL = "https://hackrx.blob.core.windows.net/files/TRAINING_SAMPLES.zip?sv=2025-07-05&spr=https&st=2025-11-28T06%3A47%3A35Z&se=2025-11-29T06%3A47%3A35Z&sr=b&sp=r&sig=yB8R2zjoRL2%2FWRuv7E1lvmWSHAkm%2FoIGsepj2Io9pak%3D"

# Your API endpoint
API_ENDPOINT = "http://localhost:8000/extract-bill-data"


def download_training_data():
    """Download and extract training data"""
    print("📥 Downloading training data...")
    
    # Create data directory
    data_dir = Path("data/training")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Download ZIP
    zip_path = data_dir / "TRAINING_SAMPLES.zip"
    
    if not zip_path.exists():
        response = requests.get(TRAINING_DATA_URL, stream=True)
        response.raise_for_status()
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Downloaded to {zip_path}")
    else:
        print(f"ℹ️  Training data already downloaded")
    
    # Extract ZIP
    extract_dir = data_dir / "samples"
    if not extract_dir.exists():
        print("📦 Extracting files...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"✅ Extracted to {extract_dir}")
    else:
        print(f"ℹ️  Files already extracted")
    
    return extract_dir


def test_single_file_local(file_path):
    """Test extraction with local file using extractor directly"""
    from app.extractor import OllamaBillExtractor
    
    print(f"\n{'='*60}")
    print(f"Testing: {Path(file_path).name}")
    print(f"{'='*60}")
    
    extractor = OllamaBillExtractor()
    
    # For local testing, we need to create a temporary URL or use file directly
    # Since extractor expects URL, we'll modify it to accept file path
    # Or upload to a temporary server
    
    # For now, just test API endpoint
    pass


def test_api_with_url(document_url):
    """Test API with document URL"""
    try:
        print(f"\n📤 Sending request to API...")
        print(f"   Document: {document_url[:80]}...")
        
        # Prepare request
        payload = {
            "document": document_url
        }
        
        # Send request
        start_time = time.time()
        response = requests.post(API_ENDPOINT, json=payload, timeout=300)
        processing_time = time.time() - start_time
        
        # Parse response
        result = response.json()
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"📊 Results:")
        print(f"{'='*60}")
        print(f"Status: {'✅ Success' if result['is_success'] else '❌ Failed'}")
        print(f"Processing Time: {processing_time:.2f}s")
        print(f"Total Items: {result['data']['total_item_count']}")
        print(f"Total Pages: {len(result['data']['pagewise_line_items'])}")
        print(f"Token Usage: {result['token_usage']['total_tokens']}")
        
        # Print page-wise summary
        for page in result['data']['pagewise_line_items']:
            print(f"\nPage {page['page_no']} ({page['page_type']}):")
            print(f"  Items: {len(page['bill_items'])}")
            
            # Print first 3 items
            for item in page['bill_items'][:3]:
                print(f"    - {item['item_name']}: ₹{item['item_amount']}")
            
            if len(page['bill_items']) > 3:
                print(f"    ... and {len(page['bill_items']) - 3} more items")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_all_training_samples():
    """Test all training samples"""
    extract_dir = download_training_data()
    
    # Get all PDF and image files
    files = list(extract_dir.glob("**/*.pdf")) + \
            list(extract_dir.glob("**/*.png")) + \
            list(extract_dir.glob("**/*.jpg"))
    
    print(f"\n{'='*60}")
    print(f"Found {len(files)} training files")
    print(f"{'='*60}\n")
    
    results = []
    
    for idx, file_path in enumerate(files, 1):
        print(f"\n[{idx}/{len(files)}] Processing: {file_path.name}")
        
        # For local testing, you'll need to either:
        # 1. Upload files to a temporary server
        # 2. Modify extractor to accept local file paths
        # 3. Use the actual URLs from the training data
        
        # For now, just print the file
        print(f"   File path: {file_path}")
        
        # If you have URLs for these files, test with API
        # result = test_api_with_url(url)
        # results.append(result)
    
    return results


def test_with_sample_url():
    """Test with a sample URL from the problem statement"""
    # Note: This URL might be expired, use actual URLs from training data
    sample_url = "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png?sv=2025-07-05&spr=https&..."
    
    print("Testing with sample URL from problem statement...")
    result = test_api_with_url(sample_url)
    
    if result:
        # Save result
        output_file = Path("data/outputs/sample_2_result.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n✅ Result saved to {output_file}")


def main():
    """Main test function"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║        Training Data Test Script - HackRx Datathon          ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Download training data
    extract_dir = download_training_data()
    
    print(f"\n✅ Training data ready at: {extract_dir}")
    print(f"\nNext steps:")
    print(f"1. Start Ollama: run start_ollama.bat")
    print(f"2. Start API: run start_api.bat")
    print(f"3. Run this script again to test")
    print(f"\nNote: You'll need to upload training files to a server")
    print(f"or modify the code to accept local file paths for testing.")


if __name__ == "__main__":
    main()