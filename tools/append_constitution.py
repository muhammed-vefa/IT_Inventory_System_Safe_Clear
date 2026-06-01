import os

file_path = "C:/Users/MUHAMMED-VEFA-IS/.gemini/antigravity/scratch/IT_Inventory/mimari_rehber.md"

new_rules = """
---

## 4. GÜÇLENDİRİLMİŞ 100 MADDELİK GELİŞTİRİCİ ANAYASASI

### A. Genel Çalışma Disiplini
1. **Tek Hedef:** Her iş için tek ana hedef yazılacak. Bir promptta çoklu amaçlar (performans + arayüz + devops) birbirine karıştırılmayacak.
2. **Kapsam Sınırlandırması:** Her iş için "kapsam içi" ve "kapsam dışı" dosya listesi belirlenecek.
3. **Sıfır Tolerans:** Kapsam dışı dosya değişirse sonuç otomatik FAIL olacak. "Yanlışlıkla oldu" kabul edilmeyecek.
4. **Planlı Dokunma:** Patch öncesi hangi dosyalara dokunulacağının listesi çıkarılacak.
5. **Sapma Raporlaması:** Patch sonrası gerçekte değişen dosyalar ile planlanan dosyalar karşılaştırılıp sapmalar raporlanacak.
6. **Neden Sorusu:** "Neden şimdi bu dosyaya dokunuyoruz?" sorusuna yanıt verilemeyen değişiklikler reddedilecek.
7. **İzole Geliştirme:** Bug fix ile yeni özellik (feature) geliştirme asla aynı patchte yapılmayacak.
8. **Temizlik Ayrımı:** Temizlik (refactoring) ile fonksiyonel düzeltme aynı anda yapılmayacak.
9. **Teşhis Önceliği:** Önce teşhis konulacak, rapor üretilecek, ardından kod yazılacak (Rapor üretmeden kod yazmak yasak).
10. **Kesinlik İlkesi:** "Muhtemelen" kelimesi bir patch gerekçesi olamaz; şüphe varsa raporlanır, kesinleşirse müdahale edilir.

### B. Kanıt ve Rapor Disiplini
11. **Kök Sebep:** Her patch için kök sebep tek cümleyle özetlenecek.
12. **Dosya/Satır Kanıtı:** Her patch için dosya/satır kanıtı sunulacak ("düzelttim" demek yetmez).
13. **Davranış Kıyası:** Patchin "önceki davranışı" ve "sonraki davranışı" açıkça belirtilecek.
14. **Tablo Standardı:** Raporlarda Bulgu | Dosya | Kanıt | Risk | Öneri formatı zorunlu olacak.
15. **Net Sonuçlar:** Her sonuç raporunda PASS/FAIL ibaresi açıkça yazılacak.
16. **Eksiksiz Rapor:** Rapor eksikse, işlem sonucu "SUCCESS" olarak işaretlenemez.
17. **Zorunlu Verifier:** Sistemde verifier aracı varsa, çalıştırılmadan işlem başarılı sayılmayacak.
18. **Statik/Canlı Ayrımı:** Ajan sadece statik proof verebilir; canlı (live) test ve proof kullanıcının sorumluluğundadır.
19. **Şeffaf Hatalar:** Log, traceback veya hata çıktısı rapora olduğu gibi eklenecek, sansürlenmeyecek.
20. **Log Teyidi:** "Hata yok" demek için log kontrol kanıtı gerekecek.

### C. Git ve Rollback Güvenliği
21. **Branch Teyidi:** Her patchten önce çalışılan mevcut branch yazılacak.
22. **HEAD Hash:** Her patchten önce mevcut HEAD hash değeri kaydedilecek (Rollback için).
23. **Geri Dönüş (Rollback):** Her patch için rollback komutu veya hedefi açıkça belirtilecek.
24. **Açıklayıcı Commit:** Commit mesajları işin kapsamını net anlatacak (Örn: `fix(inventory): lazy load grouped tabs`).
25. **Belirsiz Commit Yasak:** "Update files" gibi belirsiz, çöp commit mesajları kullanılmayacak.
26. **Temiz Push:** Push öncesi `git status` temiz/planlı olmalı; beklenmeyen dosya varsa push engellenecek.
27. **Eşitlik Zorunluluğu:** Push sonrası local HEAD ile origin HEAD eşitliği kontrol edilecek.
28. **Conflict Onayı:** Push rejected (çakışma) durumunda otomatik çözüm yapılmayacak, kullanıcı onayı beklenecek.
29. **Force Push Yasak:** `git push -f` kesinlikle kırmızı çizgidir ve kullanılması yasaktır.
30. **Uncommitted Yasak:** Patchten sonra commitlenmemiş (fakat değiştirilmiş) dosya kalırsa SUCCESS raporlanmayacak.

### D. SQL ve Veri Güvenliği
31. **SELECT * Takibi:** SQL sorgularında `SELECT *` kullanımı raporlanacak ve zamanla optimize edilecek (hotspot).
32. **Fetchall Riski:** Büyük listelerde `fetchall()` kullanımı performans riski olarak işaretlenecek.
33. **DELETE Güvenliği:** SQL'de `DELETE` sorgularında `WHERE` koşulu zorunludur. Yoksa CRITICAL FAIL.
34. **Yıkıcı Komut Onayı:** `DROP`, `TRUNCATE`, `ALTER` gibi komutlar sadece açık kullanıcı onayı ile çalıştırılabilir.
35. **Migration Onayı:** Otomatik schema düzeltme ve migration önerileri kullanıcı onayına tabi olacak.
36. **Tahmin Yasak:** Kolon veya tablo isimleri tahmin edilerek yama yapılmayacak ("belki id_deletet olabilir" denmeyecek).
37. **Backward Compatibility Sınırı:** Veritabanını çorbaya çevirmemek için eski kolon adlarına yersiz geriye dönük uyumluluk eklenmeyecek.
38. **Tarih Standartı:** SQL tarih formatları sistemin geri kalanıyla (Örn: DD.MM.YYYY) uyumlu standartta olacak.
39. **Frontend Parse Güvenliği:** Frontend tarafında locale string doğrudan parse edilmeyecek.
40. **Hassas Veri Maskeleme:** `password_hash`, `bim_pass` gibi hassas alanlar response (API dönüşü) içerisinde gereksiz dönmeyecek.

### E. Auth / Yetki / Güvenlik
41. **Auth Dekoratörleri:** Test bahanesiyle auth decorator (`@require_auth`) kaldırılmayacak; sorun auth ise raporlanacak.
42. **Rol Değişmezliği:** Rol/izin davranışları normal bir patchin içinde araya sıkıştırılarak değiştirilemez.
43. **Timeout Güvenliği:** Login hızlandırma bahanesiyle session timeout (oturum süresi) gevşetilemez.
44. **Token Raporu:** Token/cookie davranışlarındaki değişiklikler güvenlik raporuna tabi olacak.
45. **Header Kontrolü:** "Bearer undefined" gibi hatalı yetkilendirme header durumları özel kontrol listesinde tutulacak.
46. **Yüksek Riskli Yamalar:** Şifre/hash alanlarına dokunan tüm yamalar "high-risk" kabul edilecek.
47. **Şifre Sızıntısı Raporu:** Kullanıcı listeleme gibi endpoint'lerde şifre dönüyorsa acilen raporlanacak.
48. **Global Admin Endpointleri:** `clear_all_data`, `backup` gibi rotalar "global admin" seviyesinde korunup ayrı raporlanacak.
49. **Security Debt:** Yetkisiz erişim ihtimali olan endpointler "security debt" (güvenlik borcu) olarak raporlanacak.
50. **XSS Kontrolü:** Kullanıcıdan gelen veriler doğrudan `innerHTML` ile tabloya basıldığında XSS riski olarak raporlanacak.

### F. Frontend ve UI Davranışı
51. **Tasarım Onayı:** CSS ve görsel tasarım değişiklikleri, kullanıcı açıkça "tasarım değiştir" demedikçe yapılmayacak.
52. **Mantık Sınırı:** UI bug düzeltmelerinde sadece veri bağlama (data-binding) ve mantık (logic) değişecek.
53. **Encode Kontrolü:** `innerHTML` kullanılırken verilerin escape/encode edilip edilmediği kontrol edilecek.
54. **Raw DOM Riski:** Raw JSON veya string verilerini (açıklama, yol vb.) doğrudan DOM elementlerine basmak engellenecek.
55. **Event Spam:** Aynı event listener'ın tekrar tekrar (duplicate) bind edilip edilmediği kontrol edilecek.
56. **API Çağrı İsrafı:** Aynı sekmeye defalarca tıklandığında gereksiz API çağrısı yapılmaması sağlanacak.
57. **Cache Politikası:** Sekme cache'leri `localStorage` yerine geçici runtime memory'de tutulacak.
58. **Hedefli Cache Silme:** Ekle/Sil/Düzenle işlemlerinden sonra sadece ilgili sekmenin cache'i (invalidate) temizlenecek.
59. **Loader Kilitlenmesi:** Frontend'deki sonsuz dönen (kilitli) loader durumları tespit edilip raporlanacak.
60. **Console Temizliği:** Browser konsolunda kırmızı hata (error) varsa yama "başarılı" kabul edilmeyecek.

### G. Performans Kuralları
61. **Ölçüm Zorunluluğu:** Performans optimizasyonlarında önce ölçüm yapılacak, tahmin yürütülmeyecek.
62. **Endpoint Sayımı:** Her yavaş ekranın arkasında kaç adet endpoint çağrısı olduğu tespit edilecek.
63. **Geçiş Maliyeti:** Sekme geçişlerinde gerçekleşen API çağrı maliyetleri raporlanacak.
64. **Duplicate Çağrılar:** Aynı endpoint'in tek tıkla 2 veya daha fazla kez çağrılması birincil öncelikli düzeltilecek.
65. **Lazy-Load:** Sekme gruplarında ve büyük verilerde lazy-load (tembel yükleme) standart hale getirilecek.
66. **Görünür Render:** Büyük tablolar render edilirken sadece "aktif sekme" verisi kadar DOM render yapılacak.
67. **Arka Plan Polling:** Arka planda periyodik ping (polling) varsa hangi ekranda neden çalıştığı belgelenecek.
68. **Zombi Polling:** Polling işlemi, ekran kapatıldıktan sonra devam ediyorsa bu bir bug kabul edilecek.
69. **DevOps Kalıntıları:** Monitoring ve devops'a ait kalıntılar, performans raporlarında ayrı bir başlıkta ele alınacak.
70. **Şema Koruma:** Sırf performans yaması yapılıyor diye SQL şeması kökten değiştirilmeyecek.

### H. Modül Sahipliği ve Mimari (Ownership)
71. **Tek Sahiplik:** Her tablo için (DB tarafında) tek bir ana "owner" (sahip) dosya/modül olacak.
72. **İzinsiz Yazma:** Bir modül, sorumluluk alanında olmayan başka bir modülün tablosuna doğrudan WRITE (Yazma) yapıyorsa bu durum raporlanacak.
73. **READ/WRITE Ayrımı:** Tablolar arası işlemlerde `READ_REFERENCE` ile `FOREIGN_WRITE` ayrımları net olacak.
74. **Read-Only Dashboard:** Dashboard (Özet) ekranı, verileri sadece özetleyen (readonly) bir yapı olacak.
75. **Dashboard Yazamaz:** Dashboard modülü üzerinden sisteme veya veritabanına doğrudan veri kaydı yapılmayacak.
76. **Envanterin Sınırı:** Envanter sekmesi sadece PC, Sıramatik/Kiosk ve Tablet'i yönetecek.
77. **Yazıcıların Sınırı:** Yazıcılar sekmesi (Printer/Peripheral) kendi cihaz gruplarını tamamen ayrı yönetecek.
78. **Servis Sınırı:** Printer Servis modülü sadece arıza ve servis kayıtlarını (logistiği) yönetecek.
79. **Bilgi Bankası Sınırı:** Bilgi bankası, notlar ve döküman alanlarının yönetiminden sorumlu olacak.
80. **Fonksiyon Taşımaları:** Modüller arası (cross-domain) büyük fonksiyon aktarımları, kullanıcı onaylı özel çıkarma (extraction) planları ile yapılacak.

### I. Dosya ve Klasör Hijyeni
81. **Root Temizliği:** Projenin root (kök) klasöründe rastgele üretilmiş yeni `.py`, `.md`, `.txt`, `.json` dosyaları kalmayacak.
82. **Geçici Scriptler:** Tüm geçici (çalıştır-at) scriptler doğrudan `tools/` klasörüne konulacak.
83. **Rapor Düzeni:** Üretilen sistem raporları `reports/` veya benzeri belirlenmiş klasörlere alınacak.
84. **Dokümantasyon:** Kullanıcıya teslim edilecek dokümanlar (rehberler) `docs/` veya root altında düzenli bir formatta tutulacak.
85. **Yedekleme Disiplini:** Veritabanı ve snapshot yedekleri doğrudan `backups/` (veya `database/`) klasöründe toplanacak.
86. **Derleme Çöpleri:** `__pycache__` ve `.pyc` gibi Python derleme dosyaları depoda tutulmayacak.
87. **Excel Kilitleri:** Excel geçici kilit dosyaları (`~$...xlsx`) takip edilip temizlenecek.
88. **Büyük Dosya Takibi:** Sistem tarafından oluşturulan gereksiz büyük boyutlu (generated) dosyalar raporlanacak.
89. **Büyük Temizlikte Rapor:** Büyük temizlik işlerinden sonra zorunlu "Klasör Hijyen Raporu" oluşturulacak.
90. **Konum Sapmaları:** Modüllerin ait oldukları klasör dışına taşınması durumunda rapor verilerek teyit alınacak.

### J. Hata Yönetimi ve Log
91. **Sessiz Geçiş Yasak:** Hataları yutan genel `try/except: pass` kullanımları yasaklanacak.
92. **Hata Yutuluyorsa Raporlanacak:** Hata gizleniyorsa bile bunun nedeni loglarda veya kod yorumlarında mutlaka belirtilecek.
93. **Boş Ekran Aciliyeti:** Kullanıcıya veri basılamayıp "boş ekran" gösteren durumlarda derhal backend ve console logları incelenecek.
94. **API Sessizliği:** Backend'den dönen API hataları frontend tarafından sessizce yutulmayacak; ekrana veya loga anlamlı bir mesaj düşürülecek.
95. **Log Kategorizasyonu:** Basit hata ayıklama (debug) mesajları ile kritik sistem hata logları (spam vs. exception) birbirinden net ayrılacak.

### K. Test ve Doğrulama
96. **Syntax Yetmezliği:** Bir dosyanın sadece syntax kontrolünden (parse) geçmesi "kod kusursuz çalışıyor" demek değildir.
97. **Mock (Sahte) Test Yasak:** Önemli testler sahte verilerle değil, gerçek endpoint'ler ve test senaryolarıyla doğrulanacak.
98. **Canlı Test Zorunluluğu:** Kullanıcı tarafından uygulanacak "Canlı Test Checklist'i" her yamadan sonra talep edilecek.
99. **Odaklı Kontrol Listesi:** Bir yamadan sonra "Kullanıcı hangi modülleri öncelikle hızlı kontrol etmeli?" listesi verilecek.
100. **Gözlem Süresi (Cooldown):** Özellikle performans ve Auth (giriş) işlemlerinden sonra sistem "hemen stabil" ilan edilmeyecek, kullanıcıdan belirli bir süre canlı ortamda gözlemlemesi istenecek.
"""

with open(file_path, "a", encoding="utf-8") as f:
    f.write(new_rules)

print("100 maddelik Anayasa eklendi!")
