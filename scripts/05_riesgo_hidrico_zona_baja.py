"""
05 - Riesgo hídrico: zona baja del lote (percentil 10 de elevación)
------------------------------------------------------------------
Delimita el 10% de menor elevación del AOI (a partir del DEM ya recortado
al polígono real, no al rectángulo del raster) y repite la serie temporal
de NDWI/NDVI/VV solo sobre esa zona. Calcula además la superficie exacta
en riesgo hídrico.

Depende de haber corrido antes 02_altimetria_dem_curvas.py
y 04_riesgo_hidrico_serie_completa.py (reutiliza `meses`, `s2`, `s1`).
"""

import ee
import geemap
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import shapes
from rasterio.mask import mask
from shapely.geometry import shape

ee.Initialize()

aoi_gdf = gpd.read_file('aoi_pilar.geojson')

# --- DEM recortado al polígono real del AOI (no al rectángulo del raster) ---
with rasterio.open('dem_pilar_smooth.tif') as src:
    aoi_reproj = aoi_gdf.to_crs(src.crs)
    dem_clip_arr, dem_clip_transform = mask(src, aoi_reproj.geometry, crop=True, nodata=np.nan)
    dem_clip_arr = dem_clip_arr[0]
    dem_crs = src.crs

# --- Umbral y máscara del 10% más bajo, sobre el DEM ya recortado ---
dem_valido = dem_clip_arr[~np.isnan(dem_clip_arr)]
umbral_bajo = np.nanpercentile(dem_valido, 10)
print(f"Umbral zona baja (percentil 10, recortado al AOI): {umbral_bajo:.2f} m")

mascara_baja = np.where(np.isnan(dem_clip_arr), False, dem_clip_arr <= umbral_bajo)

formas = list(shapes(mascara_baja.astype('uint8'), mask=mascara_baja, transform=dem_clip_transform))
geoms = [shape(geom) for geom, val in formas if val == 1]

zona_baja_gdf = gpd.GeoDataFrame(geometry=geoms, crs=dem_crs).to_crs(epsg=4326)
zona_baja_gdf = gpd.clip(zona_baja_gdf, aoi_gdf)
zona_baja_gdf.to_file('zona_baja_pilar.geojson', driver='GeoJSON')

# --- Superficie exacta en riesgo ---
zona_baja_utm = zona_baja_gdf.to_crs(epsg=32721)
superficie_riesgo_ha = zona_baja_utm.geometry.area.sum() / 10000
SUPERFICIE_TOTAL_HA = 871.74
pct_lote = superficie_riesgo_ha / SUPERFICIE_TOTAL_HA * 100

print(f"Superficie en zona de riesgo hídrico: {superficie_riesgo_ha:.2f} ha")
print(f"Porcentaje del lote: {pct_lote:.1f}%")
print(f"Superficie sin restricciones: {SUPERFICIE_TOTAL_HA - superficie_riesgo_ha:.2f} ha ({100 - pct_lote:.1f}%)")

# --- Serie temporal de 12 meses, solo sobre la zona baja ---
# Reutiliza `meses`, `s2`, `s1` definidos en 04_riesgo_hidrico_serie_completa.py
zona_baja_ee = geemap.geopandas_to_ee(zona_baja_gdf)
zona_baja_geom = zona_baja_ee.geometry()

resultados_zona_baja = []
for inicio, fin in meses:
    coleccion_s2 = s2.filterBounds(zona_baja_geom).filterDate(inicio, fin).sort('CLOUDY_PIXEL_PERCENTAGE')
    n_s2 = coleccion_s2.size().getInfo()

    coleccion_s1 = s1.filterDate(inicio, fin)
    n_s1 = coleccion_s1.size().getInfo()
    vv_medio = None
    if n_s1 > 0:
        img_s1 = coleccion_s1.mean().clip(zona_baja_geom)
        stats_vv = img_s1.reduceRegion(ee.Reducer.mean(), zona_baja_geom, 10, maxPixels=1e9).getInfo()
        vv_medio = stats_vv.get('VV')

    ndwi_val, ndvi_val = None, None
    if n_s2 > 0:
        img_s2 = coleccion_s2.first()
        green, nir, red = img_s2.select('B3'), img_s2.select('B8'), img_s2.select('B4')
        ndwi = green.subtract(nir).divide(green.add(nir)).rename('NDWI').clip(zona_baja_geom)
        ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI').clip(zona_baja_geom)
        stats = ndwi.addBands(ndvi).reduceRegion(ee.Reducer.mean(), zona_baja_geom, 10, maxPixels=1e9).getInfo()
        ndwi_val, ndvi_val = stats.get('NDWI'), stats.get('NDVI')

    resultados_zona_baja.append({'mes': inicio[:7], 'ndwi': ndwi_val, 'ndvi': ndvi_val, 'vv_medio': vv_medio})

df_zona_baja = pd.DataFrame(resultados_zona_baja)
df_zona_baja.to_csv('serie_zona_baja_pilar.csv', index=False)

print("\nCorrelación (zona baja):")
print(df_zona_baja[['ndwi', 'ndvi', 'vv_medio']].corr())
