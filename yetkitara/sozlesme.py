"""Girdi sözleşmesinin TEK kaynağı.

Ajan sözleşmesi iki parçadan oluşur:

  * sistem promptu — ajanın beyan ettiği kısıtlar ve rol (düz metin)
  * araç şeması   — ajana verilen yetenekler (MCP tools/list biçimi)

Denetleyici bu ikisini karşılaştırır.

TASARIM DERSİ: İlk sürümde kalıplar sözcük sınırı olmadan yazılmıştı ve
olasılık dili ("yol açabilir", "çalıştırılabilir") ile gerçek eylem birbirine
karışıyordu. Gerçekçi sözleşmelerde ölçüldüğünde 10 araçta 8 yanlış pozitif
üretti. İki kök neden düzeltildi:

  1. Alt dize eşleşmesi — "kur" deseni "oKUResinde" eşleşiyordu. Tüm
     kalıplar artık sözcük sınırı kullanır.
  2. Yasağın negasyon bağlamı yoktu — "you MAY delete" bir izindir, yasak
     değildir. Yalnızca olumsuzlama bağlamında geçen eylemler yasak sayılır.
"""

import re

# --- Sözcük sınırlı yardımcı ---------------------------------------------------

# Türkçe ve İngilizce ekler için güvenli sınır: harf/rakam değil olan yer.
# "oluştur" kalıbı "oluşturmak" ve "oluşturulması" biçimlerini de yakalamalıdır.
def _son(s: str) -> str:
    return rf"{s}\w*"


# --- Eylem kategorileri ---------------------------------------------------------

SILME = "silme"
GONDERME = "gonderme"
YAZMA = "yazma"
CALISTIRMA = "calistirma"
YETKI = "yetki"

# Bir aracın taşıdığı etkiler. ARAÇ adı + açıklaması üzerinden eşleştirilir.
#
# Türkçe ve ASCII yazım birlikte verilir: gerçek araç şemalarında `kayit_sil`
# ve `kayıt_sil` aynı ölçüde yaygındır, yalnızca birini kabul etmek diğerini
# görünmez kılar.
ETKI_KATEGORILERI: dict[str, re.Pattern[str]] = {
    SILME: re.compile(
        r"\b(?:delete|remove|destroy|drop|purge|truncate|unlink|rmdir|revoke|"
        r"sil\w*|kald\w*|sifirla\w*)\b",
        re.IGNORECASE,
    ),
    GONDERME: re.compile(
        r"\b(?:send|mail|notify|webhook|share|export|publish|download|"
        r"gonder\w*|yayinla\w*|paylas\w*|indir\w*|disa aktar\w*)\b",
        re.IGNORECASE,
    ),
    YAZMA: re.compile(
        r"\b(?:write|update|patch|insert|create|edit|modify|append|upsert|"
        r"yaz\w*|guncelle\w*|olustur\w*|olushtur\w*|duzenle\w*|degistir\w*)\b",
        re.IGNORECASE,
    ),
    CALISTIRMA: re.compile(
        r"\b(?:exec|execute|shell|spawn|command|deploy|restart|rebuild|"
        r"calistir\w*|yurut\w*|baslat\w*|dagit\w*)\b",
        re.IGNORECASE,
    ),
    YETKI: re.compile(
        r"\b(?:grant|permission|allowlist|credential|api key|api key|"
        r"yetki\w*|izinlendir\w*|yetkilendir\w*)\b",
        re.IGNORECASE,
    ),
}

OKUMA_RE = re.compile(
    r"\b(?:list|get|read|search|query|fetch|find|describe|inspect|view|show|"
    r"lookup|count|stat|oku\w*|listele\w*|goster\w*|ara|sorgula\w*|getir|"
    r"incele\w*|bul)\b",
    re.IGNORECASE,
)

# --- Yasağın negasyon bağlamı ----------------------------------------------------

