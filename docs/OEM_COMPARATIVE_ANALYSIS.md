# OEM Comparative Analysis

This table records only what the repository can substantiate. Vendor names are not assigned from an adapter class alone.

| Vendor | Identification | Acquisition | Filesystem parser | Decoder | Metadata | Limitation |
|---|---|---|---|---|---|---|
| Dahua | Metadata/filename evidence match | File/image ingestion | OEM: NOT IMPLEMENTED | FFmpeg formats where supported | FFprobe where decodable | Requires validated Dahua sample for proprietary filesystem |
| CP Plus | Metadata/filename evidence match | File/image ingestion | OEM: NOT IMPLEMENTED | FFmpeg formats where supported | FFprobe where decodable | Requires validated CP Plus sample |
| Honeywell | Metadata/filename evidence match | File/image ingestion | OEM: NOT IMPLEMENTED | FFmpeg formats where supported | FFprobe where decodable | Requires validated Honeywell sample |
| TP-Link | Metadata/filename evidence match | File/image ingestion | OEM: NOT IMPLEMENTED | FFmpeg formats where supported | FFprobe where decodable | Requires validated TP-Link sample |
| Godrej | Metadata/filename evidence match | File/image ingestion | OEM: NOT IMPLEMENTED | FFmpeg formats where supported | FFprobe where decodable | Requires validated Godrej sample |
| Uniview | Metadata/filename evidence match | File/image ingestion | OEM: NOT IMPLEMENTED | FFmpeg formats where supported | FFprobe where decodable | Requires validated Uniview sample |
| Hikvision | Metadata/filename evidence match | File/image ingestion | OEM: NOT IMPLEMENTED | FFmpeg formats where supported, including DAV where compatible | FFprobe where decodable | Requires validated Hikvision filesystem/sample |
| Matrix | Metadata/filename evidence match | File/image ingestion | OEM: NOT IMPLEMENTED | FFmpeg formats where supported | FFprobe where decodable | Requires validated Matrix sample |

## Important distinction

A `.dav` or `.ifv` file is decoded when the local FFmpeg build supports its demuxer. That is **format support**, not proof that the application understands a vendor's proprietary filesystem or acquisition protocol.
