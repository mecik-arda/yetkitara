"""CLI giriş noktası.

Çıkış kodları:
  0 — temiz
  1 — eşik veya üzerinde bulgu var, ya da girdi sorunu bildirildi
  2 — kullanım/girdi hatası
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from . import raporlama, tarayici
from .modeller import Onem


def _konsolu_hazirla() -> None:
    for akis in (sys.stdout, sys.stderr):
        yeniden = getattr(akis, "reconfigure", None)
        if yeniden is not None:
            try:
                yeniden(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def _esik_coz(metin: str) -> Onem:
    o = Onem.ayristir(metin)
    if o is None:
        raise argparse.ArgumentTypeError(
            f"geçersiz eşik: {metin!r}. Seçenekler: dusuk, orta, yuksek, kritik"
        )
    return o


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="yetkitara",
        description="Ajan sistem promptu ile araç şeması arasındaki yetki sözleşmesi denetçisi.",
    )
    alt = p.add_subparsers(dest="komut", required=True)

    t = alt.add_parser("tara", help="Ajan sözleşmesi dosyasını veya dizinini denetle")
    t.add_argument("hedef", help="JSON dosyası veya dizin")
    t.add_argument("--bicim", choices=("metin", "json"), default="metin")
    t.add_argument("--esik", type=_esik_coz, default=Onem.ORTA,
                   help="düşük|orta|yüksek|kritik (varsayılan: orta)")
    t.add_argument("--renksiz", action="store_true", help="ANSI renk kullanma")

    k = alt.add_parser("kurallar", help="Kural kümesini listele")
    k.add_argument("--bicim", choices=("metin", "json"), default="metin")

    return p


def _kurallari_listele(bicim: str) -> int:
    from .kurallar import KURALLAR

    if bicim == "json":
        print(__import__("json").dumps([
            {"kimlik": k.kimlik, "kural": k.ad, "onem": k.onem.name,
             "aciklama": k.aciklama, "oneriler": k.oneriler}
            for k in KURALLAR
        ], ensure_ascii=False, indent=2))
        return 0

    print(f"YetkiTara: {len(KURALLAR)} kural.\n")
    for k in KURALLAR:
        print(f"[{k.onem.name.capitalize()}] {k.kimlik}: {k.ad}")
        print(f"  {k.aciklama}")
        for i, o in enumerate(k.oneriler.split("\n")):
            print(("  Öneri: " if i == 0 else "          ") + o.strip())
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    _konsolu_hazirla()
    args = _parser().parse_args(argv)

    if args.komut == "kurallar":
        return _kurallari_listele(args.bicim)

    hedef = pathlib.Path(args.hedef)
    try:
        sonuclar, sorunlar = tarayici.tum_tara(hedef)
    except FileNotFoundError:
        print(f"Hata: hedef bulunamadı: {hedef}", file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError) as e:
        print(f"Hata: girdi okunamadı: {e}", file=sys.stderr)
        return 2

    if not sonuclar:
        print(f"Hata: {hedef} altında denetlenecek sözleşme dosyası yok", file=sys.stderr)
        return 2

    filtreli = tarayici.filtrele(sonuclar, args.esik)
    esik_ad = args.esik.name.lower().replace("ı", "i").replace("ü", "u")

    if args.bicim == "json":
        print(raporlama.json_uret(filtreli, sorunlar, taranan=sonuclar))
    else:
        print(raporlama.metin_uret(
            filtreli, sorunlar, renkli=not args.renksiz,
            taranan=sonuclar, esik_ad=esik_ad,
        ), end="")

    if sorunlar:
        return 1
    if filtreli:
        print("Risk eşiğine ulaşıldı.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
