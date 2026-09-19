"""
02 - Altimetría: DEM, suavizado y curvas de nivel
---------------------------------------------------
Descarga el DEM Copernicus GLO-30 recortado al AOI, lo suaviza para
reducir ruido de sensor en terreno chato, y genera curvas de nivel
recortadas al polígono real del lote.

Requiere: earthengine-api, geemap, rasterio, gdal (gdal_contour en PATH),
scipy, geopandas, matplotlib.
"""

import subprocess

import ee
import geemap
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from scipy.ndimage import gaussian_filter

ee.Initialize()

aoi_gdf = gpd.read_file('aoi_pilar.geojson')
aoi = geemap.geopandas_to_ee(aoi_gdf)
aoi_geom = aoi.geometry()

# --- Descarga del DEM ---
dem = ee.ImageCollection("COPERNICUS/DEM/GLO30").select('DEM').mosaic()
dem_clip = dem.clip(aoi_geom)

geemap.ee_export_image(
    dem_clip,
    filename='dem_pilar.tif',
    scale=30,
    region=aoi_geom,
    file_per_band=False
)

# --- Suavizado (reduce ruido de píxel en terreno con poco relieve) ---
with rasterio.open('dem_pilar.tif') as src:
    dem_arr = src.read(1)
    profile = src.profile

dem_smooth = gaussian_filter(dem_arr, sigma=2)

profile.update(dtype='float32')
with rasterio.open('dem_pilar_smooth.tif', 'w', **profile) as dst:
    dst.write(dem_smooth.astype('float32'), 1)

# --- Curvas de nivel (intervalo ajustado al rango real de elevación) ---
subprocess.run([
    'gdal_contour', '-a', 'elevacion', '-i', '0.25',
    'dem_pilar_smooth.tif', 'curvas_nivel_pilar_final.shp'
], check=True)

curvas = gpd.read_file('curvas_nivel_pilar_final.shp')
curvas_clip = gpd.clip(curvas, aoi_gdf)
print(f"Curvas de nivel generadas (recortadas al AOI): {len(curvas_clip)}")

# --- Rango real de elevación dentro del AOI ---
with rasterio.open('dem_pilar_smooth.tif') as src:
    aoi_reproj = aoi_gdf.to_crs(src.crs)
    dem_clip_arr, dem_clip_transform = mask(src, aoi_reproj.geometry, crop=True, nodata=np.nan)
    dem_clip_arr = dem_clip_arr[0]

valid = dem_clip_arr[~np.isnan(dem_clip_arr)]
print(f"Elevación real dentro del AOI — mín: {valid.min():.2f} m, máx: {valid.max():.2f} m, rango: {valid.max()-valid.min():.2f} m")
