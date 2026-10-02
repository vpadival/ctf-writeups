# _BISIM_HIKAYE

**Category:** Misc  
**Difficulty:** Easy  
**Points:** 300

## Challenge Description

We are given a photograph of a rural mountain settlement containing traditional houses, reddish-orange tiled roofs, a mosque/minaret, and a winding road.

The goal is to determine where the photograph was taken and submit the answer in the following format:

```text
cyberweek{city_country}
```

Special Turkish characters are supposed to be simplified. For example:

```text
ü -> u
ş -> s
ğ -> g
```

---

## Initial Analysis

From the image alone, several characteristics suggested that the location was somewhere in **Türkiye**:

- Red clay-tiled roofs
- Closely packed rural houses
- Mountainous and forested terrain
- A prominent mosque minaret
- Traditional Anatolian village architecture

The challenge name `_BISIM_HIKAYE` also appeared Turkish.

Initially, I investigated **İzmir** because **BİSİM** is associated with İzmir. However, submissions based on İzmir were incorrect, meaning the challenge title alone was not enough to determine the intended location.

---

## Reverse Image Search

Instead of relying only on visual geolocation, I performed reverse-image searches using several services:

- TinEye
- Yandex Images
- Bing Visual Search
- Google Lens

These searches produced much stronger matches and eventually connected the photograph to reporting about **Karyağmaz village**.

The matching Anadolu Ajansı coverage concerns Karyağmaz, historically associated with **Dursunbey, Balıkesir**, and its relocation to **Yalıntaş Mahallesi in Mustafakemalpaşa, Bursa**.

Reference:

https://www.aa.com.tr/tr/pg/foto-galeri/sehir-degistiren-karyagmaz-koyu-yeni-yerine-tasinmak-icin-gun-sayiyor/146

---

## Following the Location Trail

This initially created some ambiguity because multiple administrative locations appeared in the source material:

```text
Karyağmaz
    |
    +-- Dursunbey
    |      |
    |      +-- Balıkesir
    |
    +-- Relocation
           |
           +-- Yalıntaş
                  |
                  +-- Mustafakemalpaşa
                         |
                         +-- Bursa
```

According to Anadolu Ajansı, Karyağmaz was being relocated from **Dursunbey, Balıkesir** to the **Yalıntaş** area of **Mustafakemalpaşa, Bursa**.

Reference:

https://www.aa.com.tr/tr/yasam/sehir-degistiren-karyagmaz-koyu-yeni-yerine-tasinmak-icin-gun-sayiyor/2432144

Later reporting also confirms that residents had moved into the new settlement in **Mustafakemalpaşa, Bursa**.

Reference:

https://www.aa.com.tr/tr/gundem/il-degistiren-karyagmazlilar-yeni-yerlesim-yerinde-ilk-kez-oy-kullandi/2896936

---

## Failed Attempts

Because the source material involved several different administrative locations, I tested a number of reasonable possibilities:

```text
cyberweek{izmir_turkey}
cyberweek{izmir_turkiye}
cyberweek{dursunbey_turkey}
cyberweek{dursunbey_turkiye}
cyberweek{balikesir_turkey}
cyberweek{balikesir_turkiye}
cyberweek{karyagmaz_turkiye}
```

None of these were accepted.

The key was following the relocation context to the **Bursa** side rather than using the village's earlier **Balıkesir/Dursunbey** association.

---

## Flag Construction

The challenge requests the format:

```text
city_country
```

The intended city was:

```text
Bursa
```

The country name was expected as:

```text
Türkiye -> turkiye
```

Therefore:

```text
bursa + turkiye
```

---

## Flag

```text
cyberweek{bursa_turkiye}
```

---

## Conclusion

This challenge was primarily an **OSINT and reverse-image-search** problem disguised as straightforward image geolocation.

The visual clues were sufficient to narrow the photograph down to **Türkiye**, but they were not enough to reliably determine the exact location.

The decisive steps were:

1. Performing reverse-image searches across multiple search engines.
2. Identifying the photograph as being related to **Karyağmaz village**.
3. Tracing the village's relocation from **Dursunbey, Balıkesir** to **Yalıntaş, Mustafakemalpaşa, Bursa**.
4. Testing the relevant administrative locations against the required flag format.
5. Confirming the accepted answer as **Bursa, Türkiye**.

Final flag:

```text
cyberweek{bursa_turkiye}
```