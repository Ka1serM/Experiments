# Laborbericht: PBRT CPU/GPU E2E Experiment

## Konfiguration

| Parameter | Wert |
|---|---|
| Datum/Zeit | `2026-05-27T14:49:43` |
| Git commit | `d24ba4f1b86b88471b9bfecd4116e1ce150f384b` |
| Git branch | `psf-interpolation` |
| Determinismus-Grenzwert | `0.0` |
| CPU/GPU-Grenzwert | `0.1` |

## Scene-Parameter

| Parameter | Wert |
|---|---|
| Integrator class | `path` |
| Sampler class | `independent` |
| Film/sensor class | `rgb` |
| Camera class | `perspective` |
| PSF grid | `not specified` |
| Film xresolution | `1928` |
| Film yresolution | `1088` |
| Film diagonal | `6.641411898083118` |
| Sampler pixelsamples | `512` |
| SPP | `128` |

---

## Grund fuer das Experiment

<!--
Warum wurde dieses Experiment durchgefuehrt?
Welche Frage soll beantwortet werden?
-->

---

## Hypothese / Erwartung

<!--
Was wird erwartet?
-->

---

## Beobachtungen

---

## Notizen

---

## Ergebnisse

| Render | Modus | Sekunden | Determinismus rel. MSE | CPU/GPU rel. MSE | Determinismus | CPU/GPU | Speedup | Zeitersparnis |
|---|---|---|---|---|---|---|---|---|
| CPU A | CPU | `19.653` | `0.000000e+00` | `2.119661e-06` | PASS | PASS | — | — |
| CPU B | CPU | `19.655` | `0.000000e+00` | — | PASS | — | — | — |
| GPU A | GPU | `1.751` | `0.000000e+00` | `2.119661e-06` | PASS | PASS | `11.226x` | `91.1%` |
| GPU B | GPU | `1.704` | `0.000000e+00` | — | PASS | — | `11.534x` | `91.3%` |
| Durchschnitt | CPU/GPU | `19.654` / `1.727` | — | — | — | — | `11.378x` | `91.2%` |

### Relative-MSE-Diff-Bilder

| Vergleich | Bild |
|---|---|
| CPU vs CPU | `outputs/diff_cpu_vs_cpu.png` |
| GPU vs GPU | `outputs/diff_gpu_vs_gpu.png` |
| CPU vs GPU | `outputs/diff_cpu_vs_gpu.png` |

![CPU vs CPU relative MSE](outputs/diff_cpu_vs_cpu.png)

![GPU vs GPU relative MSE](outputs/diff_gpu_vs_gpu.png)

![CPU vs GPU relative MSE](outputs/diff_cpu_vs_gpu.png)


---

## Interpretation

<!--
Was bedeuten die Ergebnisse?
Sind die Abweichungen plausibel?
Wurde die Hypothese bestaetigt oder widerlegt?
-->

---

## Fazit

<!--
Kurze Zusammenfassung:
- Bestanden / fehlgeschlagen?
- Wichtigste Erkenntnis?
- Naechste Schritte?
-->

---

## Naechste Schritte

<!--
TODOs, Folgeexperimente oder Debugging-Ideen.
-->

- [ ]
- [ ]
- [ ]
