import time
import requests
import io

from PIL import Image
from colorama import Fore, Style, init

init(autoreset=True)

# CONFIGURATION
BASE_URL = "https://agrivision.orjnz.com/api/v1"  # Or your VPS URL
EMAIL = "farmer@example.com"
PASSWORD = "securepassword123"

def create_dummy_image(size=(3000, 4000)):
    """Creates a large 12MP dummy image to simulate raw camera output"""
    print(f"{Fore.YELLOW}Generating dummy 12MP image...{Style.RESET_ALL}")
    img = Image.new('RGB', size, color='green')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=95)
    img_byte_arr.seek(0)
    return img_byte_arr.getvalue()

def benchmark():
    session = requests.Session()
    
    print(f"\n{Fore.CYAN}=== STARTING PERFORMANCE AUDIT ==={Style.RESET_ALL}")
    
    # 1. Measure Health Check (Baseline Network Latency)
    start = time.time()
    try:
        r = session.get(f"https://agrivision.orjnz.com/health")
        latency = (time.time() - start) * 1000
        print(f"Health Check: {Fore.GREEN}{latency:.2f}ms{Style.RESET_ALL} (Status: {r.status_code})")
    except Exception as e:
        print(f"Health Check: {Fore.RED}FAILED ({e}){Style.RESET_ALL}")
        return

    # 2. Measure Auth (DB Latency)
    start = time.time()
    r = session.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    auth_latency = (time.time() - start) * 1000
    if r.status_code == 200:
        token = r.json()['access_token']
        print(f"Login/Auth:   {Fore.GREEN}{auth_latency:.2f}ms{Style.RESET_ALL}")
    else:
        print(f"Login/Auth:   {Fore.RED}FAILED {r.status_code}{Style.RESET_ALL}")
        return

    # 3. Measure Analysis Pipeline (The Heavy Lifting)
    # We test with a LARGE image to see the unoptimized impact
    image_data = create_dummy_image()
    print(f"Payload Size: {len(image_data)/1024/1024:.2f} MB")
    
    start = time.time()
    files = {'file': ('test_plant.jpg', image_data, 'image/jpeg')}
    headers = {'Authorization': f'Bearer {token}'}
    
    print("Sending Analysis Request (Upload -> MinIO -> Gemini -> DB)...")
    r = session.post(f"{BASE_URL}/analyze", files=files, headers=headers)
    
    total_time = (time.time() - start)
    
    if r.status_code == 200:
        print(f"Full Analysis Pipeline: {Fore.GREEN}{total_time:.2f} seconds{Style.RESET_ALL}")
        # Parse timing (if server sends processing time headers, otherwise calculate total)
        data = r.json()
        print(f"Diagnosis: {data['data']['diagnosis']['name']}")
    else:
        print(f"Analysis: {Fore.RED}FAILED {r.status_code}{Style.RESET_ALL} - {r.text}")

if __name__ == "__main__":
    benchmark()