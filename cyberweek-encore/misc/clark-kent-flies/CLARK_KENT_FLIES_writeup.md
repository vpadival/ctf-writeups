# CLARK_KENT_FLIES

**Category:** Misc
**Difficulty:** Medium
**Points:** 100

## Challenge Description

> Clark didn't trust words on paper.
> Words on paper get read by the wrong people.

**Provided file:** `last_son_of_krypton.wav`

## Initial Analysis

Started by inspecting the file itself rather than assuming its format from the extension.

```
$ file last_son_of_krypton.wav
last_son_of_krypton.wav: RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, mono 22050 Hz
```

```python
>>> import wave
>>> w = wave.open('last_son_of_krypton.wav','rb')
>>> w.getparams()
_wave_params(nchannels=1, sampwidth=2, framerate=22050, nframes=220160, comptype='NONE', compname='not compressed')
```

A standard uncompressed 16-bit mono PCM WAV, roughly 10 seconds long. Nothing unusual in the header, no appended data after the audio stream, and the file plays back as what sounds like plain background noise/tone — nothing intelligible to the ear.

## Hypothesis

The description leans on a "written vs. spoken" theme — a hint that the flag isn't encoded as *literal audio content* to be transcribed, but rather hidden in a domain that isn't perceptible by just listening. The classic move for this in audio-misc challenges is spectrogram steganography: text or an image is drawn directly into the frequency/time bins of the signal, invisible to the ear but visible once the waveform is transformed into the frequency domain.

## Solution

Loaded the waveform and rendered its spectrogram (STFT magnitude over time):

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile

sr, data = wavfile.read('last_son_of_krypton.wav')
plt.figure(figsize=(20, 8))
plt.specgram(data, Fs=sr, NFFT=2048, noverlap=1800, cmap='inferno')
plt.axis('off')
plt.savefig('spec_hi.png', dpi=200, bbox_inches='tight', pad_inches=0)
```

This immediately revealed text baked into the mid-frequency band (~4–8 kHz) across the duration of the clip — but rendered upside down:

![upside-down spectrogram text](spec_raw.png)

Flipping the rendered spectrogram image vertically (`PIL.Image.FLIP_TOP_BOTTOM`) corrected the orientation and made it fully legible:

```python
from PIL import Image
Image.open('spec_hi.png').transpose(Image.FLIP_TOP_BOTTOM).save('spec_hi_flipped.png')
```

![flag in spectrogram](spec_hi_flipped.png)

The recovered text reads cleanly:

```
hks{aldsb19954zxc9mg}
```

## Flag

```
hks{aldsb19954zxc9mg}
```

## Takeaways

- Always inspect a file's actual structure (`file`, header parsing) before trusting its extension or assuming the content is meant to be consumed at face value.
- "Misc" audio challenges that emphasize *distrust of visible/written text* are a strong signal to check the spectrogram — a very common technique for embedding text/images inaudibly in a waveform's frequency content.
- The embedded text was mirrored vertically in this instance; when a spectrogram render looks garbled or upside down, trying basic image transforms (flip, 180° rotate) before discarding the approach is worth the extra minute.
