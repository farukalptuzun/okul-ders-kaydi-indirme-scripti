# Okul Video İndirici

Bu script, okul web sitesindeki BigBlueButton sunum videolarını indirmek için kullanılır.

## Kurulum

1. Python 3.6 veya üzeri gereklidir
2. Gerekli paketleri yükleyin:

```bash
pip install -r requirements.txt
```

## Kullanım

1. `download_video.py` dosyasını açın
2. `USERNAME` ve `PASSWORD` değerlerini kendi bilgilerinizle değiştirin
3. İsterseniz `VIDEO_URL` değerini değiştirebilirsiniz
4. Scripti çalıştırın:

```bash
python download_video.py
```

İndirilen dosyalar `downloads/` klasöründe olacaktır.

## Özellikler

- Otomatik oturum açma desteği
- Video ve ses dosyalarını otomatik bulma
- İndirme ilerleme göstergesi
- Çoklu video format desteği (webm, mp4, ogg, mp3)

## Notlar

- Eğer script video bulamazsa, tarayıcınızın geliştirici araçlarını (F12) kullanarak network sekmesinden video URL'lerini manuel olarak kontrol edebilirsiniz
- Bazı sunumlar birden fazla video segmenti içerebilir, hepsi indirilecektir

