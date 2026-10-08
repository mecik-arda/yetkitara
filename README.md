# yetkitara

Ajan sistem promptu ile araç şeması arasındaki **yetki sözleşmesini** denetleyen Türkçe CLI.

> Ajanınız "asla silme" diyor ve şemasında bir silme aracı var. Prompt'taki bu
> yasak, ölçülmüş olarak yetersiz kalıyor. yetkitara, kısıtın şema düzeyinde
> karşılığı olup olmadığını denetler.

Sıfır bağımlılık, çevrimdışı, salt okunur. Hiçbir dosyayı değiştirmez, ağa
bağlanmaz, kod çalıştırmaz, LLM çağırmaz.

---

## Neden var

Erişim denetimini modele devretmek yaygın bir varsayımdır — *"sistem promptuna
yaz, model uyacaktır"*. Bu varsayım ölçülmüş olarak yanlıştır:

- **arXiv 2605.18414** — açık izin listeleri prompt düzeyinde ihlali **%4'e**
  düşürüyor ama **hiçbir zaman sıfıra** iniyor; uyum modelden modele **%4–%37**
  arasında değişiyor ve genel yetenekle ilişkisi yok. MCP'nin ajanın keşfedebileceği
  ve çağırabileceği araçları kimliğe göre kısıtlayan yerleşik bir mekanizması yok.
- **HALLPERM** (AAAI SS 2026) — *"models appear compliant at the structural level
  while exhibiting unsafe intent"*: şema ihlali nadirdir (%0,78), güvensiz niyet
  yaygındır (%65,95). Sertleştirilmiş sistem prompt'u şema ihlalini düşürür ama
  niyeti hiç düşürmez.
- **arXiv 2606.20023** — prompt düzeyindeki kontroller aşırı yetkili araç
  seçimini yeterince sınırlamıyor.

Bu çalışmaların ortak bulgusu: **beyan edilen kısıt ile verilen yetenek
arasındaki boşluk ölçülebilir ve kapatılabilir.** yetkitara bu boşluğu dağıtım
öncesinde raporlar.

---

## Girdi sözleşmesi

Ajan sözleşmesi iki parçadan oluşur ve JSON olarak verilir:

```json
{
  "sistem_promptu": "Sen bir destek asistanısın. ASLA müşteri kaydını silme.",
  "araclar": [
    {
      "name": "musteri_sil",
      "description": "Müşteri kaydını siler.",
      "inputSchema": {
        "type": "object",
        "properties": { "musteri_id": { "type": "string" } },
        "required": ["musteri_id"]
      }
    }
  ]
}
```

`systemPrompt` / `tools` / `tool_schemas` anahtarları da kabul edilir. Araçlar
MCP `tools/list` biçimindedir (`name`, `description`, `inputSchema`).

---

## Denetlenenler

| Kimlik | Kural | Seviye |
|---|---|---|
| YTK01 | Prompt'ta yasaklanan bir eylemi yapan araçta onay kapısı (onay, dry_run, onay_ticket) yok | Yüksek |
| YTK02 | Salt-okur rol beyanı var, ancak şemada silme/gönderme/çalıştırma/yetki değiştiren araç var | Yüksek |
| YTK03 | Prompt kapsamı daraltıyor, ancak hiçbir araç kapsam parametresi (proje_id, tenant, yol) taşımıyor | Orta |
| YTK04 | Prompt bir eylemi koşula bağlıyor (onay alındıktan sonra), araçta koşul parametresi yok | Orta |
| YTK05 | Araç açıklamasız ya da yüksek etkili olup parametresiz | Düşük |

### Raporlanan şey çelişki değil, eksik uygulamadır

Bir ajanın promptunda "asla silme" yazıp şemasında silme aracı bulunması tek
başına zafiyet değildir; birçok meşru tasarımda böyledir. Raporlanabilen olan,
yasağın **şema düzeyinde hiçbir karşılığı bulunmamasıdır**: onay parametresi,
kapsam parametresi veya rol kısıtı yoktur.

Bu ayrım bilinçlidir. Kural, "tasarım gerginliği"ni değil, "gerginliği kapatacak
mekanizmanın yokluğunu" raporlar.

### Eylem eşleştirmesi

