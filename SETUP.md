# Kurulum Kılavuzu

## 1. Python Paketlerini Yükleyin

```bash
pip install -r requirements.txt
```

## 2. Chrome WebDriver Kurulumu (Selenium için)

Selenium kullanmak için Chrome WebDriver gereklidir.

### macOS:

```bash
brew install chromedriver
```

veya manuel olarak:
1. https://chromedriver.chromium.org/downloads adresinden Chrome sürümünüze uygun driver'ı indirin
2. İndirilen dosyayı `/usr/local/bin` klasörüne taşıyın

### Linux:

```bash
sudo apt-get install chromium-chromedriver
```

veya manuel olarak:
1. https://chromedriver.chromium.org/downloads adresinden driver'ı indirin
2. `/usr/local/bin` klasörüne kopyalayın

### Windows:

1. https://chromedriver.chromium.org/downloads adresinden driver'ı indirin
2. ChromeDriver.exe dosyasını PATH'e ekleyin veya script ile aynı klasöre koyun

## Alternatif: Tarayıcıdan Cookie Kullanma

Eğer Selenium kurulumu zorsa, tarayıcınızdan cookie'leri alıp kullanabilirsiniz:

1. Chrome'da F12 ile Developer Tools'u açın
2. Network sekmesine gidin
3. Video sayfasını açın
4. Bir video dosyası isteğine tıklayın (ör. video.webm)
5. Headers sekmesinde "Cookie" değerini kopyalayın
6. Script içinde cookie'yi kullanın

## 3. Scripti Çalıştırın

```bash
python download_video.py
```

