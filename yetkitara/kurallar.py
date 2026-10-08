"""Kural kümesi — YTK01–YTK05.

Kuralların temel önceliği: **çelişkiyi değil, eksik uygulamayı raporla.**

Bir ajanın sistem promptunda "asla silme" yazıp şemasında silme aracı
bulunması tek başına zafiyet değildir — birçok meşru tasarımda böyledir.
Raporlanabilir olan şey, yasağın **şema düzeyinde hiçbir karşılığı
bulunmamasıdır**: onay parametresi, kapsam parametresi veya rol kısıtı yoktur.
Literatür bu boşluğun ölçülmüş olduğunu gösteriyor (arXiv 2605.18414:
izin listesi ihlali %4'e iner ama sıfıra inmez, modelden modele %4–%37).
"""

from __future__ import annotations

from .modeller import Kural, Onem

KURALLAR: tuple[Kural, ...] = (
    Kural(
        kimlik="YTK01",
        ad="Yasaklı eylemin onay kapısı yok",
        onem=Onem.YUKSEK,
        aciklama=(
            "Sistem promptu yüksek etkili bir eylemi yasaklıyor, ancak şemada "
            "bu eylemi gerçekleştiren araç için onay veya kuru çalıştırma "
            "parametresi bulunmuyor. Kısıt yalnızca metinde yaşıyor."
        ),
        oneriler=(
            "Araca onay kapısı ekleyin: onay parametresi, dry_run önizlemesi veya "
            "authorize_on_behalf alanı. Kısıtı modele bırakmak yerine şema "
            "düzeyinde uygulayın."
        ),
    ),
    Kural(
        kimlik="YTK02",
        ad="Salt-okur rol, değiştirici yetenek",
        onem=Onem.YUKSEK,
        aciklama=(
            "Sistem promptu ajanı salt-okur, yalnızca analiz eden bir rol olarak "
            "tanımlıyor, ancak şemada sistem durumunu değiştiren araçlar var."
        ),
        oneriler=(
            "Rol beyanı ile yetenekleri hizalayın: ya rolü genişletin (ve "
            "aracın yüksek etkisini belgeleyin) ya da değiştirici araçları şemadan "
            "çıkarın. Salt-okur rol yalnızca okuma amaçlı araçlarla tutarlıdır."
        ),
    ),
    Kural(
        kimlik="YTK03",
        ad="Kapsam beyanı, şemada karşılıksız",
        onem=Onem.ORTA,
        aciklama=(
            "Sistem promptu erişim kapsamını daraltıyor, ancak hiçbir araç bu "
            "kapsamı taşıyan bir parametreye sahip değil. Daraltma yalnızca metinde."
        ),
        oneriler=(
            "Kapsamı şemaya taşıyın: allowed_paths, tenant, namespace, project_id "
            "gibi bir parametre. Model verilen sözleşmeyi kendiliğinden daraltamaz."
        ),
    ),
    Kural(
        kimlik="YTK04",
        ad="Koşullu izin, koşul parametresi yok",
        onem=Onem.ORTA,
        aciklama=(
            "Sistem promptu bir eylemi koşula bağlıyor (onay alındıktan sonra, "
            "teyit edilirse), ancak araç bu koşulu temsil eden bir parametre "
            "taşımıyor. Koşul doğrulanamaz."
        ),
        oneriler=(
            "Koşulu parametreleştirin: onay, teyit veya dry_run alanı. Aksi hâlde "
            "koşul, aracın çağrılma biçiminden bağımsız olarak yalnızca bir metin "
            "isteği olarak kalır."
        ),
    ),
    Kural(
        kimlik="YTK05",
        ad="Açıklamasız veya eksik şemalandırılmış araç",
        onem=Onem.DUSUK,
        aciklama=(
            "Aracın açıklaması yok ya da yüksek etkili bir araç hiçbir parametre "
            "taşımıyor. Model aracın ne yaptığını şemadan çıkaramadığı için "
            "varsayımda bulunur."
        ),
        oneriler=(
            "Aracın ne yaptığını, hangi veriye dokunduğunu ve etkisinin geri "
            "dönüşü olup olmadığını açıklamaya yazın. Yüksek etkili araçlarda "
            "parametre tanımı zorunludur."
        ),
    ),
)

KURALLAR_IDX: dict[str, Kural] = {k.kimlik: k for k in KURALLAR}