Yasak ve araç etkisi **ayrı ayrı eylem kategorilerine** çevrilir, yalnızca
kesişen eylem raporlanır. Prompt'ta silme yasaklanmışsa, gönderme yapan araç
için YTK01 üretilmez.

| Kategori | Araç etkisi örnekleri |
|---|---|
| silme | `delete`, `remove`, `sil`, `kaldır`, `revoke` |
| gönderme | `send`, `export`, `download`, `gönder`, `yayınla`, `indir` |
| yazma | `write`, `create`, `update`, `oluştur`, `güncelle` |
| çalıştırma | `exec`, `deploy`, `çalıştır`, `başlat` |
| yetki | `grant`, `credential`, `yetki`, `izinlendir` |

### Negasyon bağlamı

Yasağın **olumsuzlama içeren cümlede** geçmesi gerekir:

- `"ASLA müşteri verisini silme"` → yasak algılanır
- `"You may create, modify and delete files"` → **izin**, yasak değildir

Aynı mantık araç tarafında da uygulanır: bir aracın açıklaması *"sistem durumunu
değiştirmez"* diyorsa, bu yan cümle etki hesabına katılmaz.

---

## Kurulum

```bash
git clone https://github.com/mecik-arda/yetkitara
cd yetkitara
pip install .
```

Kurulum olmadan da çalışır:

```bash
python -m yetkitara.cli tara sozlesme.json
```

---

## Kullanım

```bash
# Tek sözleşme
yetkitara tara sozlesme.json

# Dizin, makine okunur çıktı
yetkitara tara ajanlar/ --bicim json

# CI için yalnızca yüksek önem
yetkitara tara sozlesme.json --esik yuksek

# Kural kümesini göster
yetkitara kurallar
yetkitara kurallar --bicim json
```

Örnek çıktı:

```text
YetkiTara: 1 sözleşme, 4 araç, 8 bulgu (1 sözleşme eşiği geçti).
Eşik: yuksek (altındaki bulgular gizlendi).

[Yüksek] riskli.json — musteri_sil · Yasaklı eylemin onay kapısı yok
  Kanıt: prompt silme yasağını içeriyor, araçta onay parametresi yok
  Güven: orta
  Öneri: Araca onay kapısı ekleyin: onay parametresi, dry_run önizlemesi veya
          authorize_on_behalf alanı. Kısıtı modele bırakmak yerine şema
          düzeyinde uygulayın.
Risk eşiğine ulaşıldı.
```

**Çıkış kodları**

| Kod | Anlam |
|---|---|
| `0` | Temiz |
| `1` | Eşik veya üzerinde bulgu var, ya da girdi sorunu bildirildi |
| `2` | Girdi veya kullanım hatası |

---

## Gürültü ölçümü

Kurallar meşru tasarımlar üzerinde sınandı — destek asistanı, kod inceleyici ve
geniş yetkili kodlama asistanı sözleşmeleri.

| Sürüm | Ölçüm |
|---|---|
| İlk | 10 araçta **8 yanlış pozitif** |
| Eylem bazlı eşleştirme sonrası | 10 araçta 3 bulgu |
| Negasyon bağlamı + katlama sonrası | **10 araçta 0 bulgu** |

İki kök neden düzeltildi ve `tests/test_denetleme.py` içinde
`TestGurultuRegresyonu` ile sabitlendi:

1. **Alt dize eşleşmesi** — `kur` deseni "oKUResinde" eşleşiyordu; araç adlarındaki
   alt çizgi `\b` sınırını bozuyordu.
2. **Negasyon bağlamının yokluğu** — `"you MAY delete"` bir izin metniydi, yasak
   olarak okunuyordu. Aynı hata araç açıklamalarında da vardı (*"değiştirmez"*).

**Ders:** kurallar kendi örneklerinde değil, meşru tasarımlarda sınanmalıdır.

---

## Rakipler ve fark

Bu alan dolu; işte dürüst konumlandırma.

