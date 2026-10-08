"""Denetleyici — sistem promptu ile araç şemasını karşılaştırır.

Araç yalnızca okur: hiçbir dosyayı değiştirmez, ağa bağlanmaz, kod
çalıştırmaz, LLM çağırmaz. Girdi dosyasını okur ve metin üzerinde statik
karşılaştırma yapar.
"""

from __future__ import annotations

import json
import pathlib

from . import sozlesme as s
from .kurallar import KURALLAR_IDX
from .modeller import Arac, Bulgu, Sonuc, Sozlesme

ATLANACAK = frozenset({
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".ruff_cache", "build", "dist",
})

# Salt-okur rol ile birlikte tehlikeli sayılan etkiler. İçerik üretmek (yazma)
# yetki yükseltmesi değildir: analist rolünün işi özet üretmektir. Silme,
# gönderme, çalıştırma ve yetki değiştirme ise dış dünyayı etkiler.
DESTRUCTIVE = frozenset({s.SILME, s.GONDERME, s.CALISTIRMA, s.YETKI})

SISTEM_PROMPT_ANAHTARLARI = ("sistem_promptu", "sistemPrompt", "system_prompt", "systemPrompt")
ARAC_ANAHTARLARI = ("araclar", "tools", "tool_schemas", "arac_schemas")


def _arac_ayristir(ham: dict) -> Arac | None:
    ad = ham.get("name") or ham.get("ad")
    if not isinstance(ad, str) or not ad.strip():
        return None
    aciklama = ham.get("description") or ham.get("aciklama") or ""
    sema = ham.get("inputSchema") or ham.get("girdi_sema") or {}
    parametreler: set[str] = set()
    if isinstance(sema, dict):
        ozellikler = sema.get("properties")
        if isinstance(ozellikler, dict):
            parametreler = {k for k in ozellikler if isinstance(k, str)}
        elif isinstance(ozellikler, list):
            parametreler = {k for k in ozellikler if isinstance(k, str)}
        gerekli = sema.get("required")
        if isinstance(gerekli, list):
            parametreler |= {k for k in gerekli if isinstance(k, str)}
    return Arac(
        ad=ad.strip(),
        aciklama=aciklama.strip() if isinstance(aciklama, str) else "",
        parametreler=frozenset(parametreler),
        girdi_sema=json.dumps(sema, ensure_ascii=False) if sema else "",
    )


def sozlesme_ayristir(veri: dict) -> Sozlesme | None:
    """Girdi sözlüğünden sözleşmeyi kurar; eksikse None döner."""
    prompt = ""
    for anahtar in SISTEM_PROMPT_ANAHTARLARI:
        deger = veri.get(anahtar)
        if isinstance(deger, str) and deger.strip():
            prompt = deger
            break
    araclar: list[Arac] = []
    for anahtar in ARAC_ANAHTARLARI:
        liste = veri.get(anahtar)
        if isinstance(liste, list):
            for ham in liste:
                if isinstance(ham, dict):
                    arac = _arac_ayristir(ham)
                    if arac is not None:
                        araclar.append(arac)
            break
    if not prompt or not araclar:
        return None
    return Sozlesme(dosya="", sistem_promptu=prompt, araclar=tuple(araclar))


def _bulgu(kural_id: str, arac: str, kanit: str, guven: str = "orta") -> Bulgu:
    return Bulgu(
        kural=KURALLAR_IDX[kural_id],
        arac=arac,
        kanit=kanit,
        guven=guven,
    )


