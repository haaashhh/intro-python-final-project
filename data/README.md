# Sample data

Real GPS recordings downloaded from the public
[OpenStreetMap GPS trace archive](https://www.openstreetmap.org/traces).
All traces were uploaded by their authors as *public* traces and are
available under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/).
© OpenStreetMap contributors.

| File | Activity | Recorded with | Points | Source trace |
|---|---|---|---|---|
| `run_contern_5k.gpx` | 5.6 km run, Contern (LU), with heart rate | Garmin Connect | 2139 | [Mincka / 12472188](https://www.openstreetmap.org/user/Mincka/traces/12472188) |
| `run_saint_pe_trail_11k.gpx` | 11.5 km trail run, Saint-Pé-de-Bigorre (FR), with heart rate | Garmin Connect | 2951 | [Crys64 / 12474342](https://www.openstreetmap.org/user/Crys64/traces/12474342) |
| `run_imola_24k.gpx` | 24 km run, Imola (IT), with heart rate | Garmin Connect | 9428 | [Danysan95 / 12470747](https://www.openstreetmap.org/user/Danysan95/traces/12470747) |
| `run_owenfs_5k.gpx` | 4.7 km run | unknown app | 1576 | [owenfs / 12464565](https://www.openstreetmap.org/user/owenfs/traces/12464565) |
| `hike_corvara_passo_gardena.gpx` | 6.8 km hike, Corvara to Passo Gardena, Dolomites (IT) | Garmin Connect | 6692 | [kangasta / 12474286](https://www.openstreetmap.org/user/kangasta/traces/12474286) |
| `ride_blue_springs_17k.gpx` | 17 km road ride | Garmin Connect | 4583 | [FlatbreadAndSmilingSunIsNiche / 12474383](https://www.openstreetmap.org/user/FlatbreadAndSmilingSunIsNiche/traces/12474383) |
| `walk_osmand_6k.gpx` | 5.8 km walk | OsmAnd | 1287 | [KofDim / 12473182](https://www.openstreetmap.org/user/KofDim/traces/12473182) |
| `walk_osmand_1k.gpx` | 1 km walk | OsmAnd | 261 | [BholeKiBhasam / 12473986](https://www.openstreetmap.org/user/BholeKiBhasam/traces/12473986) |

Files were downloaded from `https://www.openstreetmap.org/trace/<id>/data` and are unmodified.

The GPX 1.0 files under `tests/data/` come from the
[gpxpy](https://github.com/tkrajina/gpxpy) test suite (Apache License 2.0,
see `tests/data/LICENSE-gpxpy.txt`) and are only used as parser test fixtures.
