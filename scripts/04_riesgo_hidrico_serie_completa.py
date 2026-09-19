"""
04 - Riesgo hídrico: serie temporal de 12 meses (AOI completo)
------------------------------------------------------------------
Calcula NDWI y NDVI (Sentinel-2) y retrodispersión VV (Sentinel-1, radar)
mes a mes sobre los últimos 12 meses, promediados sobre el AOI completo.

Sirve como línea de base: en este proyecto no mostró correlación fuerte
entre radar e índices ópticos, lo que llevó a repetir el análisis solo
sobre la zona baja del lote (ver script 05).
"""

import datetime

import ee
import geemap
import geopandas as gpd
import pandas as pd
from dateutil.relativedelta import relativedelta

ee.Initialize()

aoi_gdf = gpd.read_file('aoi_pilar.geojson')
aoi = geemap.geopandas_to_ee(aoi_gdf)
aoi_geom = aoi.geometry()

s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
s1 = ee.ImageCollection('COPERNICUS/S1_GRD') \
    .filterBounds(aoi_geom) \
    .filter(ee.Filter.eq('instrumentMode', 'IW')) \
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
    .select('VV')

# Últimos 12 meses hasta la fecha de corte del análisis
HOY = datetime.date(2026, 9, 18)
meses = []
for i in range(12, 0, -1):
    fin_mes = HOY - relativedelta(months=i - 1)
    inicio_mes = fin_mes - relativedelta(months=1)
    meses.append((inicio_mes.isoformat(), fin_mes.isoformat()))

resultados = []
for inicio, fin in meses:
    coleccion_s2 = s2.filterBounds(aoi_geom).filterDate(inicio, fin).sort('CLOUDY_PIXEL_PERCENTAGE')
    n_s2 = coleccion_s2.size().getInfo()

    coleccion_s1 = s1.filterDate(inicio, fin)
    n_s1 = coleccion_s1.size().getInfo()
    vv_medio = None
    if n_s1 > 0:
        img_s1 = coleccion_s1.mean().clip(aoi_geom)
        stats_vv = img_s1.reduceRegion(ee.Reducer.mean(), aoi_geom, 10, maxPixels=1e9).getInfo()
        vv_medio = stats_vv.get('VV')

    ndwi_val, ndvi_val = None, None
    if n_s2 > 0:
        img_s2 = coleccion_s2.first()
        green, nir, red = img_s2.select('B3'), img_s2.select('B8'), img_s2.select('B4')
        ndwi = green.subtract(nir).divide(green.add(nir)).rename('NDWI').clip(aoi_geom)
        ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI').clip(aoi_geom)
        stats = ndwi.addBands(ndvi).reduceRegion(ee.Reducer.mean(), aoi_geom, 10, maxPixels=1e9).getInfo()
        ndwi_val, ndvi_val = stats.get('NDWI'), stats.get('NDVI')

    resultados.append({'mes': inicio[:7], 'ndwi': ndwi_val, 'ndvi': ndvi_val, 'vv_medio': vv_medio})
    print(f"{inicio[:7]}: NDWI={ndwi_val} | NDVI={ndvi_val} | VV={vv_medio}")

df_completo = pd.DataFrame(resultados)
df_completo.to_csv('serie_completa_pilar.csv', index=False)

print("\nCorrelación (AOI completo):")
print(df_completo[['ndwi', 'ndvi', 'vv_medio']].corr())
