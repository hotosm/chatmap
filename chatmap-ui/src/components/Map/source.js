/*
 * Sources for baselayers available for the map. Other sources can be added
 * in the future in order to have other baselayers.
*/

export const osm = {
  "version": 8,
	"sources": {
    "osm": {
			"type": "raster",
			"tiles": ["https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"],
			"tileSize": 256,
      "attribution": "&copy; OpenStreetMap Contributors",
      "maxzoom": 19
    }
  },
  "layers": [
    {
      "id": "osm",
      "type": "raster",
      "source": "osm" // This must match the source key above
    }
  ]
};

export const esri = {
  "version": 8,
	"sources": {
    "esri": {
			"type": "raster",
			"tiles": ["https://services.arcgisonline.com/ArcGis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}.png"],
			"tileSize": 256,
      "attribution": "&copy; ESRI",
      "maxzoom": 19
    }
  },
  "layers": [
    {
      "id": "esri",
      "type": "raster",
      "source": "esri" // This must match the source key above
    }
  ]
};

