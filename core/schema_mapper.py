class SchemaMapper:
    """Sistem genelindeki isimlendirme karmaşasını tek merkezden çözer."""
    
    # DB -> Internal Mapping
    FIELD_MAP = {
        'arizali': 'is_faulty',
        'is_deleted': 'is_archived',
        'recorded_device_no': 'pc_no',
        'seri_no': 'serial_number'
    }

    # Internal -> UI Mapping
    DISPLAY_MAP = {
        'is_faulty': 'Arıza Durumu',
        'is_archived': 'Arşivlendi',
        'pc_no': 'Bağlı Cihaz'
    }

    @staticmethod
    def map_to_internal(db_row):
        """Veritabanı satırını standart iç formata çevirir."""
        new_row = {}
        for k, v in db_row.items():
            mapped_key = SchemaMapper.FIELD_MAP.get(k, k)
            new_row[mapped_key] = v
        return new_row

    @staticmethod
    def map_to_db(internal_data):
        """İç veriyi veritabanı sütun isimlerine çevirir."""
        db_data = {}
        # Reverse map
        reverse_map = {v: k for k, v in SchemaMapper.FIELD_MAP.items()}
        for k, v in internal_data.items():
            mapped_key = reverse_map.get(k, k)
            db_data[mapped_key] = v
        return db_data
