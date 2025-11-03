#!/usr/bin/env python3
"""
Okul web sitesinden video indirme scripti
BigBlueButton sunum videolarını indirmek için kullanılır
"""

import requests
import os
import json
import re
from urllib.parse import urljoin, urlparse
from pathlib import Path
import sys
import time

# Selenium için opsiyonel import
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class VideoDownloader:
    def __init__(self, base_url, username=None, password=None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.username = username
        self.password = password
        
        # User-Agent ve referer header'ları ekle
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': self.base_url
        })
        
        # Eğer kullanıcı adı ve şifre varsa, oturum aç
        if username and password:
            self.login()
    
    def login(self):
        """Oturum açma işlemi"""
        base_domain = self.base_url.split('/playback')[0]
        login_urls = [
            f"{base_domain}/login",
            f"{base_domain}/login.php",
            f"{base_domain}/index.php/login",
        ]
        
        for login_url in login_urls:
            try:
                # Önce login sayfasını al (CSRF token için)
                self.session.get(login_url, timeout=10)
                
                # Login POST isteği
                response = self.session.post(login_url, data={
                    'username': self.username,
                    'password': self.password,
                    'login': 'Login',
                    'submit': 'Login'
                }, allow_redirects=True, timeout=10)
                
                if response.status_code == 200 or response.status_code == 302:
                    print(f"✓ Oturum açma denemesi başarılı: {response.status_code}")
                    return True
            except Exception as e:
                continue
        
        print(f"⚠ Oturum açma denemeleri başarısız (devam ediliyor)")
        return False
    
    def get_presentation_data_with_selenium(self):
        """Selenium ile tarayıcıyı kullanarak video URL'lerini bul"""
        if not SELENIUM_AVAILABLE:
            print("❌ Selenium bulunamadı. 'pip install selenium' ile yükleyin.")
            return [], []
        
        print("🌐 Selenium ile tarayıcı açılıyor...")
        video_urls = []
        audio_urls = []
        
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Arka planda çalış
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Network loglarını almak için performance log'ları etkinleştir
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            # Chrome WebDriver'ı dene
            try:
                driver = webdriver.Chrome(options=chrome_options)
            except Exception as e:
                # ChromeDriver bulunamazsa, alternatif yöntemler dene
                print(f"⚠ ChromeDriver bulunamadı: {e}")
                print("💡 ChromeDriver'ı yüklemek için: brew install chromedriver (macOS) veya https://chromedriver.chromium.org/")
                return [], []
            
            try:
                print("📡 Sayfa yükleniyor...")
                driver.get(self.base_url)
                
                # Sayfanın yüklenmesini bekle
                time.sleep(5)
                
                # Video elementlerini bul
                print("🔍 Video elementleri aranıyor...")
                video_elements = driver.find_elements(By.TAG_NAME, 'video')
                source_elements = driver.find_elements(By.TAG_NAME, 'source')
                
                # Video elementlerinden src'leri al
                for video in video_elements:
                    src = video.get_attribute('src')
                    if src and ('video' in src.lower() or 'deskshare' in src.lower() or 'camera' in src.lower()):
                        if src.startswith('/'):
                            full_url = urljoin(self.base_url, src)
                        else:
                            full_url = src
                        if full_url not in video_urls:
                            video_urls.append(full_url)
                
                # Source elementlerinden src'leri al
                for source in source_elements:
                    src = source.get_attribute('src')
                    if src:
                        if src.startswith('/'):
                            full_url = urljoin(self.base_url, src)
                        else:
                            full_url = src
                        if 'video' in full_url.lower() and full_url not in video_urls:
                            video_urls.append(full_url)
                        elif 'audio' in full_url.lower() and full_url not in audio_urls:
                            audio_urls.append(full_url)
                
                # Network loglarından video URL'lerini bul
                print("📊 Network trafiği analiz ediliyor...")
                logs = driver.get_log('performance')
                for log in logs:
                    try:
                        message = json.loads(log['message'])['message']
                        if message['method'] == 'Network.responseReceived':
                            url = message['params']['response']['url']
                            content_type = message['params']['response'].get('headers', {}).get('content-type', '')
                            
                            # Video veya ses dosyalarını bul
                            if any(ext in url.lower() for ext in ['.webm', '.mp4', '.ogg', '.mp3']):
                                if 'video' in content_type.lower() or 'video' in url.lower():
                                    if url not in video_urls:
                                        video_urls.append(url)
                                elif 'audio' in content_type.lower() or 'audio' in url.lower():
                                    if url not in audio_urls:
                                        audio_urls.append(url)
                    except:
                        pass
                
                # JavaScript execution ile video URL'lerini bul
                try:
                    js_video_urls = driver.execute_script("""
                        var videos = [];
                        document.querySelectorAll('video').forEach(function(video) {
                            if (video.src) videos.push(video.src);
                            video.querySelectorAll('source').forEach(function(source) {
                                if (source.src) videos.push(source.src);
                            });
                        });
                        return videos;
                    """)
                    for url in js_video_urls:
                        if url.startswith('/'):
                            full_url = urljoin(self.base_url, url)
                        else:
                            full_url = url
                        if 'video' in full_url.lower() and full_url not in video_urls:
                            video_urls.append(full_url)
                except:
                    pass
                
            finally:
                driver.quit()
            
            return video_urls, audio_urls
            
        except Exception as e:
            print(f"❌ Selenium hatası: {e}")
            import traceback
            traceback.print_exc()
            return [], []
    
    def get_presentation_data(self):
        """Sunum verilerini ve video URL'lerini al"""
        # Önce Selenium ile deneyelim
        if SELENIUM_AVAILABLE:
            print("🔍 Selenium ile video URL'leri aranıyor...")
            video_urls, audio_urls = self.get_presentation_data_with_selenium()
            if video_urls or audio_urls:
                return video_urls, audio_urls
            print("⚠ Selenium ile video bulunamadı, manuel yöntem deneniyor...")
        
        try:
            # Sunum HTML sayfasını al
            response = self.session.get(self.base_url)
            response.raise_for_status()
            
            html_content = response.text
            
            # HTML içeriğini kaydet (debug için)
            debug_html_path = 'downloads/page_source.html'
            Path(debug_html_path).parent.mkdir(exist_ok=True)
            with open(debug_html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"💾 HTML kaynağı kaydedildi: {debug_html_path}")
            
            # Video ve ses dosyalarını bul
            video_urls = []
            
            # video.webm veya video.mp4 araması
            video_patterns = [
                r'"(/presentation/[^"]+video\.webm)"',
                r'"(/presentation/[^"]+video\.mp4)"',
                r'"(/presentation/[^"]+deskshare\.webm)"',
                r'"(/presentation/[^"]+deskshare\.mp4)"',
                r'"video":"([^"]+video[^"]+)"',
                r'"deskshare":"([^"]+deskshare[^"]+)"',
            ]
            
            # Ses dosyaları
            audio_patterns = [
                r'"(/presentation/[^"]+audio\.ogg)"',
                r'"(/presentation/[^"]+audio\.mp3)"',
                r'"audio":"([^"]+audio[^"]+)"',
            ]
            
            # JavaScript içindeki video URL'lerini bul
            js_patterns = [
                r'["\']([^"\']*presentation[^"\']*video[^"\']*\.(webm|mp4))["\']',
                r'["\']([^"\']*presentation[^"\']*deskshare[^"\']*\.(webm|mp4))["\']',
                r'["\']([^"\']*presentation[^"\']*camera[^"\']*\.(webm|mp4))["\']',
                r'src:\s*["\']([^"\']*video[^"\']*)["\']',
                r'url:\s*["\']([^"\']*video[^"\']*)["\']',
            ]
            
            for pattern in js_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    url = match[0] if isinstance(match, tuple) else match
                    if url.startswith('/'):
                        full_url = urljoin(self.base_url, url)
                    elif url.startswith('http'):
                        full_url = url
                    else:
                        full_url = urljoin(self.base_url, '/' + url.lstrip('/'))
                    if full_url not in video_urls and 'video' in full_url.lower():
                        video_urls.append(full_url)
            
            # Video URL'lerini bul
            for pattern in video_patterns:
                matches = re.findall(pattern, html_content)
                for match in matches:
                    if match.startswith('/'):
                        full_url = urljoin(self.base_url, match)
                    else:
                        full_url = match
                    if full_url not in video_urls:
                        video_urls.append(full_url)
            
            # Ses URL'lerini bul
            audio_urls = []
            js_audio_patterns = [
                r'["\']([^"\']*presentation[^"\']*audio[^"\']*\.(ogg|mp3|webm))["\']',
                r'src:\s*["\']([^"\']*audio[^"\']*)["\']',
                r'url:\s*["\']([^"\']*audio[^"\']*)["\']',
            ]
            
            for pattern in js_audio_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    url = match[0] if isinstance(match, tuple) else match
                    if url.startswith('/'):
                        full_url = urljoin(self.base_url, url)
                    elif url.startswith('http'):
                        full_url = url
                    else:
                        full_url = urljoin(self.base_url, '/' + url.lstrip('/'))
                    if full_url not in audio_urls and 'audio' in full_url.lower():
                        audio_urls.append(full_url)
            
            for pattern in audio_patterns:
                matches = re.findall(pattern, html_content)
                for match in matches:
                    if match.startswith('/'):
                        full_url = urljoin(self.base_url, match)
                    else:
                        full_url = match
                    if full_url not in audio_urls:
                        audio_urls.append(full_url)
            
            # metadata.xml'den bilgi al
            metadata_url = urljoin(self.base_url, '/presentation/metadata.xml')
            try:
                metadata_response = self.session.get(metadata_url)
                if metadata_response.status_code == 200:
                    metadata_content = metadata_response.text
                    # metadata'dan video URL'leri çıkar
                    video_matches = re.findall(r'<video src="([^"]+)"', metadata_content)
                    for match in video_matches:
                        full_url = urljoin(self.base_url, match)
                        if full_url not in video_urls:
                            video_urls.append(full_url)
            except:
                pass
            
            # shapes.svg'den bilgi al
            shapes_url = urljoin(self.base_url, '/presentation/shapes.svg')
            try:
                shapes_response = self.session.get(shapes_url)
                if shapes_response.status_code == 200:
                    shapes_content = shapes_response.text
                    video_matches = re.findall(r'href="([^"]+video[^"]+)"', shapes_content)
                    for match in video_matches:
                        full_url = urljoin(self.base_url, match)
                        if full_url not in video_urls:
                            video_urls.append(full_url)
            except:
                pass
            
            # Bilinen video dosya yollarını doğrudan kontrol et
            common_video_paths = [
                '/presentation/video.webm',
                '/presentation/video.mp4',
                '/presentation/deskshare.webm',
                '/presentation/deskshare.mp4',
                '/presentation/camera.webm',
                '/presentation/camera.mp4',
            ]
            
            common_audio_paths = [
                '/presentation/audio.ogg',
                '/presentation/audio.mp3',
                '/presentation/audio.webm',
            ]
            
            # Video dosyalarını kontrol et (HEAD yerine GET ile küçük bir chunk al)
            for path in common_video_paths:
                test_url = urljoin(self.base_url, path)
                try:
                    # HEAD request yerine GET ile ilk byte'ı kontrol et
                    test_response = self.session.get(test_url, stream=True, timeout=10, headers={'Range': 'bytes=0-1023'})
                    if test_response.status_code in [200, 206]:  # 206 = Partial Content
                        content_type = test_response.headers.get('content-type', '')
                        # XML hatası değilse, gerçek video dosyası
                        if 'xml' not in content_type.lower():
                            if test_url not in video_urls:
                                video_urls.append(test_url)
                except Exception as e:
                    pass
            
            # Ses dosyalarını kontrol et
            for path in common_audio_paths:
                test_url = urljoin(self.base_url, path)
                try:
                    test_response = self.session.get(test_url, stream=True, timeout=10, headers={'Range': 'bytes=0-1023'})
                    if test_response.status_code in [200, 206]:
                        content_type = test_response.headers.get('content-type', '')
                        if 'xml' not in content_type.lower():
                            if test_url not in audio_urls:
                                audio_urls.append(test_url)
                except Exception as e:
                    pass
            
            # Tüm URL'leri temizle ve tekrarları kaldır
            video_urls = list(set(video_urls))
            audio_urls = list(set(audio_urls))
            
            # Bulunan URL'leri yazdır
            if video_urls:
                print(f"\n📹 Bulunan video URL'leri:")
                for url in video_urls:
                    print(f"   - {url}")
            if audio_urls:
                print(f"\n🎵 Bulunan ses URL'leri:")
                for url in audio_urls:
                    print(f"   - {url}")
            
            return video_urls, audio_urls
            
        except Exception as e:
            print(f"❌ Sunum verileri alınırken hata: {e}")
            import traceback
            traceback.print_exc()
            return [], []
    
    def download_file(self, url, output_path):
        """Dosyayı indir"""
        try:
            print(f"📥 İndiriliyor: {url}")
            
            # Referer header'ı ekle
            headers = {'Referer': self.base_url}
            response = self.session.get(url, stream=True, headers=headers, timeout=30)
            response.raise_for_status()
            
            # İlk chunk'ı oku ve XML hatası kontrolü yap
            first_chunk = next(response.iter_content(chunk_size=1024), None)
            if first_chunk:
                first_chunk_str = first_chunk.decode('utf-8', errors='ignore')
                if 'unsupportedRequest' in first_chunk_str or 'FAILED' in first_chunk_str:
                    print(f"\n❌ Bu URL desteklenmiyor: {url}")
                    return False
            
            # Dosya başlangıcını yaz
            with open(output_path, 'wb') as f:
                if first_chunk:
                    f.write(first_chunk)
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = len(first_chunk) if first_chunk else 0
                
                # Kalan içeriği indir
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r  İlerleme: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)
                        else:
                            print(f"\r  İndirilen: {downloaded} bytes", end='', flush=True)
            
            # Dosya boyutunu kontrol et
            file_size = os.path.getsize(output_path)
            if file_size < 100:  # 100 byte'dan küçükse muhtemelen hata
                print(f"\n⚠ Uyarı: Dosya çok küçük ({file_size} bytes), kontrol edin!")
            else:
                print(f"\n✓ İndirildi: {output_path} ({file_size} bytes)")
            
            return True
            
        except Exception as e:
            print(f"\n❌ İndirme hatası ({url}): {e}")
            return False
    
    def download_all(self, output_dir='downloads'):
        """Tüm videoları ve ses dosyalarını indir"""
        # Çıktı dizinini oluştur
        Path(output_dir).mkdir(exist_ok=True)
        
        print(f"🔍 Sunum verileri alınıyor...")
        video_urls, audio_urls = self.get_presentation_data()
        
        if not video_urls and not audio_urls:
            print("❌ Video veya ses dosyası bulunamadı!")
            print("💡 Manuel olarak video URL'lerini kontrol edin:")
            print(f"   {self.base_url}/presentation/")
            return
        
        print(f"\n📹 {len(video_urls)} video dosyası bulundu")
        print(f"🎵 {len(audio_urls)} ses dosyası bulundu\n")
        
        # Videoları indir
        for i, url in enumerate(video_urls, 1):
            filename = url.split('/')[-1] or f"video_{i}.webm"
            output_path = os.path.join(output_dir, filename)
            self.download_file(url, output_path)
        
        # Ses dosyalarını indir
        for i, url in enumerate(audio_urls, 1):
            filename = url.split('/')[-1] or f"audio_{i}.ogg"
            output_path = os.path.join(output_dir, filename)
            self.download_file(url, output_path)
        
        print(f"\n✅ Tüm dosyalar indirildi: {output_dir}/")


def main():
    # KULLANICI AYARLARI - Buraya kullanıcı adı ve şifrenizi girin
    USERNAME = ""  # Buraya kullanıcı adınızı yazın
    PASSWORD = ""          # Buraya şifrenizi yazın
    
    # Video URL'i
    VIDEO_URL = "https://uzemload2025-2026.gidatarim.edu.tr/playback/presentation/2.3/2eef81719994f86c8cfe36f849b031b0dd982824-1759406163000"
    
    # Çıktı dizini
    OUTPUT_DIR = "downloads"
    
    print("=" * 60)
    print("📹 Okul Video İndirici")
    print("=" * 60)
    print(f"URL: {VIDEO_URL}\n")
    
    # İndiriciyi oluştur
    downloader = VideoDownloader(
        base_url=VIDEO_URL,
        username=USERNAME if USERNAME != "kullanici_adi" else None,
        password=PASSWORD if PASSWORD != "sifre" else None
    )
    
    # İndirmeyi başlat
    downloader.download_all(output_dir=OUTPUT_DIR)
    
    print("\n" + "=" * 60)
    print("✨ İşlem tamamlandı!")
    print("=" * 60)


if __name__ == "__main__":
    main()

