# Planet-clip-downloader
A python script for downloading clips of satellite images from Planet Labs.

Requirements:
Python 3 and the usual libraries, also area, xmltodict etc.. Look in the .py file for details. 
Should work on both windows and linux

Example usage:

(1) Download get_planet_v2.py and example.json and put them in a folder somewhere

(2) Edit the example.json file to cover your Area of interest, time interval, and minimum acceptible cloud coverage.
More filter options are available, see the planet API for details. Polygon coordinates can be convieniently acquired from http://geojson.io/.

(2) get your planet API key by logging in to planet.com and going to your profile page

(3) open command prompt, navigate to the folder that contains the .py and .json files and run this:

python get_planet_v2.py --path /path/to/where/I/keep/my/planet/images --filter /path/to/my/filter/files/example.json --key c1234MyPlanetAPIkey

The program then searches the Planet database for images that match the filter, removes 3 band duplicates of 4 band images, and compares the results with images already present in your image folder. If no new images are found, the program exits. Otherwise it estimates the area of the new images, and asks if you want to proceed with the download. NOTE: this program is not gauranteed to never accidentally use up all of your quota! I reccommend using short time intervals foryour first few seaches to make sure everythng is working properly. If you answer yes, the the ordering and download proceeds. At the end of each session, all downloaded .zip files are extracted into the data directory. 
