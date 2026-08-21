# Phase 12 — Report generation

Administrator **Generate QoS Report** produces a professional multi-section PDF.

## Selectable filters

- ISP
- Package
- Region
- Date range / days
- Focus metric (`download|upload|latency|jitter|packet_loss|qos`)
- Comparison mode (`isp_vs_isp|isp_vs_benchmark|isp_vs_ideal`)

## Report sections

1. Cover  
2. Executive Summary  
3. Measurement Methodology  
4. Test Configuration  
5. ISP Performance  
6. Package Performance  
7. Regional Performance  
8. Mauritius Heatmap (tabular + chart)  
9. Download Analysis  
10. Upload Analysis  
11. Latency Analysis  
12. Jitter Analysis  
13. Packet Loss  
14. QoS Benchmark  
15. Peak-Hour Analysis  
16. AI Analysis  
17. Recommendations  
18. Limitations  
19. Conclusion  

The PDF states **number of tests**, **measurement period**, **servers used**,
**methodology**, and **limitations**.

## API

```http
GET /admin/report?days=90
GET /admin/report?isp=Emtel&region=Ebene&metric=latency&comparison=isp_vs_ideal&days=30
GET /admin/report?date_from=2026-07-01&date_to=2026-08-20&package=Fibre%20100
```

## UI

Admin portal → **Report** tab (or toolbar **Generate QoS Report**).

## Modules

- `backend/app/services/report_service.py`
- `backend/app/services/admin_report.py`
