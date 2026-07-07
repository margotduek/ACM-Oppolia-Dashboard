# Oppolia — Reportes de Pauta

Dashboards de la campaña de generación de leads de **Oppolia México** (Meta Ads).

- **Reporte para el cliente** (`cliente.html`) → resultados de negocio
- **Reporte interno (Iván)** (`interno.html`) → playbook de optimización paso a paso

Publicado con GitHub Pages. Generado por Converging Works.

## Regenerar los datos

```bash
python3 fetch_data.py          # jala Meta Ads (act_1291756783078220) a data.json
python3 build_report_data.py   # regenera data/meta-ads-resumen.md con las cifras vigentes
```

Requiere un `.env` (no está en el repo) con `META_ACCESS_TOKEN` y `META_OPPOLIA_AD_ACCOUNT_ID`.

### Qué se regenera solo vs qué sigue siendo manual

`cliente.html` e `interno.html` **no se regeneran automáticamente** — no son un template con placeholders,
son reportes redactados a mano porque mezclan métricas con juicio cualitativo que no viene de la API:

- La categorización de leads ("aprovechable" / "confundido" / "no contactable") sale de revisar a mano
  la [hoja de seguimiento](https://docs.google.com/spreadsheets/d/139DsDF5Wx_Bk5k4Y9CashvoKhZNbQhZu3m23Pq9H2UQ/edit),
  no de Meta.
- Las citas textuales de leads, el veredicto narrativo y las recomendaciones son redacción, no datos.

Lo que **sí** es 100% derivable de Meta Ads y se regenera con `build_report_data.py` → `data/meta-ads-resumen.md`:
inversión, leads, CPL, CTR, desglose por campaña/creativo, edad/género, región y Facebook vs Instagram.
Antes de escribir el próximo reporte, corre el script y usa esas cifras como fuente de verdad en vez de
volver a sacarlas a mano de Meta Ads Manager.
