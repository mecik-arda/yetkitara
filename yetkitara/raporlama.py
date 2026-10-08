"""Çıktı üretimi — Türkçe metin ve makine okunur JSON.

Her iki biçim de aynı Sonuc listesinden türer; metin çıktısında görünen her
bulgu JSON'da da bulunur.
"""

from __future__ import annotations

import json

from .modeller import Onem, Sonuc

RENKLER = {
    Onem.KRITIK: "\033[1;31m",
    Onem.YUKSEK: "\033[0;31m",
    Onem.ORTA: "\033[0;33m",
    Onem.DUSUK: "\033[0;36m",
}
SIFIRLA = "\033[0m"

_ONEM_ADI = {
    Onem.KRITIK: "Kritik",
    Onem.YUKSEK: "Yüksek",
    Onem.ORTA: "Orta",
    Onem.DUSUK: "Düşük",
}


def metin_uret(
    bulgulu: list[Sonuc],
    sorunlar: list[str],
    renkli: bool = True,
    taranan: list[Sonuc] | None = None,
    esik_ad: str = "",
) -> str:
    kaynak = taranan if taranan is not None else bulgulu
    toplam_bulgu = sum(len(s.bulgular) for s in kaynak)
    toplam_arac = sum(len(s.sozlesme.araclar) for s in kaynak if s.sozlesme)
    baslik = f"YetkiTara: {len(kaynak)} sözleşme, {toplam_arac} araç"

    satirlar: list[str] = []
    if toplam_bulgu == 0:
        satirlar.append(f"{baslik}, 0 bulgu.")
    else:
        satirlar.append(f"{baslik}, {toplam_bulgu} bulgu ({len(bulgulu)} sözleşme eşiği geçti).")
    if esik_ad:
        satirlar.append(f"Eşik: {esik_ad} (altındaki bulgular gizlendi).")
    satirlar.append("")

    for sonuc in bulgulu:
        for b in sonuc.bulgular:
            onem_ad = _ONEM_ADI[b.onem]
            if renkli:
                onem_ad = f"{RENKLER[b.onem]}{onem_ad}{SIFIRLA}"
            satirlar.append(f"[{onem_ad}] {sonuc.dosya} — {b.arac} · {b.kural.ad}")
            satirlar.append(f"  Kanıt: {b.kanit}")
            satirlar.append(f"  Güven: {b.guven}")
            for i, o in enumerate(b.kural.oneriler.split("\n")):
                onek = "  Öneri: " if i == 0 else "          "
                satirlar.append(onek + o.strip())
            satirlar.append("")

    if sorunlar:
        satirlar.append("Atlanan veya okunamayan girdiler:")
        for s_ in sorted(set(sorunlar)):
            satirlar.append(f"  Uyarı: {s_}")
        satirlar.append("")

    return "\n".join(satirlar).rstrip() + "\n"


def json_uret(
    bulgulu: list[Sonuc],
    sorunlar: list[str],
    taranan: list[Sonuc] | None = None,
) -> str:
    kaynak = taranan if taranan is not None else bulgulu
    veri = {
        "arac": "yetkitara",
        "sonuc": {
            "sozlesme_sayisi": len(kaynak),
            "arac_sayisi": sum(len(s.sozlesme.araclar) for s in kaynak if s.sozlesme),
            "bulgu_sayisi": sum(len(s.bulgular) for s in kaynak),
            "raporlanan_sozlesme": len(bulgulu),
            "en_yuksek_onem": (
                _ONEM_ADI[max((b.onem for s in kaynak for b in s.bulgular),
                              key=lambda o: o.value)]
                if any(s.bulgular for s in kaynak) else None
            ),
        },
        "sozlesmeler": [
            {
                "dosya": s.dosya,
                "arac_sayisi": len(s.sozlesme.araclar) if s.sozlesme else 0,
                "araclar": (
                    [{"ad": a.ad, "parametre_sayisi": len(a.parametreler)}
                     for a in s.sozlesme.araclar]
                    if s.sozlesme else []
                ),
                "bulgular": [
                    {
                        "kimlik": b.kural.kimlik,
                        "onem": _ONEM_ADI[b.onem],
                        "arac": b.arac,
                        "kural": b.kural.ad,
                        "aciklama": b.kural.aciklama,
                        "kanit": b.kanit,
                        "guven": b.guven,
                        "oneriler": b.kural.oneriler,
                    }
                    for b in s.bulgular
                ],
            }
            for s in bulgulu
        ],
        "sorunlar": sorted(set(sorunlar)),
    }
    return json.dumps(veri, ensure_ascii=False, indent=2)
