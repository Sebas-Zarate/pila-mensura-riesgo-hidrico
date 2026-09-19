"""
06 - Visualizaciones finales
--------------------------------
Genera las imágenes finales del análisis a partir de los archivos
intermedios ya guardados por los scripts 02, 03, 04 y 05:
  - Altimetría: DEM relleno + curvas de nivel
  - Mapa de la zona de riesgo hídrico sobre el DEM
  - Serie temporal (NDVI/NDWI/VV) de la zona baja
  - Serie temporal (NDVI/NDWI/VV) del AOI completo, como contraste

No depende de mantener el kernel vivo entre scripts: relee todo desde
los archivos .geojson / .shp / .csv generados en pasos anteriores.
"""

import os

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask

os.makedirs('assets_export', exist_ok=True)

# --- Datos base ---
aoi_gdf = gpd.read_file('aoi_pilar.geojson')

with rasterio.open('dem_pilar_smooth.tif') as src:
    aoi_reproj = aoi_gdf.to_crs(src.crs)
    dem_clip_arr, dem_clip_transform = mask(src, aoi_reproj.geometry, crop=True, nodata=np.nan)
    dem_clip_arr = dem_clip_arr[0]

extent = [
    dem_clip_transform[2],
    dem_clip_transform[2] + dem_clip_transform[0] * dem_clip_arr.shape[1],
    dem_clip_transform[5] + dem_clip_transform[4] * dem_clip_arr.shape[0],
    dem_clip_transform[5],
]

curvas_final_clip = gpd.clip(gpd.read_file('curvas_nivel_pilar_final.shp'), aoi_gdf)
zona_baja_gdf = gpd.read_file('zona_baja_pilar.geojson')
df_zona_baja = pd.read_csv('serie_zona_baja_pilar.csv')
df_completo = pd.read_csv('serie_completa_pilar.csv')


def graficar_serie(df, titulo, nombre_archivo):
    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax1.plot(df['mes'], df['ndvi'], color='green', marker='o', label='NDVI')
    ax1.plot(df['mes'], df['ndwi'], color='blue', marker='o', label='NDWI')
    ax1.set_ylabel('Índice óptico (NDVI / NDWI)')
    ax1.tick_params(axis='x', rotation=45)
    ax1.legend(loc='upper left')
    ax2 = ax1.twinx()
    ax2.plot(df['mes'], df['vv_medio'], color='darkred', marker='s', linestyle='--', label='VV (Sentinel-1)')
    ax2.set_ylabel('VV (dB)')
    ax2.legend(loc='upper right')
    plt.title(titulo)
    fig.tight_layout()
    plt.savefig(f'assets_export/{nombre_archivo}', dpi=150, bbox_inches='tight')
    plt.close(fig)


# --- 1. Altimetría ---
fig, ax = plt.subplots(figsize=(9, 9))
im = ax.imshow(dem_clip_arr, cmap='terrain', extent=extent)
curvas_final_clip.plot(ax=ax, color='black', linewidth=0.4, alpha=0.5)
aoi_gdf.boundary.plot(ax=ax, color='red', linewidth=1.5)
plt.colorbar(im, ax=ax, label='Elevación (m)', shrink=0.8)
ax.set_title('Modelo de elevación - Lote Pila (relleno + curvas)')
plt.savefig('assets_export/02_altimetria_dem_curvas.png', dpi=150, bbox_inches='tight')
plt.close(fig)

# --- 2. Mapa de zona de riesgo hídrico ---
fig, ax = plt.subplots(figsize=(9, 9))
im = ax.imshow(dem_clip_arr, cmap='terrain', extent=extent)
zona_baja_gdf.plot(ax=ax, facecolor='none', edgecolor='red', linewidth=2, hatch='//')
aoi_gdf.boundary.plot(ax=ax, color='black', linewidth=1)
plt.colorbar(im, ax=ax, label='Elevación (m)', shrink=0.8)
ax.set_title('Zona de riesgo hídrico (percentil 10 más bajo) - Lote Pila')
plt.savefig('assets_export/03_mapa_zona_riesgo_hidrico.png', dpi=150, bbox_inches='tight')
plt.close(fig)

# --- 3 y 4. Series temporales (zona baja y AOI completo) ---
graficar_serie(df_zona_baja, 'Serie temporal 12 meses - Zona baja (percentil 10) - Lote Pila', '04_serie_temporal_zona_baja.png')
graficar_serie(df_completo, 'Serie temporal 12 meses - Lote Pila completo (AOI)', '05_serie_temporal_aoi_completo.png')

print("Listo. Imágenes guardadas en assets_export/:")
for f in sorted(os.listdir('assets_export')):
    print(f' - {f}')
