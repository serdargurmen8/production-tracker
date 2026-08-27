"""
core/domain/permissions.py
-----------------------------
Rol tabanlı yetkilendirme kuralları.

Saf (I/O'suz, Streamlit'siz) bir eşleme: hangi rol hangi işlemi
yapabilir. UI ve repository katmanları sadece can(role, action)
fonksiyonunu çağırır; yeni bir rol veya yeni bir yetki eklemek
istendiğinde tek bakılacak yer burasıdır.

Roller:
    VIEWER   -> Sadece canlı ekranı görür (salt okunur).
    OPERATOR -> Canlı ekranı görür + üretim durumunu işaretler.
    PLANNER  -> OPERATOR'ün yaptığı her şeye ek olarak araya acil
                sipariş ekleyip çıkarabilir ve sipariş iptal
                edebilir (bunlar aynı "Planlama" sekmesinde).
    ADMIN    -> Her şeyi yapabilir; ayrıca günlük Excel yükler,
                kullanıcı yönetimini kontrol eder ve denetim
                (audit) kayıtlarını görüntüler.
"""

VIEWER = "VIEWER"
OPERATOR = "OPERATOR"
PLANNER = "PLANNER"
ADMIN = "ADMIN"

ROLES = [VIEWER, OPERATOR, PLANNER, ADMIN]

ROLE_LABELS = {
    VIEWER: "İzleyici",
    OPERATOR: "Operatör",
    PLANNER: "Planlamacı",
    ADMIN: "Yönetici",
}

# action -> bu action'ı yapabilecek roller kümesi
PERMISSIONS = {
    "view_live": {VIEWER, OPERATOR, PLANNER, ADMIN},
    "change_status": {OPERATOR, PLANNER, ADMIN},
    "urgent_order": {PLANNER, ADMIN},
    "cancel_order": {PLANNER, ADMIN},
    "excel_upload": {ADMIN},
    "user_management": {ADMIN},
    "view_audit_log": {ADMIN},
}


def can(role: str, action: str) -> bool:
    """
    role: kullanıcının rolü (VIEWER / OPERATOR / PLANNER / ADMIN)
    action: yapılmak istenen işlem (PERMISSIONS sözlüğündeki bir anahtar)

    Tanımsız bir action verilirse güvenli taraf seçilir: kimse
    yapamaz (boş küme -> False).
    """

    return role in PERMISSIONS.get(action, set())


def is_valid_role(role: str) -> bool:
    return role in ROLES
