# Rocket Forensics Architecture

```text
Authenticated Frontend (React/Vite)
        |
        v
FastAPI API
        |
        +--> Case / Evidence / Custody / Report services
        |
        +--> Evidence integrity: SHA-256 + MD5
        |
        +--> Device evidence inference
        |
        +--> Vendor/format adapter registry
        |       +--> Standard containers
        |       +--> FFmpeg CCTV DAV / IFV
        |       +--> Raw H.264/H.265
        |       +--> OEM identification-only boundaries
        |
        +--> Read-only forensic-image ingestion
        |       +--> image hashing/type detection
        |       +--> Sleuth Kit partition/filesystem inspection (when installed)
        |       +--> standard signature carving
        |
        +--> Analysis working copy
        |       +--> FFmpeg decode
        |       +--> YOLO object detection
        |       +--> OpenCV motion detection
        |       +--> OpenCV face detection
        |
        +--> Normalized timeline / search / temporal correlation
        |
        +--> Chain of custody
        |
        +--> ReportLab forensic PDF
        |
        v
MongoDB + immutable/read-only evidence storage + working storage
```

## Preservation rule

The acquired evidence bytes are hashed at acquisition. Analysis reads the original only after an integrity gate; formats requiring decoding are converted into a separate working copy. The original acquisition is not overwritten.

## OEM boundary

The adapter architecture is ready for OEM-specific filesystem and acquisition modules, but an adapter class is not treated as proof of OEM support. OEM parsing requires validated device/image samples and parser specifications.