def denetle(sozlesme: Sozlesme) -> list[Bulgu]:
    """Sözleşmeye YTK01–YTK05 kurallarını uygular."""
    bulgular: list[Bulgu] = []
    prompt = sozlesme.sistem_promptu

    yasaklar = s.yasak_kategorileri(s._normalize(prompt))
    salt_okur = bool(s.SALT_OKUR_RE.search(s._normalize(prompt)))
    kapsam_var = bool(s.KAPSAM_RE.search(s._normalize(prompt)))
    kosullu_var = bool(s.KOSULLU_RE.search(s._normalize(prompt)))

    for arac in sozlesme.araclar:
        etkiler = s.etki_kategorileri(arac.metin)
        yuksek_etki = bool(etkiler)

        kesisen = yasaklar & etkiler
        if kesisen and not arac.onay_parametresi_var():
            eylem = ", ".join(sorted(kesisen))
            bulgular.append(_bulgu(
                "YTK01", arac.ad,
                f"prompt {eylem} yasağını içeriyor, araçta onay parametresi yok",
            ))

        if yuksek_etki and salt_okur:
            baskin = etkiler & DESTRUCTIVE
            if baskin:
                eylem = ", ".join(sorted(baskin))
                bulgular.append(_bulgu(
                    "YTK02", arac.ad,
                    f"salt-okur rol beyanı var, araç şu etkileri taşıyor: {eylem}",
                ))

        if kapsam_var and not arac.kapsam_parametresi_var():
            bulgular.append(_bulgu(
                "YTK03", arac.ad,
                "kapsam beyanı var, araçta kapsam parametresi yok",
                guven="dusuk",
            ))

        if kosullu_var and yuksek_etki and not arac.onay_parametresi_var():
            bulgular.append(_bulgu(
                "YTK04", arac.ad,
                "koşullu izin var, araçta koşul parametresi yok",
            ))

        if not arac.aciklama or (yuksek_etki and not arac.parametreler):
            eksik = "açıklama yok" if not arac.aciklama else "yüksek etkili, parametre yok"
            bulgular.append(_bulgu("YTK05", arac.ad, eksik, guven="dusuk"))

    return bulgular


def dosya_tara(dosya: pathlib.Path, kok: pathlib.Path | None = None) -> Sonuc:
    ad = dosya.name if kok is None else str(dosya.relative_to(kok))
    sonuc = Sonuc(dosya=ad)
    try:
        ham = dosya.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        sonuc.sorunlar.append(f"{ad}: okunamadı ({e.__class__.__name__})")
        return sonuc

    try:
        veri = json.loads(ham)
    except json.JSONDecodeError as e:
        sonuc.sorunlar.append(f"{ad}: JSON ayrıştırılamadı (satır {e.lineno}, sütun {e.colno})")
        return sonuc

    if not isinstance(veri, dict):
        sonuc.sorunlar.append(f"{ad}: JSON nesnesi bekleniyordu")
        return sonuc

    sozlesme = sozlesme_ayristir(veri)
    if sozlesme is None:
        eksik = []
        prompt_var = any(
            isinstance(veri.get(k), str) and veri[k].strip()
            for k in SISTEM_PROMPT_ANAHTARLARI
        )
        if not prompt_var:
            eksik.append("sistem_promptu")
        if not any(isinstance(veri.get(k), list) for k in ARAC_ANAHTARLARI):
            eksik.append("araclar")
        sonuc.sorunlar.append(f"{ad}: sözleşme eksik ({', '.join(eksik) or 'bilinmiyor'})")
        return sonuc

    sonuc.sozlesme = Sozlesme(dosya=ad, sistem_promptu=sozlesme.sistem_promptu,
                              araclar=sozlesme.araclar)
    sonuc.bulgular = denetle(sozlesme)
    return sonuc


def _adaylar(kok: pathlib.Path) -> list[pathlib.Path]:
    if kok.is_file():
        return [kok]
    return [
        p for p in sorted(kok.rglob("*.json"))
        if not ATLANACAK & set(p.relative_to(kok).parts)
    ]


def dizi_tara(kok: pathlib.Path) -> tuple[list[Sonuc], list[str]]:
    sonuclar: list[Sonuc] = []
    sorunlar: list[str] = []
    for d in _adaylar(kok):
        if d.stat().st_size > 2_000_000:
            sorunlar.append(f"{d}: 2 MB üstü, atlandı")
            continue
        sonuc = dosya_tara(d)
        sonuclar.append(sonuc)
        sorunlar.extend(sonuc.sorunlar)
    return sonuclar, sorunlar


def tum_tara(kok: pathlib.Path) -> tuple[list[Sonuc], list[str]]:
    if not kok.exists():
        raise FileNotFoundError(kok)
    return dizi_tara(kok)


def filtrele(sonuclar: list[Sonuc], esik) -> list[Sonuc]:
    out = []
    for s_ in sonuclar:
        kalan = [b for b in s_.bulgular if b.onem.value >= esik.value]
        if kalan:
            out.append(Sonuc(dosya=s_.dosya, sozlesme=s_.sozlesme,
                             bulgular=kalan, sorunlar=s_.sorunlar))
    return out
