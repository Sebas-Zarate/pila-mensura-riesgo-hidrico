"""
01 - Definición y exportación del área de interés (AOI)
--------------------------------------------------------
Dibuja el polígono del lote sobre una imagen satelital de alta resolución
usando geemap, calcula su superficie y lo exporta como GeoJSON.

Requiere: earthengine-api autenticado (ee.Authenticate() / ee.Initialize())
y geemap instalado.
"""

import ee
import geemap

ee.Initialize()

# Centrar el mapa en las coordenadas de referencia del lote
LAT, LON = -36.265676, -57.993135

Map = geemap.Map()
Map.setCenter(LON, LAT, 15)
Map.add_basemap('SATELLITE')
Map  # dibujar el polígono del lote a mano con la herramienta de polígono del panel

# --- Ejecutar después de dibujar el polígono en el mapa ---
aoi = ee.FeatureCollection(Map.draw_features)
geemap.ee_export_vector(aoi, filename='aoi_pilar.geojson')

area_ha = aoi.geometry().area(1).divide(10000).getInfo()
print(f"Superficie del AOI: {area_ha:.2f} ha")
