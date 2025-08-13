# chatmap-py

This is a Python package for analyzing chat logs in JSON format,
pair locations with messages and generate a GeoJSON as a result.

## Install

```bash
pip install chatmap-py
```

## Usage

```
chatmap_py.cli <filename> > map.geojson
```

Or in your code:

```py
from chatmap_py import parser
geoJSON = parser.streamParser(data)
```

## Licensing

This project is part of ChatMap

Copyright 2025 Emilio Mariscal

This is free software! you may use this project under the terms of the GNU General Public License (GPL) Version 3.
