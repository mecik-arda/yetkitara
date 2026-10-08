"""Veri sınıfları — sözleşme, araç, bulgu ve sonuç.

Sözleşme tek kaynaktan (sozlesme.py) beslenir; bu modül taşıma ve sunum katmanıdır.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Onem(Enum):
    DUSUK = 1
    ORTA = 2
    YUKSEK = 3
    KRITIK = 4

    @classmethod
    def ayristir(cls, metin: str) -> Onem | None:
        if not metin:
            return None
        try:
            return cls[metin.strip().upper().replace("İ", "I").replace("ı", "I")]
        except KeyError:
            return None


@dataclass(frozen=True)
class Arac:
    """MCP tools/list biçiminden okunan tek bir araç tanımı."""

    ad: str
    aciklama: str
    parametreler: frozenset[str] = frozenset()
    girdi_sema: str = ""

    @property
    def metin(self) -> str:
        return f"{self.ad} {self.aciklama}"

    def onay_parametresi_var(self) -> bool:
        from .sozlesme import onay_parametresi_mi

        return any(onay_parametresi_mi(p) for p in self.parametreler)

    def kapsam_parametresi_var(self) -> bool:
        from .sozlesme import kapsam_parametresi_mi

        return any(kapsam_parametresi_mi(p) for p in self.parametreler)

    def yuksek_etkili(self) -> bool:
        from . import sozlesme as s

        return bool(s.etki_kategorileri(self.metin))

    def okuma_amacli(self) -> bool:
        from . import sozlesme as s

        return bool(s.OKUMA_RE.search(s._normalize(self.ad))) and not self.yuksek_etkili()


@dataclass(frozen=True)
class Sozlesme:
    """Ajanın beyan ettiği kısıtlar ile sahip olduğu yeteneklerin çifti."""

    dosya: str
    sistem_promptu: str
    araclar: tuple[Arac, ...]

    @property
    def onay_kapisi_var(self) -> bool:
        return any(a.onay_parametresi_var() for a in self.araclar)

    @property
    def kapsam_kapisi_var(self) -> bool:
        return any(a.kapsam_parametresi_var() for a in self.araclar)


@dataclass(frozen=True)
class Kural:
    kimlik: str
    ad: str
    onem: Onem
    aciklama: str
    oneriler: str


@dataclass(frozen=True)
class Bulgu:
    kural: Kural
    arac: str
    kanit: str
    guven: str = "orta"

    @property
    def onem(self) -> Onem:
        return self.kural.onem

    def metin_satiri(self) -> str:
        return f"[{self.kural.kimlik}] {self.arac}: {self.kural.ad}"


@dataclass
class Sonuc:
    dosya: str
    sozlesme: Sozlesme | None = None
    bulgular: list[Bulgu] = field(default_factory=list)
    sorunlar: list[str] = field(default_factory=list)

    @property
    def en_yuksek_onem(self) -> Onem | None:
        if not self.bulgular:
            return None
        return max((b.onem for b in self.bulgular), key=lambda o: o.value)

    def esik_gecer(self, esik: Onem) -> bool:
        en_yuksek = self.en_yuksek_onem
        return en_yuksek is not None and en_yuksek.value >= esik.value