# Bir cümlede olumsuzlama bulunduğunda, o cümledeki eylemler yasak kabul edilir.
# Bu olmadan "you may delete" bir yasak olarak okunur.
OLUMSUZLAMA_RE = re.compile(
    r"(?:\b(?:never|do not|don t|must not|mustn t|cannot|can t|may not|"
    r"not allowed|avoid|refuse|prohibit\w*|forbidden|disallow\w*|"
    r"asla|hicbir|hic|kesinlikle|yasak\w*|gerekmez|istemiyoruz)\b"
    r"|\byapma\b"
    r"|\bolmaz\b"
    r"|\b\w{3,}(?:mez|maz)\b)",
    re.IGNORECASE,
)

CUMLE_BOLUCU = re.compile(r"[.!?;\n]")


# Yasağın eyleme göre kategorisi — cümle bağlamıyla birlikte uygulanır.
YASAK_KATEGORILERI: dict[str, re.Pattern[str]] = {
    SILME: re.compile(
        r"\b(?:sil\w*|delete\w*|remove\w*|kald\w*)\b", re.IGNORECASE
    ),
    GONDERME: re.compile(
        r"\b(?:gonder\w*|ilet\w*|paylas\w*|yayinla\w*|disa aktar\w*|"
        r"send\w*|share\w*|export\w*)\b",
        re.IGNORECASE,
    ),
    YAZMA: re.compile(
        r"\b(?:yaz\w*|degistir\w*|duzenle\w*|guncelle\w*|olustur\w*|olushtur\w*|"
        r"ekle\w*|write\w*|update\w*|modify\w*|create\w*|edit\w*)\b",
        re.IGNORECASE,
    ),
    CALISTIRMA: re.compile(
        r"\b(?:calistir\w*|yurut\w*|baslat\w*|exec\w*|execute\w*)\b",
        re.IGNORECASE,
    ),
    YETKI: re.compile(
        r"\b(?:yetki\w*|izin\w*|yetkilendir\w*|grant\w*|permission\w*)\b",
        re.IGNORECASE,
    ),
}

# --- Rol ve kapsam beyanı --------------------------------------------------------

SALT_OKUR_RE = re.compile(
    r"(?:\b(?:salt okur|read only|readonly|only read|salt okuma)\b"
    r"|\b(?:yalnizca|sadece|only)\s+(?:oku|analiz|incele|raporla|bilgi ver|okuma)"
    r"|\bdegisiklik\s+(?:yapma|yapmay\w*)"
    r"|\bhicbir\s+(?:dosya|kayit|veri)\s+(?:degistirme|silme))",
    re.IGNORECASE,
)

KAPSAM_RE = re.compile(
    r"(?:\b(?:yalnizca|sadece|only|restricted to)\s+"
    r"(?:su|bu|the|listed|specified|given|belirtilen|listelenen|verilen|kayitlar\w*|"
    r"kayitlara|sadece)"
    r"|\bkapsam\w*\s+(?:sinirli|darl|daralt\w*)"
    r"|\bverilen\s+proje\w*)",
    re.IGNORECASE,
)

KOSULLU_RE = re.compile(
    r"(?:\bonay\s+(?:alindiktan|aldiktan|verildikten|alinirsa|alirsa)"
    r"|\bteyit\s+(?:edildiginde|aldiktan|alinirsa|verilirse)"
    r"|\bkullanici\s+(?:onay|teyit)"
    r"|\bonay\s+olmadan"
    r"|\bonaylanmadan"
    r"|\bonay\s+dolmadan"
    r"|\bonay\s+alinmadan"
    r"|\btespit\s+edildikten\s+sonra"
    r"|\bonly\s+(?:after|once)\s+(?:approval|confirm)\w*)",
    re.IGNORECASE,
)

# --- Araca ait eşleşmeler ---------------------------------------------------------
#
# Parametre adları kesirle karşılaştırılır. `onay_ticket` için "onay" segmenti,
# `proje_id` için "proje" segmenti eşleşir; `.*_` öneki kullanılmaz çünkü
# son segment yerine tüm adı hedefler ve yanlış bölünmeler üretir.

