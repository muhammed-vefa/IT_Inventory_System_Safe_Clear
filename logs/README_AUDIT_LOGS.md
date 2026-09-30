# Audit Log Dosyalari Kullanim Rehberi

CSV dosyalari kisa gorunebilir; bu normaldir cunku makine tarafindan doldurulacak header formatidir. Ancak her CSV icin asagidaki kullanim zorunludur.

## PATCH_LOG_TEMPLATE.csv
Her patch icin tek satir yazilir.

Zorunlu kolon mantigi:
- incident_id: Hatanin takip numarasi.
- patch_id: Patch numarasi.
- environment: local/staging/production.
- severity: LOW/MEDIUM/HIGH/CRITICAL.
- changed_files: degisen dosyalar.
- touched_symbols: etkilenen field/fonksiyon/endpoint.
- unknown_count_before/after: hard-stop sayaclari.
- suspicious_count_before/after: supheli bulgu sayaclari.
- missing_evidence_before/after: eksik kanit sayaclari.
- rollback_commit: geri donus noktasi.
- new_commit: yeni commit.
- endpoint/ui/sql/server_log test sonuclari.
- observation_window_result: patch sonrasi gozlem sonucu.

## VALIDATION_LOG_TEMPLATE.csv
Her validation fazi icin kayit tutulur:
- endpoint validation
- UI validation
- SQL validation
- Git validation
- rollback validation

## INCIDENT_LOG_TEMPLATE.csv
Hata ilk bildirildiginde acilir ve patch kapaninca kapatilir.

## Kapanis Kurali
final_status PASS olamaz eger:
- unknown_count_after > 0
- suspicious_count_after > 0
- missing_evidence_after > 0
- rollback_commit bos
- endpoint_test FAIL
- server_log_test FAIL
