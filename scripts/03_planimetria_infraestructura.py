"""
03 - Planimetría: digitalización de infraestructura
------------------------------------------------------
Digitaliza a mano (sobre geemap) caminos internos/de acceso y elementos
puntuales de infraestructura (silos bolsa, molinos), y calcula longitud
total de caminos y cantidad de elementos puntuales.

Flujo: se dibuja cada capa por separado en un Map nuevo para no mezclar
geometrías de distinto tipo, y se exporta antes de pasar a la siguiente.
"""

import ee
import geemap
import geopandas as gpd

ee.Initialize()

aoi_gdf = gpd.read_file('aoi_pilar.geojson')
aoi = geemap.geopandas_to_ee(aoi_gdf)

# --- Capa 1: caminos (herramienta de polilínea) ---
Map = geemap.Map()
Map.centerObject(aoi, zoom=17)
Map.add_basemap('Esri.WorldImagery')
Map.addLayer(aoi, {}, 'AOI Pila')
Map  # dibujar caminos a mano

# --- Ejecutar después de dibujar los caminos ---
caminos = ee.FeatureCollection(Map.draw_features)
geemap.ee_export_vector(caminos, filename='caminos_pilar.geojson')

# --- Capa 2: infraestructura puntual (silos bolsa + molinos) ---
# Reiniciar el Map (nuevo objeto) antes de dibujar esta capa
Map2 = geemap.Map()
Map2.centerObject(aoi, zoom=17)
Map2.add_basemap('Esri.WorldImagery')
Map2.addLayer(aoi, {}, 'AOI Pila')
Map2  # dibujar puntos a mano

# --- Ejecutar después de marcar los puntos ---
infraestructura = ee.FeatureCollection(Map2.draw_features)
geemap.ee_export_vector(infraestructura, filename='infraestructura_puntual_pilar.geojson')
print(f"Puntos marcados: {infraestructura.size().getInfo()}")

# --- Métricas finales ---
caminos_gdf = gpd.read_file('caminos_pilar.geojson')
infra_gdf = gpd.read_file('infraestructura_puntual_pilar.geojson')

caminos_utm = caminos_gdf.to_crs(epsg=32721)  # UTM 21S
longitud_caminos_m = caminos_utm.geometry.length.sum()

print(f"Longitud total de caminos digitalizados: {longitud_caminos_m:.0f} m")
print(f"Cantidad de elementos puntuales (silos bolsa + molinos): {len(infra_gdf)}")