ONAY_SEGMENTLER = frozenset({
    "confirm", "confirmation", "confirmed", "ack", "acknowledge", "acknowledged",
    "approved", "approval", "preview", "onay", "onayla", "onaylandi",
    "teyit", "kabul", "izni", "izin",
})

KAPSAM_SEGMENTLER = frozenset({
    "scope", "allowed", "tenant", "namespace", "project", "repo", "branch",
    "workspace", "root", "workdir", "working", "dir", "path", "filter",
    "where", "limit", "kapsam", "izinli", "yol", "dizin", "calisma",
    "proje", "musteri", "kullanici",
})

_AYIRICI_RE = re.compile(r"[_\-.]")


def _segmentler(ad: str) -> set[str]:
    return {s for s in _AYIRICI_RE.split(ad.lower()) if s}


def onay_parametresi_mi(ad: str) -> bool:
    s = _segmentler(ad)
    if s & ONAY_SEGMENTLER:
        return True
    return "dryrun" in ad.lower().replace("_", "").replace("-", "")


def kapsam_parametresi_mi(ad: str) -> bool:
    return bool(_segmentler(ad) & KAPSAM_SEGMENTLER)


# --- Yardımcılar ----------------------------------------------------------------

_DIYAKRITIK = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "I": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u", "â": "a", "î": "i",
})


def _normalize(metin: str) -> str:
    """Ayrıcıları ve Türkçe diyakritiklerini sadeleştirir.

    İki gerekçe birleşiyor:

    1. Araç adları kayıt_sil biçiminde alt çizgi kullanır; Python'da `_` bir
       sözcük karakteri olduğu için `\\bsil\\w*` deseni "kayıt_sil" içinde
       eşleşmez. Ayırıcıları boşluğa çevirmek bunu çözer.
    2. Gerçek sözleşmeler hem Türkçe (silme) hem ASCII (silme) yazım
       karışık taşır. Diyakritikleri katlamak, kalıpların ASCII biçimde
       kalmasını ve iki yazımı da yakalamasını sağlar.
    3. Cümle bölücü `[.!?;\\n]` ile çalıştığı için NOKTA boşluğa
       çevrilmez. Nokta silinirse "You may delete" ile "Never touch" aynı
       cümle sayılır ve bir izin yanlışlıkla yasak olarak okunur.

    Returns:
        Katlanmış metin.
    """
    return metin.replace("_", " ").replace("-", " ").translate(_DIYAKRITIK)


def etki_kategorileri(metin: str) -> set[str]:
    """Aracın taşıdığı etkiler.

    Araç açıklamaları ne yapmadığını da yazar ("sistem durumunu değiştirmez").
    Olumsuzlama içeren yan cümleler çıkarılmadan tarama yapılırsa araç kendi
    güvenlik özelliğinden dolayı suçlanır.
    """
    duz = _normalize(metin)
    bulunan: set[str] = set()
    for yan in CUMLE_BOLUCU.split(duz):
        if OLUMSUZLAMA_RE.search(yan):
            continue
        for k, rx in ETKI_KATEGORILERI.items():
            if rx.search(yan):
                bulunan.add(k)
    return bulunan


def yasak_kategorileri(metin: str) -> set[str]:
    """Yalnızca olumsuzlama içeren cümlelerdeki eylemleri yasak sayar.

    "You may delete files inside the workspace" bir izindir ve burada yasak
    olarak sayılmaz; yalnızca aynı cümlede olumsuzlama varsa dikkate alınır.
    """
    bulunan: set[str] = set()
    for cumle in CUMLE_BOLUCU.split(_normalize(metin)):
        if not OLUMSUZLAMA_RE.search(cumle):
            continue
        for k, rx in YASAK_KATEGORILERI.items():
            if rx.search(cumle):
                bulunan.add(k)
    return bulunan
