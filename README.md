# Planet-clip-downloader
A python script for downloading clips of satellite images from Planet Labs.

Requirements:
python 3 and the usual libraries, also area, xmltodict etc. look in the .py file for details
should work on both windows and linux

Example usage:

Edit the example.json file to cover your Area of interest, time interval, and minimum acceptible cloud coverage
more filter options are available, see the planet API for details. Polygon coordinates can be
convieniently got from http://geojson.io/.

Then run at the command line with

python get_planet_v2.py --path /path/to/where/I/keep/my/planet/files 
--filter /path/to/my/filter/files/example.json --key c1234MyPlanetAPIkey

