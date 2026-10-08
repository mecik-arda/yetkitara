"""Denetleyici testleri — her YTK kuralı için en az bir test."""

import json
import pathlib
import sys
import tempfile
import unittest

PROJE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE))

from yetkitara import sozlesme as s  # noqa: E402
from yetkitara import tarayici  # noqa: E402
from yetkitara.kurallar import KURALLAR, KURALLAR_IDX  # noqa: E402
from yetkitara.modeller import Onem  # noqa: E402

ONAY = {"onay": {"type": "boolean"}}
KAPSAM = {"proje_id": {"type": "string"}}


def sozlesme_uret(prompt: str, araclar: list[dict]) -> tarayici.Sozlesme:
    return tarayici.sozlesme_ayristir({"sistem_promptu": prompt, "araclar": araclar})


def arac(ad: str, aciklama: str = "", **sema) -> dict:
    temel = {"name": ad, "description": aciklama}
    if sema:
        temel["inputSchema"] = {"type": "object", "properties": sema}
    return temel


def _yaz(veri: dict) -> tarayici.Sonuc:
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "s.json"
        p.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")
        return tarayici.dosya_tara(p, pathlib.Path(d))


def _kimlikler(prompt: str, araclar: list[dict]) -> set[str]:
    sz = sozlesme_uret(prompt, araclar)
    assert sz is not None, "sözleşme ayrıştırılamadı"
    return {b.kural.kimlik for b in tarayici.denetle(sz)}


class TestEylemKategorileri(unittest.TestCase):
    def test_yasak_negasyon_bağlami_gerektirir(self):
        izinli = "You may create, modify and delete files inside the workspace."
        self.assertEqual(s.yasak_kategorileri(izinli), set())

    def test_yasak_negasyonla_yakalanir(self):
        yasakli = "ASLA müşteri verisini silme ve değiştirme."
        self.assertEqual(s.yasak_kategorileri(yasakli), {s.SILME, s.YAZMA})

    def test_ingilizce_yasak_yakalnir(self):
        self.assertIn(s.SILME, s.yasak_kategorileri("Never delete a customer record."))

    def test_alt_dize_eslesmesi_yok(self):
        for metin in ("salt okur modunda çalış", "okur", "yapılandırılmış", "kural"):
            self.assertEqual(s.etki_kategorileri(metin), set(), metin)

    def test_etki_kategorileri_arac_adiyla(self):
        self.assertIn(s.SILME, s.etki_kategorileri("kayit_sil"))
        self.assertIn(s.GONDERME, s.etki_kategorileri("bilgi_gonder"))
        self.assertIn(s.YAZMA, s.etki_kategorileri("rapor_olustur"))


class TestYTK01(unittest.TestCase):
    def test_yasakli_eylem_onay_kapisi_yok(self):
        k = _kimlikler(
            "ASLA müşteri verisini silme.",
            [arac("musteri_sil", "Kaydı siler.", musteri_id={})],
        )
        self.assertIn("YTK01", k)

    def test_onay_kapisi_varsa_gecerli(self):
        k = _kimlikler(
            "ASLA müşteri verisini silme.",
            [arac("musteri_sil", "Kaydı siler.", musteri_id={}, **ONAY)],
        )
        self.assertNotIn("YTK01", k)

    def test_farkli_eylem_tetiklemez(self):
        k = _kimlikler(
            "ASLA müşteri verisini silme.",
            [arac("bilgi_gonder", "E-posta gönderir.", kisi_id={})],
        )
        self.assertNotIn("YTK01", k)

    def test_yasak_yoksa_gecerli(self):
        k = _kimlikler(
            "Kayıtları yönetirsin.",
            [arac("musteri_sil", "Kaydı siler.", musteri_id={})],
        )
        self.assertNotIn("YTK01", k)

    def test_dry_run_onay_kapisi_sayilir(self):
        k = _kimlikler(
            "ASLA müşteri verisini silme.",
            [arac("musteri_sil", "Kaydı siler.", musteri_id={}, dry_run={})],
        )
        self.assertNotIn("YTK01", k)


