from flask import Blueprint, jsonify

# Eksik olan tum modulleri burada sahte (placeholder) olarak tanimliyoruz
# Boylece main.py hata vermeden acilir.

printer_manager_bp = Blueprint('printer_manager', __name__)
@printer_manager_bp.route('/test')
def p_test(): return jsonify({"status":"ok"})

areas_manager_bp = Blueprint('areas_manager', __name__)
@areas_manager_bp.route('/test')
def a_test(): return jsonify({"status":"ok"})

notes_manager_bp = Blueprint('notes_manager', __name__)
@notes_manager_bp.route('/test')
def n_test(): return jsonify({"status":"ok"})

depot_manager_bp = Blueprint('depot_manager', __name__)
@depot_manager_bp.route('/test')
def d_test(): return jsonify({"status":"ok"})

document_service_bp = Blueprint('document_service', __name__)
@document_service_bp.route('/test')
def doc_test(): return jsonify({"status":"ok"})

logs_manager_bp = Blueprint('logs_manager', __name__)
@logs_manager_bp.route('/test')
def l_test(): return jsonify({"status":"ok"})

mahal_manager_bp = Blueprint('mahal_manager', __name__)
@mahal_manager_bp.route('/test')
def m_test(): return jsonify({"status":"ok"})

service_manager_bp = Blueprint('service_manager', __name__)
@service_manager_bp.route('/test')
def s_test(): return jsonify({"status":"ok"})

bim_service_bp = Blueprint('bim_service', __name__)
@bim_service_bp.route('/test')
def b_test(): return jsonify({"status":"ok"})

keyos_service_bp = Blueprint('keyos_service', __name__)
@keyos_service_bp.route('/test')
def k_test(): return jsonify({"status":"ok"})
