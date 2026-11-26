# Step 7: the CCCD QR code as an exact side A

The narrowed scope (`docs/RESEARCH_PLAN.md` §2a) leans on the QR code of the chip CCCD as the
exact copy that handwritten or OCR'd fields are compared against. This step tests the one
property that design needs: when the code is read, is the value right? Thresholds were written
down first: [PREREG.md](PREREG.md). Numbers: [RESULTS.md](RESULTS.md).

## Data

None real. Testing on real cards means real citizens' identity data, and the project does not
collect it. Each payload is a made-up person (`document_intake.synth.make_person`), written as
`CCCD|CMND|name|ddmmyyyy|sex|address|ddmmyyyy` in UTF-8. That field layout is our reading of
public descriptions of the card's QR code, not checked against a card (HYPOTHESIS). What matters
here is the payload length and the Vietnamese text, which it matches in kind. The codes are drawn
with CoreImage (`CIQRCodeGenerator`, error correction M) and read with Apple Vision
(`VNDetectBarcodesRequest`). No card layout, emblem or real number is drawn.

## Findings

1. **No silent errors.** 2,526 of 2,800 degraded codes were decoded, and every decoded string
   equals the generated payload byte for byte, Vietnamese diacritics included (no Latin-1 or
   NFD mix-ups). PREREG §1 gives **GO**. This is what the QR format promises: Reed–Solomon error
   correction either recovers the data or fails.
2. **Failures are abstentions.** The decode rate falls with blur (69.8%), the combined condition
   (78.8%) and the phone-photo condition (89.2%). A failed read asks the clerk for another photo.
   It does not produce a wrong value.

## Limits

This is an **upper bound**. The codes are fresh and perfectly printed, then degraded in software.
A real card's code is laser-engraved on worn polycarbonate, behind a hologram, photographed under
real glare. The simulated glare here is mild; it brightens part of the code without washing it
out. The decode *rate* on real cards will be lower. The *zero silent errors* finding depends on
the QR format, not on these conditions, so it should carry over to real cards. That is a
HYPOTHESIS until it is tested on real cards with consent.

## Reproduce

```bash
swiftc -O audits/cccd_qr/qr_tool.swift -o audits/cccd_qr/work/qr_tool
uv run python audits/cccd_qr/run_qr.py --md audits/cccd_qr/RESULTS.md
```
