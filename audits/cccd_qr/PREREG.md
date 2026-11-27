# Pre-registration: CCCD QR decode

Written on 2026-11-25, before any run.

## Why synthetic

The narrowed scope uses the QR code on the chip CCCD as the exact side A. Testing it on real
cards means real citizens' identity data; the project does not collect that. So every payload
here is generated: a made-up person (`document_intake.synth.make_person`) in the field layout of
the card's QR code, `CCCD|CMND|name|ddmmyyyy|sex|address|ddmmyyyy`, UTF-8. The codes are drawn
with CoreImage and read with Apple Vision's barcode detector. No card layout, emblem or real
number is reproduced.

This is an **upper bound**: a clean, freshly generated code, degraded in software. A real card's
code is engraved on worn plastic and photographed under glare.

## Conditions

clean; small (module of 1.5–2 px); blur; skew 7°; phone photo (the pilot's `photo()`); glare (a
bright blob over part of the code); combined. 400 codes per condition.

## Thresholds (fixed now)

1. **Silent errors.** A decode whose payload differs from the generated one in any byte. GO for
   "QR is an exact side A" if there are none in any condition (400 clean decodes per condition
   bound the rate below about 0.75% at 95%); KILL if any condition has one.
2. **Coverage.** The decode rate per condition is reported, with no bar: a failed decode is an
   abstention, not an error, and a clerk can retake the photo.
3. **Unicode.** Every decoded name and address must equal the generated NFC string. A decoder
   that reads the bytes as Latin-1 counts as a silent error under 1.
