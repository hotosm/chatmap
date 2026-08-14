import { esri, osm } from "./source";

export class BackgroundControl {
    onAdd(map) {
        this._map = map;
        this._container = document.createElement("div");
        this._container.className = "maplibregl-ctrl map-ctrl map-background-ctrl map-background-ctrl-sat";
        this._container.onclick = () => this.changeStyle();
        this._currentSource = "osm";
        return this._container;
    }

    changeStyle() {
        const currentStyle = this._map.getStyle()

        const allCurrentSources = Object.keys(currentStyle.sources).reduce((acc, el) => {
            if (el !== this._currentSource) {
                acc.push({
                    id: el,
                    source: { ...currentStyle.sources[el] }
                })
            }
            return acc
        },[])

        const allCurrentLayers = currentStyle.layers.filter(el =>
            el.source !== "osm" || el.source !== "esri"
        )

        this._map.once('style.load', async () => {

            allCurrentSources.forEach(source => {
                this._map.addSource(source.id, source.source)
            })

            allCurrentLayers.forEach(layer => {
                if (layer.source !== "osm" && layer.source !== "esri") {
                    this._map.addLayer(layer)
                }
                
            })
        })

        if (this._currentSource == "osm") {
            this._currentSource = "esri";
            this._container.className = [...this._container.className.split(" ")
                .filter(x => x !== "map-background-ctrl-sat"), "map-background-ctrl-osm"].join(" ")
            this._map.setStyle(esri)
        } else {
            this._container.className = [...this._container.className.split(" ")
                .filter(x => x !== "map-background-ctrl-osm"), "map-background-ctrl-sat"].join(" ")
            this._currentSource = "osm";
            this._map.setStyle(osm)
        }
        


    }

    onRemove() {
        this._container.remove();
        this._map = undefined;
    }
}

const locationHandler = async () => {
    if (!navigator.geolocation) {
      console.error("Geolocation is not supported by your browser");
      return;
    }

    try {
      const position = await new Promise((resolve, reject) => {
        const watchId = navigator.geolocation.watchPosition(
          (pos) => {
            navigator.geolocation.clearWatch(watchId);
            clearTimeout(timeoutId);
            resolve(pos);
          },
          (err) => {
            navigator.geolocation.clearWatch(watchId);
            clearTimeout(timeoutId);
            reject(err);
          },
          {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
          }
        );

        const timeoutId = setTimeout(() => {
          navigator.geolocation.clearWatch(watchId);
          reject(new Error("Location timeout: Could not get GPS fix within 15s"));
        }, 15000);
      });

      return position.coords;

    } catch (error) {
      console.error("Failed to get location:", error.message || error);
      return false;
    }
};