class TestYTK02(unittest.TestCase):
    def test_salt_okur_rol_ve_yikici_arac(self):
        k = _kimlikler(
            "Salt okur modunda çalış: hiçbir kaydı silme.",
            [arac("kayit_sil", "Kaydı siler.", kayit_id={})],
        )
        self.assertIn("YTK02", k)

    def test_icerik_uretme_tetiklemez(self):
        k = _kimlikler(
            "Salt okur modunda çalış. Yalnızca analiz yap.",
            [arac("ozet_olustur", "Özet metni üretir.", proje_id={})],
        )
        self.assertNotIn("YTK02", k)

    def test_rol_yoksa_gecerli(self):
        k = _kimlikler(
            "Müşteri işlemlerini yönetirsin.",
            [arac("kayit_sil", "Kaydı siler.", kayit_id={})],
        )
        self.assertNotIn("YTK02", k)


class TestYTK03(unittest.TestCase):
    def test_kapsam_beyani_parametre_yok(self):
        k = _kimlikler(
            "Yalnızca listelenen kayıtlara eriş.",
            [arac("kayit_oku", "Kaydı okur.", kayit={})],
        )
        self.assertIn("YTK03", k)

    def test_kapsam_parametresi_gecerli(self):
        k = _kimlikler(
            "Yalnızca listelenen kayıtlara eriş.",
            [arac("kayit_oku", "Kaydı okur.", **KAPSAM)],
        )
        self.assertNotIn("YTK03", k)


class TestYTK04(unittest.TestCase):
    def test_kosullu_izin_kosul_parametresi_yok(self):
        k = _kimlikler(
            "Rapor indirme ancak onay alındıktan sonra yapılabilir.",
            [arac("rapor_indir", "Raporu dışa aktarır.", dosya={})],
        )
        self.assertIn("YTK04", k)

    def test_kosul_parametresi_gecerli(self):
        k = _kimlikler(
            "Rapor indirme ancak onay alındıktan sonra yapılabilir.",
            [arac("rapor_indir", "Raporu dışa aktarır.", dosya={}, **ONAY)],
        )
        self.assertNotIn("YTK04", k)


class TestYTK05(unittest.TestCase):
    def test_aciklamasiz_arac(self):
        k = _kimlikler("Bir görev.", [arac("sehir_ara", "")])
        self.assertIn("YTK05", k)

    def test_yuksek_etkili_parametresiz(self):
        k = _kimlikler("Bir görev.", [arac("kayit_sil", "Kaydı siler.")])
        self.assertIn("YTK05", k)

    def test_semali_arac_gecerli(self):
        k = _kimlikler(
            "Bir görev.",
            [arac("kayit_sil", "Kaydı siler.", kayit_id={}, **ONAY)],
        )
        self.assertNotIn("YTK05", k)


class TestKurallarTamligi(unittest.TestCase):
    def test_kural_sayisi_bes(self):
        self.assertEqual(len(KURALLAR), 5)

    def test_kimlikler_ytk01_ytk05(self):
        for i in range(1, 6):
            self.assertIn(f"YTK{i:02d}", KURALLAR_IDX)

    def test_her_kuralin_aciklamasi_ve_onerisi_var(self):
        for k in KURALLAR:
            self.assertTrue(k.aciklama.strip(), k.kimlik)
            self.assertTrue(k.oneriler.strip(), k.kimlik)

    def test_her_kuralin_onemi_tanimli(self):
        for k in KURALLAR:
            self.assertIsInstance(k.onem, Onem)