- **[lethal-trifecta-lint](https://github.com/fevziegeyurtsevenler/lethal-trifecta-lint)**
  — ölümcül üçlü zincirini denetler. **Fark:** yetkitara dağıtım öncesi
  *beyan/izin* tutarlılığını denetler; üçlü çalışma zamanı tehlikesidir.
- **[agent-security-ci](https://github.com/fevziegeyurtsevenler/agent-security-ci)**
  — ajan güvenlik adımlarını CI'a bağlar. **Fark:** bu bir CI orkestrasyon
  paketidir, sözleşme içeriğini denetlemez.
- **[agent-scan](https://github.com/snyk/agent-scan)**, **[Cisco MCP Scanner](https://github.com/cisco-ai-defense/mcp-scanner)**
  — MCP sunucularını ve araç açıklamalarını hedefler. **Fark:** bunlar sunucu
  tarafını inceler; yetkitara ajanın **kendi sözleşmesini** (prompt + şema)
  birlikte okur.
- **[İzKalkan](https://github.com/mecik-arda/izkalkan)** — çağrı izinde PII ve dış
  iletişim riski. **Fark:** çalışma zamanı izine bakar; yetkitara dağıtım
  öncesi statik sözleşmeye bakar. İkisi birbirinin yerine geçmez.
- **Elle inceleme** — bir sözleşmeyi gözden geçirmek mümkündür ama 4 aracın
  12 sözleşmesinde elle kapsam kaybı olur. **Fark:** mekanik, tekrarlanabilir,
  CI'a bağlanır.

---

## Güvenlik modeli

- Araç **yalnızca okur** — dosyayı değiştirmez, ağa bağlanmaz, kod
  çalıştırmaz, LLM çağırmaz.
- Araç **asla otomatik engelleme yapmaz**. Bir bulgu bir **risk göstergesidir**,
  kesin gerçek değildir; insan doğrulaması şarttır.
- Statik metin analizi **yaklaşıktır**. Yasağın algılanması dilbilimsel bir
  tahmindir: `kapsam`, `koşul` ve `onay` kavramları doğal dilde ifade edildiği
  için kalıplar bunların bir kısmını yakalar, tamamını değil.
- Bir bulgu, sözleşmede **kapatılması gereken bir boşluğun olduğunu** gösterir;
  modelin o anda ihlal edeceğini iddia etmez.
- Araç yalnızca **yetkilendirilmiş** çalışmalarda ve kendi ajan
  sözleşmelerinizde kullanılmalıdır.

---

## Sınırlamalar

- **Çalışma zamanı davranışını ölçmez.** Bulgu, modelin verilen araçla ne
  yapacağını test etmez; yalnızca şemanın neyi mümkün kıldığını raporlar.
- **Negasyon algısı cümle düzeyindedir.** "Şunu yapma, şunu yap" gibi tek
  cümlede geçen çelişkiler doğru ayrıştırılamayabilir.
- **Yetenekleri aracın adı ve açıklamasından çıkarır.** Gerçek `inputSchema`
  kısıtları (`enum`, `readOnly`, `x-destructive`) desteklenir ancak öncelik
  metne verilir.
- **İleriye dönük eşleme yapmaz.** Şemadaki bir aracın çalışma zamanında gerçekten
  ne yaptığını izlemez.
- **Ajan mimarisinin tamamını kapsamaz.** Çok ajanlı sistemlerde ajanlar arası
  yetki devri ve bellek aktarımı denetlenmez.

---

## Geliştirme

```bash
python -m unittest discover -s tests -v
ruff check .
```

32 test: her YTK kuralı için en az bir test, eylem kategorileri, negasyon
ayrımı, giriş biçimleri, çıkış kodu sözleşmesi ve **meşru sözleşmelerde sıfır
bulgu** regresyonu.

---

## Lisans

[MIT](LICENSE) — Arda Meçik

Bu proje, Türkçe yapay zeka güvenliği kaynak listesi
[awesome-ai-security-tr](https://github.com/fevziegeyurtsevenler/awesome-ai-security-tr)
ekojisisteminе katkı kapsamında geliştirilmiştir.

## Sorumluluk reddi

Bu araç yalnızca yetkilendirilmiş güvenlik çalışmalarında ve kendi ajan
sözleşmelerinizde kullanılmalıdır. Denetlenen sözleşmelerin güvenli olduğu
sonucuna varılmaz; yalnızca incelenmesi gereken boşlukları işaretler.