# Limitations and Boundaries

## Implemented capability boundary

Rocket Forensics now supports standard exported surveillance files, FFmpeg-supported CCTV containers such as DAV/IFV, raw H.264/H.265 streams, read-only forensic-image ingestion and hashing, standard signature carving, optional Sleuth Kit inspection/deleted-file enumeration, FFprobe metadata, OpenCV motion and face detection, YOLO object detection, timeline/correlation, chain of custody and PDF reporting.

## Remaining OEM-specific limitations

- Proprietary DVR/NVR filesystem structures are not universally parsed.
- Vendor-specific direct acquisition protocols are not implemented.
- OEM deleted-record/index reconstruction is not implemented.
- A filename or metadata keyword is not proof of physical device identity.
- Face analysis means face **detection** only. The platform does not identify people.
- Cross-camera correlation is temporal only and does not establish same-person identity.
- YOLO requires the configured model weights and an environment with its ML dependencies.
- E01 image hashing/type detection is supported; full EWF mounting/parsing depends on an EWF-capable forensic runtime.
- Sleuth Kit features are used only when its command-line tools are installed.

## Evidence integrity

Original evidence and forensic images are kept read-only after acquisition. Decoding is performed to separate working copies. SHA-256 and MD5 are calculated from actual bytes.

## Legal/forensic qualification

The application is a prototype and does not itself certify legal admissibility, examiner qualification, or compliance with any jurisdiction's forensic laboratory accreditation requirements.