class TestGirdiBicimi(unittest.TestCase):
    def test_bozuk_json_hata_verir(self):
        sonuc = _yaz_bozuk("{")
        self.assertTrue(sonuc.sorunlar)
        self.assertEqual(sonuc.bulgular, [])

    def test_eksik_sozlesme_hata_verir(self):
        sonuc = _yaz({"sistem_promptu": "x"})
        self.assertTrue(sonuc.sorunlar)
        self.assertIn("araclar", sonuc.sorunlar[0])

    def test_giris_bicimleri_kabul(self):
        sonuc = _yaz({
            "systemPrompt": "ASLA kayıt silme.",
            "tools": [{
                "name": "kayit_sil",
                "description": "Kaydı siler.",
                "inputSchema": {"properties": {"id": {}}},
            }],
        })
        self.assertEqual(sonuc.sorunlar, [])
        self.assertTrue(sonuc.bulgular)

    def test_cikis_kodu_sozlesmesi(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "s.json"
            p.write_text(json.dumps({
                "sistem_promptu": "Salt okur. ASLA kayıt silme.",
                "araclar": [arac("kayit_sil", "Kaydı siler.", id={})],
            }, ensure_ascii=False), encoding="utf-8")
            sonuc = tarayici.dosya_tara(p, pathlib.Path(d))
            self.assertTrue(sonuc.esik_gecer(Onem.YUKSEK))
            self.assertFalse(sonuc.esik_gecer(Onem.KRITIK))


def _yaz_bozuk(metin: str) -> tarayici.Sonuc:
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "s.json"
        p.write_text(metin, encoding="utf-8")
        return tarayici.dosya_tara(p, pathlib.Path(d))


class TestOrnekler(unittest.TestCase):
    def test_riskli_ornek_tetikler(self):
        sonuclar, _ = tarayici.dizi_tara(PROJE / "ornekler" / "riskli.json")
        kimlikler = {b.kural.kimlik for s_ in sonuclar for b in s_.bulgular}
        self.assertIn("YTK01", kimlikler)

    def test_temiz_ornek_yuksek_onem_uretmez(self):
        sonuclar, _ = tarayici.dizi_tara(PROJE / "ornekler" / "temiz.json")
        yuksek = [b for s_ in sonuclar for b in s_.bulgular
                  if b.onem.value >= Onem.YUKSEK.value]
        self.assertEqual(yuksek, [], f"temiz örnek yüksek önem üretti: {yuksek}")


class TestGurultuRegresyonu(unittest.TestCase):
    """Meşru sözleşmeler üzerindeki ölçüm sabitlenir.

    İlk sürüm 10 araçta 8 yanlış pozitif üretti. İki kök neden düzeltildi:
    alt dize eşleşmesi ve negasyon bağlamının yokluğu. Bu test, düzeltme
    geri alınırsa kırılır.
    """

    MEŞRU = [
        {
            "sistem_promptu": (
                "Sen bir destek asistanısın. Müşteri kayıtlarını oku ve soruları "
                "yanıtla. ASLA müşteri kaydını silme; silme işlemleri yalnızca "
                "yetkili operasyon ekibinin çağrısıyla yapılır."
            ),
            "araclar": [
                arac("musteri_getir", "Müşteri kaydını okur.", musteri_id={}),
                arac("musteri_sil", "Kaydı siler. Yalnızca yetkili ekip çağrısıyla.",
                     musteri_id={}, onay_ticket={}),
                arac("bilgi_gonder", "Yanıtı e-posta ile gönderir.",
                     kisi_id={}, govde={}),
            ],
        },
        {
            "sistem_pripto": "placeholder",
            "sistem_promptu": (
                "You are a coding assistant for the current workspace. You may "
                "create, modify and delete files inside the workspace. Never touch "
                "files outside the workspace. You may run tests."
            ),
            "araclar": [
                arac("dosya_yaz", "Dosyaya içerik yazar.", yol={}, icerik={}),
                arac("dosya_sil", "Dosyayı siler.", yol={}),
                arac("test_kosulur", "Test paketini çalıştırır.", hedef={}),
                arac("git_durum", "Çalışma alanı durumunu okur."),
            ],
        },
    ]

    def test_meşru_sozlesmelerde_bulgu_yok(self):
        toplam_arac = 0
        for veri in self.MEŞRU:
            sz = sozlesme_uret(veri["sistem_promptu"], veri["araclar"])
            self.assertIsNotNone(sz)
            bulgular = tarayici.denetle(sz)
            self.assertEqual(bulgular, [], f"{sz.araclar[0].ad}: {bulgular}")
            toplam_arac += len(sz.araclar)
        self.assertEqual(toplam_arac, 7)

    def test_izin_ile_yasak_ayirt_edilir(self):
        self.assertEqual(
            s.yasak_kategorileri(self.MEŞRU[1]["sistem_promptu"]), set()
        )


if __name__ == "__main__":
    unittest.main()
