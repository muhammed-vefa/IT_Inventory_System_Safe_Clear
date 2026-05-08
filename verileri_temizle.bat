@echo off
title IT Envanter - SQL Veri Temizleme
echo DİKKAT: Bu işlem tüm veritabanı kayıtlarını silecektir!
pause
set PYTHONPATH=.
python scratch/clear_sql_data.py
pause
