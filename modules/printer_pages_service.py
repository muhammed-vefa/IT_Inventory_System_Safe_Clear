import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from core.database_sql import query_db

def get_printer_pages_sync(ip_address, community='public'):
    # Import inside to prevent global module loading issues
    from pysnmp.hlapi import SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity, getCmd
    
    try:
        snmpEngine = SnmpEngine()
        target = UdpTransportTarget((ip_address, 161), timeout=2, retries=1)
        
        # Try SNMP v1
        iterator = getCmd(
            snmpEngine,
            CommunityData(community, mpModel=0), # v1
            target,
            ContextData(),
            ObjectType(ObjectIdentity('1.3.6.1.2.1.43.10.2.1.4.1.1'))
        )
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        
        if errorIndication or errorStatus:
            # Fallback to v2c
            target2 = UdpTransportTarget((ip_address, 161), timeout=2, retries=1)
            iterator = getCmd(
                snmpEngine,
                CommunityData(community, mpModel=1), # v2c
                target2,
                ContextData(),
                ObjectType(ObjectIdentity('1.3.6.1.2.1.43.10.2.1.4.1.1'))
            )
            eI2, eS2, eIdx2, vB2 = next(iterator)
            if not eI2 and not eS2 and vB2:
                return int(vB2[0][1])
            return None
        else:
            if varBinds:
                return int(varBinds[0][1])
            return None
    except Exception as e:
        print(f"SNMP Error on {ip_address}: {e}")
        return None

def _run_snmp_scan_background():
    print("[PrinterPages] Starting background SNMP scan for all printers...")
    printers = query_db("SELECT pr_no, serial_no, location_code, ip FROM printers WHERE is_deleted=0 AND ip IS NOT NULL AND ip != ''")
    if not printers:
        print("[PrinterPages] No printers found with IP addresses.")
        return
    
    now = datetime.now()
    success_count = 0
    
    def process_printer(printer):
        ip = printer.get('ip')
        if not ip: return False
        
        ip = ip.strip()
        pages = get_printer_pages_sync(ip)
        
        if pages is not None:
            query = """
                INSERT INTO printer_page_logs (pr_no, serial_no, location_code, ip_address, page_count, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            try:
                query_db(query, (
                    printer.get('pr_no', ''),
                    printer.get('serial_no', ''),
                    printer.get('location_code', ''),
                    ip,
                    pages,
                    now
                ))
                return True
            except Exception as e:
                print(f"[PrinterPages] DB Insert Error for {ip}: {e}")
        return False

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(process_printer, printers))
        
    success_count = sum(1 for r in results if r)
    print(f"[PrinterPages] Scan complete. Successfully logged {success_count} out of {len(printers)} printers.")

def fetch_all_printer_pages_sync():
    """Starts the SNMP scan in a background thread and returns immediately."""
    t = threading.Thread(target=_run_snmp_scan_background)
    t.daemon = True
    t.start()
    return "Tüm yazıcılar için sayaç taraması arka planda başlatıldı."

def get_page_report(start_date_str, end_date_str):
    '''
    Belirtilen başlangıç ve bitiş tarihleri arasında (gün bazında), 
    yazıcıların o tarihlerdeki EN YAKIN loglarını alıp farklarını hesaplar.
    '''
    try:
        from collections import defaultdict
        
        query = '''
            SELECT pr_no, serial_no, location_code, ip_address, page_count, timestamp
            FROM printer_page_logs
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
        '''
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1, seconds=-1)
        
        # PyODBC is best used by passing datetime objects directly,
        # avoiding locale-specific string conversion SQL errors.
        logs = query_db(query, (start_dt, end_dt))
        
        if not logs:
            return []

        # Saf python ile gruplama
        grouped = defaultdict(list)
        for row in logs:
            pr_no = row.get('pr_no')
            if pr_no:
                grouped[pr_no].append(row)
                
        report = []
        for pr_no, group_logs in grouped.items():
            if not group_logs: continue
            
            first_record = group_logs[0]
            last_record = group_logs[-1]
            
            try:
                s_count = int(first_record.get('page_count') or 0)
            except (ValueError, TypeError):
                s_count = 0
                
            try:
                e_count = int(last_record.get('page_count') or 0)
            except (ValueError, TypeError):
                e_count = 0
            
            diff = e_count - s_count
            if diff < 0: diff = 0
            
            # handle timestamp format (only date, no time info)
            t1 = first_record.get('timestamp')
            t2 = last_record.get('timestamp')
            
            def format_date_only(t):
                if not t:
                    return '-'
                if isinstance(t, datetime):
                    return t.strftime("%d.%m.%Y")
                if isinstance(t, str):
                    for fmt in [
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M:%S.%f",
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S.%f",
                        "%d.%m.%Y %H:%M",
                        "%d.%m.%Y %H:%M:%S",
                        "%d.%m.%Y",
                        "%Y-%m-%d"
                    ]:
                        try:
                            dt = datetime.strptime(t.split('.')[0], "%Y-%m-%d %H:%M:%S")
                            return dt.strftime("%d.%m.%Y")
                        except ValueError:
                            pass
                        try:
                            dt = datetime.strptime(t, fmt)
                            return dt.strftime("%d.%m.%Y")
                        except ValueError:
                            continue
                return str(t)
            
            t1_fmt = format_date_only(t1)
            t2_fmt = format_date_only(t2)

            report.append({
                "pr_no": pr_no,
                "serial_no": last_record.get('serial_no', ''),
                "location_code": last_record.get('location_code', ''),
                "ip_address": last_record.get('ip_address', ''),
                "start_date": t1_fmt,
                "end_date": t2_fmt,
                "start_count": s_count,
                "end_count": e_count,
                "difference": diff
            })
            
        return report
    except Exception as e:
        import traceback
        err_msg = str(e)
        if not err_msg:
            err_msg = repr(e)
        print(f"[PrinterPages] Report Error: {err_msg}")
        traceback.print_exc()
        raise Exception(f"Rapor hazırlanırken hata: {err_msg}")
